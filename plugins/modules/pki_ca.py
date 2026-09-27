# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Create OpenBao PKI root and intermediate authorities."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_ca
short_description: Generate a root or intermediate certificate authority
version_added: 0.1.0
description:
- Generate a root issuer, or generate an intermediate CSR and import its signed certificate.
- The action is idempotent by O(issuer_name); an existing issuer of that name is reported unchanged.
- An intermediate is signed in one of three ways, by returning RV(csr) for external signing,
  by importing O(certificate), or by signing through O(signing_mount) in the same server.
- Give O(key_name) so that a rerun after external signing reuses the generated key instead of creating another one.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action, jomrr.bao.options.pki_mount]
attributes:
  check_mode:
    support: full
    description: Reads the issuer list and reports the pending generation without creating keys.
options:
  issuer_name:
    description: Name of the issuer to create; the idempotency key.
    type: str
    required: true
    version_added: 0.1.0
  type:
    description: Authority type.
    type: str
    choices: [root, intermediate]
    required: true
    version_added: 0.1.0
  mode:
    description: Key handling; V(exported) returns the private key and V(existing) reuses O(key_name).
    type: str
    choices: [internal, exported, existing]
    default: internal
    version_added: 0.1.0
  key_name:
    description: Name of the generated key; an existing key of that name is reused for intermediates.
    type: str
    version_added: 0.1.0
  key_type:
    description: Key type of a generated key.
    type: str
    choices: [rsa, ec, ed25519]
    version_added: 0.1.0
  key_bits:
    description: Key size of a generated key.
    type: int
    version_added: 0.1.0
  common_name:
    description: Common name of the authority certificate.
    type: str
    required: true
    version_added: 0.1.0
  ou:
    description: Organizational units of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  organization:
    description: Organizations of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  country:
    description: Countries of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  locality:
    description: Localities of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  province:
    description: Provinces of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  street_address:
    description: Street addresses of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  postal_code:
    description: Postal codes of the subject.
    type: list
    elements: str
    version_added: 0.1.0
  alt_names:
    description: DNS and email subject alternative names.
    type: list
    elements: str
    version_added: 0.1.0
  ip_sans:
    description: IP subject alternative names.
    type: list
    elements: str
    version_added: 0.1.0
  uri_sans:
    description: URI subject alternative names.
    type: list
    elements: str
    version_added: 0.1.0
  other_sans:
    description: Other SANs in the form C(oid;UTF8:value).
    type: list
    elements: str
    version_added: 0.1.0
  ttl:
    description: Lifetime of a root certificate as seconds or duration.
    type: str
    version_added: 0.1.0
  not_after:
    description: Absolute end of a root certificate's validity as RFC 3339 timestamp.
    type: str
    version_added: 0.1.0
  max_path_length:
    description: Maximum path length of the authority.
    type: int
    version_added: 0.1.0
  permitted_dns_domains:
    description: Name constraints restricting issued certificates to these domains.
    type: list
    elements: str
    version_added: 0.1.0
  exclude_cn_from_sans:
    description: Do not add the common name to the SANs.
    type: bool
    version_added: 0.1.0
  certificate:
    description: PEM certificate chain signed externally for an intermediate.
    type: str
    version_added: 0.1.0
  signing_mount:
    description: PKI mount in the same server whose issuer signs the intermediate.
    type: str
    version_added: 0.1.0
  signing_issuer:
    description: Issuer reference in O(signing_mount).
    type: str
    default: default
    version_added: 0.1.0
  signing_ttl:
    description: Lifetime of the signed intermediate as seconds or duration.
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Create the root authority
  jomrr.bao.pki_ca:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-root
    issuer_name: root
    type: root
    key_name: root-key
    common_name: Example Root CA
    ttl: 87600h
    max_path_length: 1

- name: Create the intermediate signed by the root in the same server
  jomrr.bao.pki_ca:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    issuer_name: intermediate
    type: intermediate
    key_name: intermediate-key
    common_name: Example Issuing CA
    signing_mount: pki-root
    signing_issuer: root
    signing_ttl: 43800h
    max_path_length: 0

- name: Request an intermediate certificate from an external authority
  jomrr.bao.pki_ca:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    issuer_name: intermediate
    type: intermediate
    key_name: intermediate-key
    common_name: Example Issuing CA
  register: bao_intermediate

- name: Import the externally signed certificate
  jomrr.bao.pki_ca:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    issuer_name: intermediate
    type: intermediate
    key_name: intermediate-key
    common_name: Example Issuing CA
    certificate: "{{ lookup('ansible.builtin.file', 'intermediate-chain.pem') }}"
"""

RETURN = r"""
issuer_id:
  description: ID of the created or existing issuer; V(null) while an intermediate waits for its certificate.
  type: str
  returned: success
certificate:
  description: PEM certificate of the issuer.
  type: str
  returned: when the issuer exists
csr:
  description: PEM certificate signing request of a generated intermediate.
  type: str
  returned: when an intermediate CSR was generated
private_key:
  description: PEM private key; register with C(no_log).
  type: str
  returned: when O(mode=exported)
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _pki_ca
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position

LIST = {"type": "list", "elements": "str"}


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "issuer_name": {"type": "str", "required": True},
            "type": {
                "type": "str",
                "choices": ["root", "intermediate"],
                "required": True,
            },
            "mode": {
                "type": "str",
                "choices": ["internal", "exported", "existing"],
                "default": "internal",
            },
            "key_name": {"type": "str"},
            "key_type": {"type": "str", "choices": ["rsa", "ec", "ed25519"]},
            "key_bits": {"type": "int"},
            "common_name": {"type": "str", "required": True},
            "ou": LIST,
            "organization": LIST,
            "country": LIST,
            "locality": LIST,
            "province": LIST,
            "street_address": LIST,
            "postal_code": LIST,
            "alt_names": LIST,
            "ip_sans": LIST,
            "uri_sans": LIST,
            "other_sans": LIST,
            "ttl": {"type": "str"},
            "not_after": {"type": "str"},
            "max_path_length": {"type": "int"},
            "permitted_dns_domains": LIST,
            "exclude_cn_from_sans": {"type": "bool"},
            "certificate": {"type": "str"},
            "signing_mount": {"type": "str"},
            "signing_issuer": {"type": "str", "default": "default"},
            "signing_ttl": {"type": "str"},
        },
        _pki_ca.run_ca,
        mutually_exclusive=[("certificate", "signing_mount")],
    )


if __name__ == "__main__":
    main()
