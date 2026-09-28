# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""AppRole and Secret ID state; not a public API."""

from __future__ import annotations

import json
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    as_list,
    view,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import state_result
from ansible_collections.jomrr.bao.plugins.module_utils._state import (
    TOKEN_FIELDS,
    Resource,
    reconcile,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

ROLE_FIELDS: Fields = {
    "bind_secret_id": "bool",
    "secret_id_bound_cidrs": "cidrs",
    "secret_id_num_uses": "int",
    "secret_id_ttl": "duration",
    **TOKEN_FIELDS,
}
SECRET_ID_FIELDS: Fields = {
    "cidr_list": "cidrs",
    "token_bound_cidrs": "cidrs",
    "secret_id_ttl": "duration",
    "secret_id_num_uses": "int",
    "metadata": "map",
}


def _role_id(client: Api, path: str) -> str | None:
    """Read the Role ID of an existing role."""
    data = client.get(f"{path}/role-id")
    return None if data is None else str(data.get("role_id") or "")


def run_role(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one AppRole including its Role ID."""
    path = f"auth/{params['mount']}/role/{params['name']}"
    result, current = reconcile(Resource(client, path, ROLE_FIELDS, check_mode), params)
    if params["state"] == "absent":
        return result
    changed = bool(result["changed"])
    before = result["diff"]["before"]
    after = result["diff"]["after"]
    role_id = None if current is None else _role_id(client, path)
    requested = params.get("role_id")
    if requested is not None and role_id != str(requested):
        changed = True
        if not check_mode:
            client.write(f"{path}/role-id", {"role_id": str(requested)})
        before["role_id"] = role_id
        after["role_id"] = str(requested)
        role_id = str(requested)
    elif role_id is None and not check_mode:
        role_id = _role_id(client, path)
    return state_result(changed, before, after, role_id=role_id)


def run_info(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Read one AppRole; the bindings stay in the server's notation for a rollback."""
    del check_mode
    current = client.get(f"auth/{params['mount']}/role/{params['name']}")
    role = dict(current or {})
    return {
        "changed": False,
        "exists": current is not None,
        "role": role,
        "secret_id_bound_cidrs": as_list(role.get("secret_id_bound_cidrs")),
        "token_bound_cidrs": as_list(role.get("token_bound_cidrs")),
    }


def _secret_id_body(params: dict[str, Any]) -> dict[str, Any]:
    """Build the custom Secret ID request."""
    body: dict[str, Any] = {"secret_id": str(params["secret_id"])}
    for key in ("cidr_list", "token_bound_cidrs"):
        if params.get(key) is not None:
            body[key] = list(params[key])
    if params.get("ttl") is not None:
        body["ttl"] = params["ttl"]
    if params.get("num_uses") is not None:
        body["num_uses"] = int(params["num_uses"])
    if params.get("metadata"):
        body["metadata"] = json.dumps(params["metadata"])
    return body


def _verify(params: dict[str, Any], client: Api) -> None:
    """Log in with the Secret ID and revoke the verification token."""
    role_id = params.get("role_id")
    if not role_id:
        raise ValueError("verify requires role_id")
    auth = client.login(str(params["mount"]), str(role_id), str(params["secret_id"]))
    client.with_token(str(auth.get("client_token") or "")).revoke_self()


def run_secret_id(
    params: dict[str, Any], check_mode: bool, client: Api
) -> dict[str, Any]:
    """Register or revoke one custom Secret ID."""
    base = f"auth/{params['mount']}/role/{params['role']}"
    secret_id = str(params["secret_id"])
    lookup = client.write(f"{base}/secret-id/lookup", {"secret_id": secret_id})
    current = lookup.get("data") if lookup else None
    accessor = None if not current else current.get("secret_id_accessor")
    before = (
        {"accessor": accessor, **view(SECRET_ID_FIELDS, current)} if current else {}
    )
    if params["state"] == "absent":
        if not current:
            return state_result(False, {}, {})
        if not check_mode:
            client.write(f"{base}/secret-id/destroy", {"secret_id": secret_id})
        return state_result(True, before, {})
    changed = not current
    if changed and not check_mode:
        response = client.write(f"{base}/custom-secret-id", _secret_id_body(params))
        accessor = ((response or {}).get("data") or {}).get("secret_id_accessor")
    if params.get("verify") and not check_mode:
        _verify(params, client)
    requested = {
        "cidr_list": params.get("cidr_list"),
        "token_bound_cidrs": params.get("token_bound_cidrs"),
        "secret_id_ttl": params.get("ttl"),
        "secret_id_num_uses": params.get("num_uses"),
        "metadata": params.get("metadata"),
    }
    after = (
        before
        if current
        else {"accessor": accessor, **view(SECRET_ID_FIELDS, requested)}
    )
    return state_result(changed, before, after, accessor=accessor)
