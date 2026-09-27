# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""PKI issuer state and lookup helpers; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    desired_from,
    view,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import state_result
from ansible_collections.jomrr.bao.plugins.module_utils._state import (
    Resource,
    ensure,
    remove,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

FIELDS: Fields = {
    "leaf_not_after_behavior": "str",
    "usage": "csv",
    "manual_chain": "list",
    "revocation_signature_algorithm": "str",
    "issuing_certificates": "list",
    "crl_distribution_points": "list",
    "delta_crl_distribution_points": "list",
    "ocsp_servers": "list",
    "enable_aia_url_templating": "bool",
}


def find_issuer(client: Api, mount: str, name: str) -> str | None:
    """Return the ID of the issuer with the given name."""
    key_info = client.list_keys(f"{mount}/issuers").get("key_info") or {}
    for issuer_id, info in key_info.items():
        if isinstance(info, dict) and info.get("issuer_name") == name:
            return str(issuer_id)
    return None


def find_key(client: Api, mount: str, name: str) -> str | None:
    """Return the ID of the key with the given name."""
    key_info = client.list_keys(f"{mount}/keys").get("key_info") or {}
    for key_id, info in key_info.items():
        if isinstance(info, dict) and info.get("key_name") == name:
            return str(key_id)
    return None


def _default(
    client: Api, mount: str, issuer_id: str, check_mode: bool
) -> tuple[bool, bool]:
    """Make the issuer the default and return (was default, changed)."""
    config = client.get(f"{mount}/config/issuers") or {}
    was_default = config.get("default") == issuer_id
    if not was_default and not check_mode:
        client.write(f"{mount}/config/issuers", {"default": issuer_id})
    return was_default, not was_default


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile the settings and default status of an existing issuer."""
    mount = str(params["mount"]).strip("/")
    name = str(params["name"])
    issuer_id = find_issuer(client, mount, name)
    if params["state"] == "absent":
        resource = Resource(client, f"{mount}/issuer/{issuer_id}", FIELDS, check_mode)
        return remove(
            resource, None if issuer_id is None else {"name": name}, {"name": name}
        )
    if issuer_id is None:
        raise ValueError(
            f"issuer {name} not found in {mount}; create it with pki_ca first"
        )
    resource = Resource(client, f"{mount}/issuer/{issuer_id}", FIELDS, check_mode)
    current = client.get(resource.path) or {}
    result = ensure(resource, current, desired_from(params, FIELDS), patch=True)
    changed = bool(result["changed"])
    before = dict(result["diff"]["before"])
    after = dict(result["diff"]["after"])
    if params.get("default"):
        was_default, default_changed = _default(client, mount, issuer_id, check_mode)
        changed = changed or default_changed
        before["default"] = was_default
        after["default"] = True
    return state_result(changed, before, after, issuer_id=issuer_id)


def issuer_view(current: dict[str, Any] | None) -> dict[str, Any]:
    """Return the comparable view of an issuer for diffs."""
    return view(FIELDS, current)
