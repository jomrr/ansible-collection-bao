# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao AppRoles."""

from __future__ import annotations

DOCUMENTATION = r"""
module: approle
short_description: Manage AppRoles
version_added: 0.1.0
description:
- Create, update or remove an AppRole and optionally pin its Role ID.
- Only the given options are compared and written; other role settings keep their server values.
- Secret IDs are managed with M(jomrr.bao.approle_secret_id).
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, jomrr.bao.connection.state,
  jomrr.bao.options, jomrr.bao.options.token, jomrr.bao.options.approle_mount]
options:
  name:
    description: AppRole name.
    type: str
    required: true
    version_added: 0.1.0
  role_id:
    description: Explicit Role ID; OpenBao assigns one when omitted.
    type: str
    version_added: 0.1.0
  bind_secret_id:
    description: Require a Secret ID at login.
    type: bool
    version_added: 0.1.0
  secret_id_bound_cidrs:
    description: Networks in CIDR notation allowed to use Secret IDs of this role; host addresses need C(/32) or C(/128).
    type: list
    elements: str
    version_added: 0.1.0
  secret_id_num_uses:
    description: Number of logins per Secret ID; V(0) is unlimited.
    type: int
    version_added: 0.1.0
  secret_id_ttl:
    description: Secret ID lifetime as seconds or duration; V(0) never expires.
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Create an application role with a pinned Role ID
  jomrr.bao.approle:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    name: application
    role_id: application
    token_policies: [application]
    token_ttl: 15m
    token_max_ttl: 1h
    secret_id_bound_cidrs: [192.0.2.0/24]
    token_bound_cidrs: [192.0.2.0/24]

- name: Remove a role
  jomrr.bao.approle:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    name: legacy
    state: absent
"""

RETURN = r"""
role_id:
  description: Effective Role ID of the role; V(null) when the role does not exist yet in check mode.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _approle
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
            "mount": {"type": "str", "default": "approle"},
            "role_id": {"type": "str"},
            "bind_secret_id": {"type": "bool"},
            "secret_id_bound_cidrs": {"type": "list", "elements": "str"},
            "secret_id_num_uses": {"type": "int"},
            "secret_id_ttl": {"type": "str"},
            **token_spec(),
            **state_spec(),
        },
        _approle.run_role,
    )


if __name__ == "__main__":
    main()
