# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Revoke the OpenBao session token."""

from __future__ import annotations

DOCUMENTATION = r"""
module: token_revoke
short_description: Revoke the session token
version_added: 0.1.0
description:
- Revoke the token passed as O(token) through C(auth/token/revoke-self).
- Call it at the end of a run, typically in an C(always) block.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action]
options: {}
"""

EXAMPLES = r"""
- name: Close the OpenBao session
  jomrr.bao.token_revoke:
    url: https://bao.example.test:8200
    ca_file: /etc/pki/tls/certs/bao-ca.pem
    token: "{{ bao_token }}"
  check_mode: false
  changed_when: false
"""

RETURN = r"""
# The module returns only the standard fields.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _session
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module({}, _session.revoke)


if __name__ == "__main__":
    main()
