# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Revoke an OpenBao token by its accessor."""

from __future__ import annotations

DOCUMENTATION = r"""
module: token_revoke
short_description: Revoke another token by its accessor
version_added: 0.1.0
description:
- Revoke a token through C(auth/token/revoke-accessor) with the session passed as O(token).
- Use it for a token that cannot call the API itself, for example a verification token whose
  network binding excludes the controller.
- An accessor without a token, such as an already revoked one, is reported unchanged.
- To end the own session use M(jomrr.bao.logout); M(jomrr.bao.approle_info) shows the complete verification flow.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action]
options:
  accessor:
    description: Accessor of the token to revoke, as returned by M(jomrr.bao.login).
    type: str
    required: true
    version_added: 0.1.0
"""

EXAMPLES = r"""
# bao_probe is the registered result of jomrr.bao.login for the verification token.
- name: Revoke the verification token with the retained session
  jomrr.bao.token_revoke:
    url: https://bao.example.test:8200
    ca_file: /etc/pki/tls/certs/bao-ca.pem
    token: "{{ bao_token }}"
    accessor: "{{ bao_probe.accessor }}"
  when: bao_probe.accessor is defined
"""

RETURN = r"""
# The module returns only the standard fields; msg tells whether a token was revoked.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _session
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module({"accessor": {"type": "str", "required": True}}, _session.revoke)


if __name__ == "__main__":
    main()
