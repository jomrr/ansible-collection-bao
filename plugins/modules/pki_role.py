# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao PKI roles."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_role
short_description: Manage PKI certificate roles
version_added: 0.1.0
description:
- Create, update or remove a PKI role used as certificate template.
- Only the given options are compared; updates are applied as merge patch so other settings keep their values.
- Set O(server_flag) and O(client_flag) to V(false) when O(ext_key_usage_oids) alone must define the extended key usage.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, jomrr.bao.connection.state,
  jomrr.bao.options, jomrr.bao.options.pki_mount]
options:
  name:
    description: PKI role name.
    type: str
    required: true
    version_added: 0.1.0
  issuer_ref:
    description: Issuer used by this role.
    type: str
    version_added: 0.1.0
  ttl:
    description: Default certificate lifetime as seconds or duration.
    type: str
    version_added: 0.1.0
  max_ttl:
    description: Maximum certificate lifetime as seconds or duration.
    type: str
    version_added: 0.1.0
  not_before_duration:
    description: Backdating of the certificate start as seconds or duration.
    type: str
    version_added: 0.1.0
  allow_localhost:
    description: Allow localhost as common name or SAN.
    type: bool
    version_added: 0.1.0
  allowed_domains:
    description: Domains allowed in common names and SANs.
    type: list
    elements: str
    version_added: 0.1.0
  allowed_domains_template:
    description: Allow identity templates in O(allowed_domains).
    type: bool
    version_added: 0.1.0
  allow_bare_domains:
    description: Allow certificates for the allowed domains themselves.
    type: bool
    version_added: 0.1.0
  allow_subdomains:
    description: Allow subdomains of the allowed domains.
    type: bool
    version_added: 0.1.0
  allow_glob_domains:
    description: Allow glob patterns in O(allowed_domains).
    type: bool
    version_added: 0.1.0
  allow_wildcard_certificates:
    description: Allow wildcard names.
    type: bool
    version_added: 0.1.0
  allow_any_name:
    description: Allow any name without domain checks.
    type: bool
    version_added: 0.1.0
  enforce_hostnames:
    description: Require valid host names in common names and SANs.
    type: bool
    version_added: 0.1.0
  allow_ip_sans:
    description: Allow IP subject alternative names.
    type: bool
    version_added: 0.1.0
  allowed_uri_sans:
    description: Allowed URI subject alternative names.
    type: list
    elements: str
    version_added: 0.1.0
  allowed_uri_sans_template:
    description: Allow identity templates in O(allowed_uri_sans).
    type: bool
    version_added: 0.1.0
  allowed_other_sans:
    description: Allowed other SANs in the form C(oid;UTF8:value).
    type: list
    elements: str
    version_added: 0.1.0
  allowed_serial_numbers:
    description: Allowed subject serial numbers.
    type: list
    elements: str
    version_added: 0.1.0
  allowed_user_ids:
    description: Allowed user IDs in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  server_flag:
    description: Add the server authentication extended key usage.
    type: bool
    version_added: 0.1.0
  client_flag:
    description: Add the client authentication extended key usage.
    type: bool
    version_added: 0.1.0
  code_signing_flag:
    description: Add the code signing extended key usage.
    type: bool
    version_added: 0.1.0
  email_protection_flag:
    description: Add the email protection extended key usage.
    type: bool
    version_added: 0.1.0
  key_type:
    description: Key type of issued certificates.
    type: str
    choices: [rsa, ec, ed25519, any]
    version_added: 0.1.0
  key_bits:
    description: Key size of issued certificates.
    type: int
    version_added: 0.1.0
  signature_bits:
    description: Signature hash size.
    type: int
    version_added: 0.1.0
  use_pss:
    description: Use RSA PSS signatures.
    type: bool
    version_added: 0.1.0
  key_usage:
    description: Key usage values.
    type: list
    elements: str
    version_added: 0.1.0
  ext_key_usage:
    description: Named extended key usage values.
    type: list
    elements: str
    version_added: 0.1.0
  ext_key_usage_oids:
    description: Extended key usage OIDs, for example V(1.3.6.1.4.1.311.20.2.2) for smart card logon.
    type: list
    elements: str
    version_added: 0.1.0
  use_csr_common_name:
    description: Take the common name from the CSR when signing.
    type: bool
    version_added: 0.1.0
  use_csr_sans:
    description: Take the SANs from the CSR when signing.
    type: bool
    version_added: 0.1.0
  ou:
    description: Organizational units in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  organization:
    description: Organizations in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  country:
    description: Countries in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  locality:
    description: Localities in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  province:
    description: Provinces in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  street_address:
    description: Street addresses in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  postal_code:
    description: Postal codes in the subject.
    type: list
    elements: str
    version_added: 0.1.0
  generate_lease:
    description: Create leases for issued certificates.
    type: bool
    version_added: 0.1.0
  no_store:
    description: Do not store issued certificates.
    type: bool
    version_added: 0.1.0
  require_cn:
    description: Require a common name.
    type: bool
    version_added: 0.1.0
  policy_identifiers:
    description: Certificate policy OIDs.
    type: list
    elements: str
    version_added: 0.1.0
  basic_constraints_valid_for_non_ca:
    description: Mark basic constraints valid for non CA certificates.
    type: bool
    version_added: 0.1.0
  cn_validations:
    description: Common name validations such as V(email), V(hostname) or V(disabled).
    type: list
    elements: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Smart card logon template for a Samba AD domain
  jomrr.bao.pki_role:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    name: smartcard-logon
    allowed_domains: [example.test]
    allow_subdomains: true
    allowed_other_sans: ["1.3.6.1.4.1.311.20.2.3;UTF8:*@example.test"]
    server_flag: false
    client_flag: true
    ext_key_usage_oids: ["1.3.6.1.4.1.311.20.2.2"]
    policy_identifiers: ["1.3.6.1.4.1.311.21.8.1"]
    ttl: 8760h
    max_ttl: 17520h
"""

RETURN = r"""
# The module returns only the standard fields; the diff holds the compared role settings.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils import _pki_role
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    named_spec,
    run_module,
)

# pylint: enable=wrong-import-position

SPEC_TYPES: dict[str, dict[str, Any]] = {
    "str": {"type": "str"},
    "int": {"type": "int"},
    "bool": {"type": "bool"},
    "duration": {"type": "str"},
    "list": {"type": "list", "elements": "str"},
}


def main() -> None:
    """Run the module."""
    spec = {name: dict(SPEC_TYPES[kind]) for name, kind in _pki_role.FIELDS.items()}
    spec["key_type"]["choices"] = ["rsa", "ec", "ed25519", "any"]
    run_module(named_spec(spec), _pki_role.run)


if __name__ == "__main__":
    main()
