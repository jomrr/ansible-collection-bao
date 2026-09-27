# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Configure the signing key of an OpenBao SSH engine."""

from __future__ import annotations

DOCUMENTATION = r"""
module: ssh_ca
short_description: Generate or import the SSH certificate authority key
version_added: 0.1.0
description:
- Configure C(config/ca) of an SSH secrets engine by generating a signing key or importing a key pair.
- An engine that already has a signing key is reported unchanged; a different imported O(public_key) fails instead of replacing it.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action, jomrr.bao.options.ssh_mount]
attributes:
  check_mode:
    support: full
    description: Reads the CA configuration and reports the pending generation without creating keys.
options:
  key_type:
    description: Type of a generated signing key.
    type: str
    choices: [ssh-rsa, rsa, ecdsa, ec, ed25519]
    version_added: 0.1.0
  key_bits:
    description: Size of a generated signing key.
    type: int
    version_added: 0.1.0
  private_key:
    description: PEM private key to import instead of generating one.
    type: str
    version_added: 0.1.0
  public_key:
    description: OpenSSH public key matching O(private_key).
    type: str
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Generate the SSH signing key
  jomrr.bao.ssh_ca:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: ssh
    key_type: ed25519
  register: bao_ssh_ca

- name: Distribute the CA public key
  ansible.builtin.debug:
    var: bao_ssh_ca.public_key
"""

RETURN = r"""
public_key:
  description: OpenSSH public key of the signing key; V(null) in check mode before creation.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _ssh
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "key_type": {
                "type": "str",
                "choices": ["ssh-rsa", "rsa", "ecdsa", "ec", "ed25519"],
            },
            "key_bits": {"type": "int"},
            "private_key": {"type": "str", "no_log": True},
            "public_key": {"type": "str"},
        },
        _ssh.run_ca,
        required_together=[("private_key", "public_key")],
    )


if __name__ == "__main__":
    main()
