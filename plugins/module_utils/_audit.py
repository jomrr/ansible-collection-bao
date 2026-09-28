# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Audit device state; not a public API."""

from __future__ import annotations

from typing import Any, cast

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    Mapping,
    normalize,
    plan,
)
from ansible_collections.jomrr.bao.plugins.module_utils._module import MASK
from ansible_collections.jomrr.bao.plugins.module_utils._result import state_result
from ansible_collections.jomrr.bao.plugins.module_utils._state import Resource, remove
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api, BaoError

API = "sys/audit"
FIELDS: Fields = {"type": "str", "description": "str", "options": "map"}
# The server stores options as strings and a JSON boolean as "1" or "0".
BOOLEAN_OPTIONS = frozenset(
    {"elide_list_responses", "hmac_accessor", "log_raw", "skip_test"}
)
BOOLEANS = {
    "1": "true",
    "t": "true",
    "true": "true",
    "0": "false",
    "f": "false",
    "false": "false",
}
# Header values of an http device can hold credentials.
HIDDEN_OPTIONS = frozenset({"headers"})


def _text(name: str, value: object) -> str:
    """Return an option value as string with one spelling for booleans."""
    text = str(value)
    if isinstance(value, bool) or name in BOOLEAN_OPTIONS:
        return BOOLEANS.get(text.lower(), text)
    return text


def _strings(options: object) -> dict[str, str]:
    """Return an option mapping with string values."""
    mapping = cast(Mapping, normalize("map", options))
    return {name: _text(name, value) for name, value in mapping.items()}


def _device(entry: Mapping | None) -> Mapping | None:
    """Return the settings of a listed audit device."""
    if entry is None:
        return None
    return {
        "type": entry.get("type"),
        "description": entry.get("description") or "",
        "options": _strings(entry.get("options")),
        "local": bool(entry.get("local")),
    }


def _desired(params: Mapping) -> Mapping:
    """Return the requested settings; unset options are not compared."""
    desired: Mapping = {"type": str(params["type"])}
    if params.get("description") is not None:
        desired["description"] = str(params["description"])
    options = params.get("options"), params.get("secret_options")
    if options != (None, None):
        desired["options"] = {**_strings(options[0]), **_strings(options[1])}
    return desired


def _view(device: Mapping | None, hidden: frozenset[str]) -> dict[str, Any]:
    """Return the settings for the diff with hidden option values masked."""
    shown = dict(device or {})
    if "options" in shown:
        shown["options"] = {
            name: MASK if name in hidden else value
            for name, value in shown["options"].items()
        }
    return shown


def _replace(resource: Resource, current: Mapping, desired: Mapping) -> None:
    """Disable the device and enable the new one; restore the old one on failure."""
    resource.client.delete(resource.path)
    try:
        resource.client.write(resource.path, {**current, **desired})
    except BaoError:
        resource.client.write(resource.path, current)
        raise


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one audit device; an existing device is replaced only on request."""
    path = str(params["path"]).strip("/")
    if not path:
        raise ValueError("path must name an audit device")
    resource = Resource(client, f"{API}/{path}", FIELDS, check_mode)
    current = _device((client.get(API) or {}).get(f"{path}/"))
    hidden = HIDDEN_OPTIONS | frozenset(_strings(params.get("secret_options")))
    before = _view(current, hidden)
    if params["state"] == "absent":
        return remove(resource, current, before)
    desired = _desired(params)
    after = _view({**(current or {}), **desired}, hidden)
    if current is None:
        if not check_mode:
            client.write(resource.path, desired)
        return state_result(True, before, after)
    changes = plan(FIELDS, current, desired)
    if changes and not params["replace"]:
        raise ValueError(
            f"audit device {path} differs in {', '.join(sorted(changes))}; audit"
            " devices cannot be modified, set replace to disable and enable it again"
        )
    if changes and not check_mode:
        _replace(resource, current, desired)
    return state_result(bool(changes), before, after)
