# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Auth and secrets mount state; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    desired_from,
    merge,
    plan,
    to_api,
    view,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import state_result
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

FIELDS: Fields = {
    "description": "str",
    "default_lease_ttl": "duration",
    "max_lease_ttl": "duration",
}
API = {"secret": "sys/mounts", "auth": "sys/auth"}


def _options(params: dict[str, Any]) -> dict[str, str]:
    """Return the requested mount options; KV defaults to version 2."""
    options = {
        str(key): str(value) for key, value in (params.get("options") or {}).items()
    }
    if params.get("type") == "kv":
        options.setdefault("version", "2")
    return options


def _flatten(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the tunable fields of a mount listing entry."""
    config = entry.get("config") or {}
    return {
        "description": entry.get("description"),
        "default_lease_ttl": config.get("default_lease_ttl"),
        "max_lease_ttl": config.get("max_lease_ttl"),
    }


def _guard(
    path: str, current: dict[str, Any], mount_type: str, options: dict[str, str]
) -> None:
    """Refuse to replace a mount of another type or KV version."""
    if current.get("type") != mount_type:
        raise ValueError(
            f"mount {path} has type {current.get('type')!r}, requested {mount_type!r};"
            " migrate it explicitly"
        )
    current_options = {
        str(key): str(value) for key, value in (current.get("options") or {}).items()
    }
    for key, value in options.items():
        if current_options.get(key) != value:
            raise ValueError(
                f"mount {path} option {key} is {current_options.get(key)!r},"
                f" requested {value!r}; migrate it explicitly"
            )


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one auth or secrets mount."""
    base = API[str(params["kind"])]
    path = str(params["path"]).strip("/")
    current = (client.get(base) or {}).get(f"{path}/")
    if params["state"] == "absent":
        if current is None:
            return state_result(False, {}, {})
        if not check_mode:
            client.delete(f"{base}/{path}")
        before = {"type": current.get("type"), **view(FIELDS, _flatten(current))}
        return state_result(True, before, {})
    mount_type = str(params.get("type") or "")
    if not mount_type:
        raise ValueError("type is required when state is present")
    options = _options(params)
    desired = desired_from(params, FIELDS)
    if current is None:
        body: dict[str, Any] = {"type": mount_type, **to_api(FIELDS, desired)}
        config = {
            key: body.pop(key) for key in list(body) if key.endswith("_lease_ttl")
        }
        if config:
            body["config"] = config
        if options:
            body["options"] = options
        if not check_mode:
            client.write(f"{base}/{path}", body)
        after = {"type": mount_type, "options": options, **view(FIELDS, desired)}
        return state_result(True, {}, after)
    _guard(path, current, mount_type, options)
    flat = _flatten(current)
    changes = plan(FIELDS, flat, desired)
    if changes and not check_mode:
        client.write(f"{base}/{path}/tune", to_api(FIELDS, changes))
    before = {"type": mount_type, "options": options, **view(FIELDS, flat)}
    after = {
        "type": mount_type,
        "options": options,
        **view(FIELDS, merge(flat, desired)),
    }
    return state_result(bool(changes), before, after)
