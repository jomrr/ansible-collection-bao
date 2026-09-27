# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao SSH certificate roles."""

from __future__ import annotations

DOCUMENTATION = r"""
module: ssh_role
short_description: Manage SSH certificate roles
version_added: 0.1.0
description:
- Create, update or remove a CA role of an SSH secrets engine for host or user certificates.
- Principals are limited by O(allowed_users) for user certificates and O(allowed_domains) for host certificates.
- OpenBao replaces the whole role on every write, so settings outside this module's options return to their defaults on an update.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, jomrr.bao.connection.state,
  jomrr.bao.options, jomrr.bao.options.ssh_mount]
options:
  name:
    description: SSH role name.
    type: str
    required: true
    version_added: 0.1.0
  key_type:
    description: Role type; only certificate authority roles are supported.
    type: str
    choices: [ca]
    default: ca
    version_added: 0.1.0
  allow_user_certificates:
    description: Sign user certificates.
    type: bool
    version_added: 0.1.0
  allow_host_certificates:
    description: Sign host certificates.
    type: bool
    version_added: 0.1.0
  allowed_users:
    description: User principals allowed in user certificates; V(*) allows any.
    type: list
    elements: str
    version_added: 0.1.0
  allowed_users_template:
    description: Allow identity templates in O(allowed_users).
    type: bool
    version_added: 0.1.0
  allowed_domains:
    description: Domains allowed as host principals; V(*) allows any.
    type: list
    elements: str
    version_added: 0.1.0
  allowed_domains_template:
    description: Allow identity templates in the host principal domains.
    type: bool
    version_added: 0.1.0
  default_user:
    description: Principal used when the request names none.
    type: str
    version_added: 0.1.0
  default_user_template:
    description: Allow identity templates in O(default_user).
    type: bool
    version_added: 0.1.0
  allow_bare_domains:
    description: Allow the allowed domains themselves as host principals.
    type: bool
    version_added: 0.1.0
  allow_subdomains:
    description: Allow subdomains of the allowed domains as host principals.
    type: bool
    version_added: 0.1.0
  allowed_extensions:
    description: Extensions a request may set; V(*) allows any.
    type: list
    elements: str
    version_added: 0.1.0
  default_extensions:
    description: Extensions added to every certificate, such as C(permit-pty).
    type: dict
    version_added: 0.1.0
  allowed_critical_options:
    description: Critical options a request may set.
    type: list
    elements: str
    version_added: 0.1.0
  default_critical_options:
    description: Critical options added to every certificate.
    type: dict
    version_added: 0.1.0
  allow_user_key_ids:
    description: Let requests choose the key ID.
    type: bool
    version_added: 0.1.0
  key_id_format:
    description: Template for generated key IDs.
    type: str
    version_added: 0.1.0
  allowed_user_key_lengths:
    description: Allowed key types and lengths of signed public keys.
    type: dict
    version_added: 0.1.0
  algorithm_signer:
    description: Signature algorithm such as V(rsa-sha2-512) or V(default).
    type: str
    version_added: 0.1.0
  ttl:
    description: Default certificate validity as seconds or duration.
    type: str
    version_added: 0.1.0
  max_ttl:
    description: Maximum certificate validity as seconds or duration.
    type: str
    version_added: 0.1.0
  not_before_duration:
    description: Backdating of the validity start as seconds or duration.
    type: str
    version_added: 0.1.0
  allow_empty_principals:
    description: Allow certificates without principals.
    type: bool
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Host certificates for the example domain
  jomrr.bao.ssh_role:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: ssh
    name: hosts
    allow_host_certificates: true
    allowed_domains: [example.test]
    allow_subdomains: true
    ttl: 720h
    max_ttl: 8760h
    algorithm_signer: rsa-sha2-512

- name: User certificates for administrators
  jomrr.bao.ssh_role:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: ssh
    name: admins
    allow_user_certificates: true
    allowed_users: [root, admin]
    default_user: admin
    default_extensions:
      permit-pty: ""
    ttl: 8h
"""

RETURN = r"""
# The module returns only the standard fields; the diff holds the compared role settings.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils import _ssh
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    named_spec,
    run_module,
)

# pylint: enable=wrong-import-position

SPEC_TYPES: dict[str, dict[str, Any]] = {
    "str": {"type": "str"},
    "bool": {"type": "bool"},
    "csv": {"type": "list", "elements": "str"},
    "map": {"type": "dict"},
    "duration": {"type": "str"},
}


def main() -> None:
    """Run the module."""
    spec = {name: dict(SPEC_TYPES[kind]) for name, kind in _ssh.ROLE_FIELDS.items()}
    spec["key_type"].update({"choices": ["ca"], "default": "ca"})
    run_module(named_spec(spec), _ssh.run_role)


if __name__ == "__main__":
    main()
