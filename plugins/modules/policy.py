# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao ACL policies."""

from __future__ import annotations

DOCUMENTATION = r"""
module: policy
short_description: Manage ACL policies
version_added: 0.1.0
description:
- Create, update or remove an ACL policy by name.
- The policy document is compared after stripping surrounding whitespace.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.state, jomrr.bao.options]
options:
  name:
    description: Policy name.
    type: str
    required: true
    version_added: 0.1.0
  rules:
    description: Policy document in HCL or JSON; required when O(state=present).
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Allow reading application secrets
  jomrr.bao.policy:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    name: application-reader
    rules: |
      path "kv/data/app/*" {
        capabilities = ["read"]
      }

- name: Remove an obsolete policy
  jomrr.bao.policy:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    name: legacy
    state: absent
"""

RETURN = r"""
# The module returns only the standard fields; the diff holds name and rules.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _policy
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    run_module,
    state_spec,
)

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "name": {"type": "str", "required": True},
            "rules": {"type": "str"},
            **state_spec(),
        },
        _policy.run,
        required_if=[("state", "present", ("rules",))],
    )


if __name__ == "__main__":
    main()
