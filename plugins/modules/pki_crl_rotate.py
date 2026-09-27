# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Rotate the CRL of an OpenBao PKI engine."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_crl_rotate
short_description: Rotate the certificate revocation list
version_added: 0.1.0
description:
- Trigger a rebuild of the CRL or the delta CRL of a PKI secrets engine.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action, jomrr.bao.options.pki_mount]
options:
  delta:
    description: Rotate the delta CRL instead of the full CRL.
    type: bool
    default: false
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Publish revocations immediately
  jomrr.bao.pki_crl_rotate:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
"""

RETURN = r"""
success:
  description: Result reported by the server; V(null) in check mode.
  type: bool
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
            "delta": {"type": "bool", "default": False},
        },
        _pki_ca.run_crl_rotate,
    )


if __name__ == "__main__":
    main()
