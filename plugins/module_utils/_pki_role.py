# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""PKI role state; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import Fields
from ansible_collections.jomrr.bao.plugins.module_utils._state import (
    Resource,
    reconcile,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

FIELDS: Fields = {
    "issuer_ref": "str",
    "ttl": "duration",
    "max_ttl": "duration",
    "not_before_duration": "duration",
    "allow_localhost": "bool",
    "allowed_domains": "list",
    "allowed_domains_template": "bool",
    "allow_bare_domains": "bool",
    "allow_subdomains": "bool",
    "allow_glob_domains": "bool",
    "allow_wildcard_certificates": "bool",
    "allow_any_name": "bool",
    "enforce_hostnames": "bool",
    "allow_ip_sans": "bool",
    "allowed_uri_sans": "list",
    "allowed_uri_sans_template": "bool",
    "allowed_other_sans": "list",
    "allowed_serial_numbers": "list",
    "allowed_user_ids": "list",
    "server_flag": "bool",
    "client_flag": "bool",
    "code_signing_flag": "bool",
    "email_protection_flag": "bool",
    "key_type": "str",
    "key_bits": "int",
    "signature_bits": "int",
    "use_pss": "bool",
    "key_usage": "list",
    "ext_key_usage": "list",
    "ext_key_usage_oids": "list",
    "use_csr_common_name": "bool",
    "use_csr_sans": "bool",
    "ou": "list",
    "organization": "list",
    "country": "list",
    "locality": "list",
    "province": "list",
    "street_address": "list",
    "postal_code": "list",
    "generate_lease": "bool",
    "no_store": "bool",
    "require_cn": "bool",
    "policy_identifiers": "list",
    "basic_constraints_valid_for_non_ca": "bool",
    "cn_validations": "list",
}


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one PKI role; updates use a merge patch."""
    path = f"{str(params['mount']).strip('/')}/roles/{params['name']}"
    return reconcile(Resource(client, path, FIELDS, check_mode), params, patch=True)[0]
