# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""SSH secrets engine CA action and role state; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    Mapping,
    merge,
    to_api,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import action_result
from ansible_collections.jomrr.bao.plugins.module_utils._state import (
    Resource,
    reconcile,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api, BaoError

ROLE_FIELDS: Fields = {
    "key_type": "str",
    "allow_user_certificates": "bool",
    "allow_host_certificates": "bool",
    "allowed_users": "csv",
    "allowed_users_template": "bool",
    "allowed_domains": "csv",
    "allowed_domains_template": "bool",
    "default_user": "str",
    "default_user_template": "bool",
    "allow_bare_domains": "bool",
    "allow_subdomains": "bool",
    "allowed_extensions": "csv",
    "default_extensions": "map",
    "allowed_critical_options": "csv",
    "default_critical_options": "map",
    "allow_user_key_ids": "bool",
    "key_id_format": "str",
    "allowed_user_key_lengths": "map",
    "algorithm_signer": "str",
    "ttl": "duration",
    "max_ttl": "duration",
    "not_before_duration": "duration",
    "allow_empty_principals": "bool",
}


def run_role(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one SSH role; writes send the merged role because POST replaces it."""
    path = f"{str(params['mount']).strip('/')}/roles/{params['name']}"
    resource = Resource(client, path, ROLE_FIELDS, check_mode)
    return reconcile(resource, params, body=_merged)[0]


def _merged(current: Mapping | None, desired: Mapping) -> Mapping:
    """Return the full role body because POST replaces every setting."""
    merged = merge(current, desired)
    return to_api(
        ROLE_FIELDS, {key: merged[key] for key in ROLE_FIELDS if key in merged}
    )


def _normalize_key(value: object) -> str:
    """Compare public keys without surrounding or repeated whitespace."""
    return " ".join(str(value or "").split())


def _current_ca(client: Api, mount: str) -> dict[str, Any] | None:
    """Read the CA configuration; an engine without an issuer answers HTTP 400."""
    try:
        return client.get(f"{mount}/config/ca")
    except BaoError as exc:
        if exc.status == 400 and "no default issuer" in str(exc):
            return None
        raise


def run_ca(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Generate or import the signing key unless the engine already has one."""
    mount = str(params["mount"]).strip("/")
    current = _current_ca(client, mount) or {}
    public_key = current.get("public_key")
    requested = params.get("public_key")
    if public_key:
        if requested and _normalize_key(requested) != _normalize_key(public_key):
            raise ValueError(
                f"SSH engine {mount} already has a different signing key;"
                " remove it explicitly before importing another one"
            )
        return action_result(False, f"SSH CA exists in {mount}", public_key=public_key)
    if check_mode:
        return action_result(
            True, f"Would configure the SSH CA in {mount}", public_key=None
        )
    if params.get("private_key"):
        body: dict[str, Any] = {
            "generate_signing_key": False,
            "private_key": params["private_key"],
            "public_key": requested,
        }
    else:
        body = {"generate_signing_key": True}
        for name in ("key_type", "key_bits"):
            if params.get(name) is not None:
                body[name] = params[name]
    response = client.write(f"{mount}/config/ca", body)
    data = (response or {}).get("data") or {}
    created = data.get("public_key") or (_current_ca(client, mount) or {}).get(
        "public_key"
    )
    return action_result(True, f"Configured the SSH CA in {mount}", public_key=created)
