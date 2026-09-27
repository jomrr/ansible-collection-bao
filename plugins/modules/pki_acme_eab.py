# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Create OpenBao ACME external account binding keys."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_acme_eab
short_description: Create an ACME external account binding key
version_added: 0.1.0
description:
- Create an external account binding key for one ACME client, optionally bound to a role or issuer directory.
- Every run creates a new key; register the result with C(no_log) and hand RV(id) and RV(key) to the client.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action, jomrr.bao.options.pki_mount]
options:
  role:
    description: Bind the key to the ACME directory of this role.
    type: str
    version_added: 0.1.0
  issuer:
    description: Bind the key to the ACME directory of this issuer.
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Create an account binding for the web server
  jomrr.bao.pki_acme_eab:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    role: web-server
  register: bao_eab
  no_log: true
"""

RETURN = r"""
id:
  description: Key identifier for the ACME client.
  type: str
  returned: success
key:
  description: Base64 encoded HMAC key for the ACME client.
  type: str
  returned: success
key_type:
  description: Key type reported by the server.
  type: str
  returned: success
acme_directory:
  description: ACME directory the key is bound to.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _pki_ca
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "role": {"type": "str"},
            "issuer": {"type": "str"},
        },
        _pki_ca.run_eab,
    )


if __name__ == "__main__":
    main()
