# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Generate and rotate OpenBao recovery keys."""

from __future__ import annotations

DOCUMENTATION = r"""
module: recovery_key
short_description: Generate recovery key shares and rotate them on request
version_added: 0.1.0
description:
- Generate recovery key shares on a server that has none, as after declarative self-initialization
  with an auto-unseal seal.
- With O(state=present) existing recovery keys are never touched. Rotation happens only with
  O(state=rotated) and needs the existing shares in O(keys).
- A rotation that fails is cancelled, so the existing shares stay valid and a retry can start.
- The new shares are returned once and cannot be read again. Register the result with C(no_log),
  store the shares outside of this server, or encrypt them with O(pgp_keys).
- Rotation verification is not supported.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.action]
attributes:
  check_mode:
    support: full
    description: Reads the rotation status and reports the pending generation or rotation without creating keys.
requirements:
- OpenBao 2.4 or newer with a seal that supports recovery keys.
options:
  state:
    description: V(present) generates shares only when none exist; V(rotated) replaces the existing shares.
    type: str
    choices: [present, rotated]
    default: present
    version_added: 0.1.0
  shares:
    description: Number of shares to generate.
    type: int
    default: 5
    version_added: 0.1.0
  threshold:
    description: Number of shares needed to use the recovery key.
    type: int
    default: 3
    version_added: 0.1.0
  keys:
    description: Existing shares authorizing a rotation; at least as many as the current threshold.
    type: list
    elements: str
    version_added: 0.1.0
  pgp_keys:
    description: Base64 encoded PGP public keys, one per share, used to encrypt the returned shares.
    type: list
    elements: str
    version_added: 0.1.0
  backup:
    description: Keep a copy of the PGP encrypted shares in the server storage.
    type: bool
    default: false
    version_added: 0.1.0
  force:
    description: Cancel a rotation that is already in progress before starting.
    type: bool
    default: false
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Generate recovery keys after self-initialization
  jomrr.bao.recovery_key:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    shares: 5
    threshold: 3
  register: bao_recovery
  no_log: true

- name: Rotate the recovery keys with three existing shares
  jomrr.bao.recovery_key:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    state: rotated
    shares: 5
    threshold: 3
    keys: "{{ vault_recovery_shares[:3] }}"
  register: bao_recovery
  no_log: true
"""

RETURN = r"""
recovery_keys:
  description: New shares in hexadecimal form, PGP encrypted when O(pgp_keys) is set; empty without a change.
  type: list
  elements: str
  returned: success
recovery_keys_base64:
  description: New shares in base64 form; empty without a change.
  type: list
  elements: str
  returned: success
pgp_fingerprints:
  description: Fingerprints of the PGP keys in the order of the shares.
  type: list
  elements: str
  returned: success
shares:
  description: Number of recovery key shares after the run.
  type: int
  returned: success
threshold:
  description: Threshold of the recovery key after the run.
  type: int
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _recovery
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "state": {
                "type": "str",
                "choices": ["present", "rotated"],
                "default": "present",
            },
            "shares": {"type": "int", "default": 5},
            "threshold": {"type": "int", "default": 3},
            "keys": {"type": "list", "elements": "str", "no_log": True},
            "pgp_keys": {"type": "list", "elements": "str"},
            "backup": {"type": "bool", "default": False},
            "force": {"type": "bool", "default": False},
        },
        _recovery.run,
    )


if __name__ == "__main__":
    main()
