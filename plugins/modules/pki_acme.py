# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao PKI ACME configuration."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_acme
short_description: Manage the ACME configuration of a PKI engine
version_added: 0.1.0
description:
- Reconcile C(config/acme) of a PKI secrets engine.
- Enabling ACME requires the cluster C(path) set through M(jomrr.bao.pki_config).
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.state, jomrr.bao.options.pki_mount]
options:
  enabled:
    description: Serve ACME directories from this mount.
    type: bool
    version_added: 0.1.0
  allowed_issuers:
    description: Issuers ACME clients may use; V(*) allows all.
    type: list
    elements: str
    version_added: 0.1.0
  allowed_roles:
    description: Roles ACME clients may use; V(*) allows all.
    type: list
    elements: str
    version_added: 0.1.0
  allow_role_ext_key_usage:
    description: Honor the role's extended key usage instead of forcing server authentication.
    type: bool
    version_added: 0.1.0
  default_directory_policy:
    description: Behavior of the default directory, such as V(sign-verbatim), V(forbid) or V(role:<name>).
    type: str
    version_added: 0.1.0
  dns_resolver:
    description: DNS resolver address used for challenge validation.
    type: str
    version_added: 0.1.0
  eab_policy:
    description: External account binding requirement.
    type: str
    choices: [not-required, new-account-required, always-required]
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Enable ACME with mandatory account binding
  jomrr.bao.pki_acme:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    enabled: true
    allowed_roles: [web-server]
    default_directory_policy: role:web-server
    eab_policy: always-required
"""

RETURN = r"""
# The module returns only the standard fields; the diff holds the ACME settings.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _pki_config
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "enabled": {"type": "bool"},
            "allowed_issuers": {"type": "list", "elements": "str"},
            "allowed_roles": {"type": "list", "elements": "str"},
            "allow_role_ext_key_usage": {"type": "bool"},
            "default_directory_policy": {"type": "str"},
            "dns_resolver": {"type": "str"},
            "eab_policy": {
                "type": "str",
                "choices": ["not-required", "new-account-required", "always-required"],
            },
        },
        _pki_config.run_acme,
    )


if __name__ == "__main__":
    main()
