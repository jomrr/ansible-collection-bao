# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao userpass users."""

from __future__ import annotations

DOCUMENTATION = r"""
module: userpass_user
short_description: Manage userpass users
version_added: 0.1.0
description:
- Create, update or remove a user of the userpass authentication method, for example a break-glass account.
- The password is set only when the user is created; later runs never change it.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, jomrr.bao.connection.state,
  jomrr.bao.options, jomrr.bao.options.token]
options:
  name:
    description: User name.
    type: str
    required: true
    version_added: 0.1.0
  mount:
    description: Userpass authentication mount.
    type: str
    default: userpass
    version_added: 0.1.0
  password:
    description: Initial password; required to create the user and ignored afterwards.
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Create a break-glass operator
  jomrr.bao.userpass_user:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: users
    name: operator
    password: "{{ vault_operator_password }}"
    token_policies: [operator]
    token_bound_cidrs: [192.0.2.10]
    token_ttl: 30m
"""

RETURN = r"""
# The module returns only the standard fields; the diff never contains the password.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _userpass
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    run_module,
    state_spec,
    token_spec,
)

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "name": {"type": "str", "required": True},
            "mount": {"type": "str", "default": "userpass"},
            "password": {"type": "str", "no_log": True},
            **token_spec(),
            **state_spec(),
        },
        _userpass.run,
    )


if __name__ == "__main__":
    main()
