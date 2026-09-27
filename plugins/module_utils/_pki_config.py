# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""PKI engine configuration state: urls, crl, cluster and acme; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    desired_from,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import state_result
from ansible_collections.jomrr.bao.plugins.module_utils._state import Resource, ensure
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

URL_FIELDS: Fields = {
    "issuing_certificates": "list",
    "crl_distribution_points": "list",
    "delta_crl_distribution_points": "list",
    "ocsp_servers": "list",
    "enable_templating": "bool",
}
CRL_FIELDS: Fields = {
    "expiry": "duration",
    "disable": "bool",
    "ocsp_disable": "bool",
    "ocsp_expiry": "duration",
    "auto_rebuild": "bool",
    "auto_rebuild_grace_period": "duration",
    "enable_delta": "bool",
    "delta_rebuild_interval": "duration",
}
CLUSTER_FIELDS: Fields = {"path": "str", "aia_path": "str"}
ACME_FIELDS: Fields = {
    "enabled": "bool",
    "allowed_issuers": "list",
    "allowed_roles": "list",
    "allow_role_ext_key_usage": "bool",
    "default_directory_policy": "str",
    "dns_resolver": "str",
    "eab_policy": "str",
}
SECTIONS = {"urls": URL_FIELDS, "crl": CRL_FIELDS, "cluster": CLUSTER_FIELDS}


def _section(
    client: Api, path: str, fields: Fields, requested: dict[str, Any], check_mode: bool
) -> dict[str, Any]:
    """Reconcile the given keys of one configuration endpoint."""
    current = client.get(path) or {}
    desired = desired_from(requested, fields)
    return ensure(Resource(client, path, fields, check_mode), current, desired)


def run_config(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile the urls, crl and cluster configuration sections given."""
    mount = str(params["mount"]).strip("/")
    changed = False
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for name, fields in SECTIONS.items():
        requested = params.get(name)
        if not requested:
            continue
        result = _section(
            client, f"{mount}/config/{name}", fields, requested, check_mode
        )
        changed = changed or bool(result["changed"])
        before[name] = result["diff"]["before"]
        after[name] = result["diff"]["after"]
    return state_result(changed, before, after)


def run_acme(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile the ACME configuration."""
    mount = str(params["mount"]).strip("/")
    return _section(client, f"{mount}/config/acme", ACME_FIELDS, params, check_mode)
