# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao KV version 2 secrets."""

from __future__ import annotations

DOCUMENTATION = r"""
module: kv2_secret
short_description: Manage KV version 2 secret data
version_added: 0.1.0
description:
- Reconcile the keys given in O(data), generate missing O(generate) keys once and keep other existing keys.
- Every write uses check and set with the current version, so concurrent changes fail instead of being overwritten.
- A secret whose current version was deleted or destroyed is not recreated; restore it or remove it with O(state=absent) first.
- The diff lists keys and the version only; values never appear in output.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.state, jomrr.bao.options]
options:
  mount:
    description: KV version 2 mount.
    type: str
    required: true
    version_added: 0.1.0
  path:
    description: Secret path below the mount.
    type: str
    required: true
    version_added: 0.1.0
  data:
    description: Keys and values reconciled on every run.
    type: dict
    version_added: 0.1.0
  generate:
    description: Keys generated once when missing; each value maps to optional C(length) and C(chars) settings.
    type: dict
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Provide database credentials with a generated password
  jomrr.bao.kv2_secret:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: automation
    path: app/database
    data:
      username: application
    generate:
      password:
        length: 40
        chars: [ascii_letters, digits]

- name: Remove a secret with all versions
  jomrr.bao.kv2_secret:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: automation
    path: app/legacy
    state: absent
"""

RETURN = r"""
version:
  description: Secret version after the run; V(0) when the secret does not exist.
  type: int
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _kv2
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    run_module,
    state_spec,
)

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "path": {"type": "str", "required": True},
            "data": {"type": "dict", "no_log": True},
            "generate": {"type": "dict"},
            **state_spec(),
        },
        _kv2.run,
    )


if __name__ == "__main__":
    main()
