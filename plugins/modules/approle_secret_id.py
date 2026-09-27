# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage custom OpenBao AppRole Secret IDs."""

from __future__ import annotations

DOCUMENTATION = r"""
module: approle_secret_id
short_description: Register or revoke a custom Secret ID
version_added: 0.1.0
description:
- Register a caller supplied Secret ID for an AppRole or destroy it.
- An already registered Secret ID is left unchanged; its restrictions are not updated.
- With O(verify) the module logs in with the Secret ID and revokes the verification token, which consumes one use when the role limits Secret ID uses.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, jomrr.bao.connection.state,
  jomrr.bao.options, jomrr.bao.options.approle_mount]
options:
  role:
    description: Name of the AppRole owning the Secret ID.
    type: str
    required: true
    version_added: 0.1.0
  secret_id:
    description: Secret ID to register or destroy; use a random value of at least 32 characters.
    type: str
    required: true
    version_added: 0.1.0
  cidr_list:
    description: Networks allowed to log in with this Secret ID.
    type: list
    elements: str
    version_added: 0.1.0
  token_bound_cidrs:
    description: Networks allowed to use tokens issued for this Secret ID.
    type: list
    elements: str
    version_added: 0.1.0
  ttl:
    description: Secret ID lifetime as seconds or duration.
    type: str
    version_added: 0.1.0
  num_uses:
    description: Number of logins allowed with this Secret ID; V(0) is unlimited.
    type: int
    version_added: 0.1.0
  metadata:
    description: Metadata attached to tokens issued for this Secret ID.
    type: dict
    version_added: 0.1.0
  verify:
    description: Log in with the Secret ID after registration and revoke the verification token.
    type: bool
    default: false
    version_added: 0.1.0
  role_id:
    description: Role ID used for O(verify).
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Register and verify the application Secret ID
  jomrr.bao.approle_secret_id:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    role: application
    role_id: application
    secret_id: "{{ vault_application_secret_id }}"
    verify: true

- name: Revoke a leaked Secret ID
  jomrr.bao.approle_secret_id:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    role: application
    secret_id: "{{ vault_old_secret_id }}"
    state: absent
"""

RETURN = r"""
accessor:
  description: Accessor of the registered Secret ID; V(null) in check mode before registration.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _approle
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    run_module,
    state_spec,
)

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "role": {"type": "str", "required": True},
            "mount": {"type": "str", "default": "approle"},
            "secret_id": {"type": "str", "required": True, "no_log": True},
            "cidr_list": {"type": "list", "elements": "str"},
            "token_bound_cidrs": {"type": "list", "elements": "str"},
            "ttl": {"type": "str"},
            "num_uses": {"type": "int"},
            "metadata": {"type": "dict"},
            "verify": {"type": "bool", "default": False},
            "role_id": {"type": "str"},
            **state_spec(),
        },
        _approle.run_secret_id,
        required_if=[("verify", True, ("role_id",))],
    )


if __name__ == "__main__":
    main()
