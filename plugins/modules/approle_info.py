# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Read an OpenBao AppRole."""

from __future__ import annotations

DOCUMENTATION = r"""
module: approle_info
short_description: Read an AppRole and its network bindings
version_added: 0.1.0
description:
- Read one AppRole without changing it.
- The network bindings are returned as the server reports them, so they can be written back
  with M(jomrr.bao.approle) to roll back a rejected change.
- Called with a newly issued token, a successful read proves that the token may use the API
  from the current network; a denied read fails the task.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.info, jomrr.bao.options.approle_mount]
options:
  name:
    description: Name of the AppRole to read.
    type: str
    required: true
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Keep the current bindings for a rollback
  jomrr.bao.approle_info:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: ansible
    name: ansible-admin
  register: bao_role_before

- name: Change the bindings and verify access with a new token
  block:
    - name: Write the new bindings
      jomrr.bao.approle:
        url: https://bao.example.test:8200
        token: "{{ bao_token }}"
        mount: ansible
        name: ansible-admin
        secret_id_bound_cidrs: [192.0.2.0/24]
        token_bound_cidrs: [192.0.2.0/24]

    - name: Log in with the new bindings
      jomrr.bao.login:
        url: https://bao.example.test:8200
        mount: ansible
        role_id: "{{ bao_role_id }}"
        secret_id: "{{ bao_secret_id }}"
      register: bao_probe
      no_log: true

    - name: Verify the new token can read the AppRole
      jomrr.bao.approle_info:
        url: https://bao.example.test:8200
        token: "{{ bao_probe.token }}"
        mount: ansible
        name: ansible-admin
  rescue:
    - name: Restore the previous bindings
      jomrr.bao.approle:
        url: https://bao.example.test:8200
        token: "{{ bao_token }}"
        mount: ansible
        name: ansible-admin
        secret_id_bound_cidrs: "{{ bao_role_before.secret_id_bound_cidrs }}"
        token_bound_cidrs: "{{ bao_role_before.token_bound_cidrs }}"
"""

RETURN = r"""
exists:
  description: Whether the AppRole exists.
  type: bool
  returned: success
role:
  description: Settings of the AppRole as reported by the server; empty when it does not exist.
  type: dict
  returned: success
secret_id_bound_cidrs:
  description: Networks allowed to use Secret IDs, in the server's notation; empty when unset.
  type: list
  elements: str
  returned: success
token_bound_cidrs:
  description: Networks allowed to use issued tokens, in the server's notation; empty when unset.
  type: list
  elements: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _approle
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "name": {"type": "str", "required": True},
            "mount": {"type": "str", "default": "approle"},
        },
        _approle.run_info,
    )


if __name__ == "__main__":
    main()
