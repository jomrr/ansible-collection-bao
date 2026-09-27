# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Log in to OpenBao with an AppRole."""

from __future__ import annotations

DOCUMENTATION = r"""
module: login
short_description: Log in with an AppRole and return a session token
version_added: 0.1.0
description:
- Log in at an AppRole authentication mount and return the client token.
- Register the result with C(no_log) and keep the token in a fact for the other modules.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.action,
  jomrr.bao.options.approle_mount]
attributes:
  check_mode:
    support: full
    description: Reports the pending login; RV(token) is then V(null).
options:
  role_id:
    description: Role ID of the AppRole.
    type: str
    required: true
    version_added: 0.1.0
  secret_id:
    description: Secret ID of the AppRole.
    type: str
    required: true
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Open an OpenBao session
  jomrr.bao.login:
    url: https://bao.example.test:8200
    ca_file: /etc/pki/tls/certs/bao-ca.pem
    mount: ansible
    role_id: "{{ bao_role_id }}"
    secret_id: "{{ bao_secret_id }}"
  register: bao_login
  no_log: true
  check_mode: false
  changed_when: false

- name: Keep the session token
  ansible.builtin.set_fact:
    bao_token: "{{ bao_login.token }}"
  no_log: true
"""

RETURN = r"""
token:
  description: Client token of the new session; V(null) in check mode.
  type: str
  returned: success
accessor:
  description: Token accessor.
  type: str
  returned: success
lease_duration:
  description: Token lifetime in seconds.
  type: int
  returned: success
policies:
  description: Policies attached to the token.
  type: list
  elements: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _session
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "default": "approle"},
            "role_id": {"type": "str", "required": True},
            "secret_id": {"type": "str", "required": True, "no_log": True},
        },
        _session.login,
        token=False,
    )


if __name__ == "__main__":
    main()
