# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Read the health state of an OpenBao server."""

from __future__ import annotations

DOCUMENTATION = r"""
module: health_info
short_description: Read the initialization, seal and readiness state
version_added: 0.1.0
description:
- Read the state of a server from C(sys/health) without a token.
- The module never changes anything and fails only when the server cannot be reached or returns no state.
- Combine it with C(until), C(retries) and C(delay) to wait for an initialized and unsealed server.
extends_documentation_fragment: [jomrr.bao.connection]
attributes:
  check_mode:
    support: full
    description: Reads the same state in check mode.
  diff_mode:
    support: none
    description: The module reads state and returns no diff.
options: {}
"""

EXAMPLES = r"""
- name: Wait for an initialized and unsealed server
  jomrr.bao.health_info:
    url: https://bao.example.test:8200
    ca_file: /etc/pki/tls/certs/bao-ca.pem
  register: bao_health
  until: bao_health is succeeded and bao_health.ready
  retries: 20
  delay: 3

- name: Stop when the server was never initialized
  ansible.builtin.assert:
    that: bao_health.initialized
"""

RETURN = r"""
initialized:
  description: Whether the server storage is initialized.
  type: bool
  returned: success
sealed:
  description: Whether the server is sealed.
  type: bool
  returned: success
standby:
  description: Whether the server is a standby node; a sealed server reports V(true).
  type: bool
  returned: success
ready:
  description: Whether the server is initialized, unsealed and active.
  type: bool
  returned: success
version:
  description: Server version.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _health
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module({}, _health.run, token=False)


if __name__ == "__main__":
    main()
