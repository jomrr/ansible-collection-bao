# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao auth and secrets mounts."""

from __future__ import annotations

DOCUMENTATION = r"""
module: mount
short_description: Manage auth and secrets mounts
version_added: 0.1.0
description:
- Enable, tune or disable an authentication method or secrets engine mount.
- An existing mount of another type or another KV version is never replaced; the module fails instead.
- Disabling a mount removes all data stored below it.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.state, jomrr.bao.options]
options:
  path:
    description: Mount path without surrounding slashes.
    type: str
    required: true
    version_added: 0.1.0
  kind:
    description: Whether the path is a secrets engine or an authentication method.
    type: str
    choices: [secret, auth]
    default: secret
    version_added: 0.1.0
  type:
    description: Backend type such as V(kv), V(pki), V(ssh), V(approle) or V(userpass); required when O(state=present).
    type: str
    version_added: 0.1.0
  description:
    description: Mount description.
    type: str
    version_added: 0.1.0
  default_lease_ttl:
    description: Default lease TTL as seconds or duration; V(0) inherits the server default.
    type: str
    version_added: 0.1.0
  max_lease_ttl:
    description: Maximum lease TTL as seconds or duration; V(0) inherits the server default.
    type: str
    version_added: 0.1.0
  options:
    description: Backend options set at creation; V(kv) mounts default to C(version 2).
    type: dict
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Enable a KV version 2 store
  jomrr.bao.mount:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: kv
    type: kv
    description: Application secrets

- name: Enable an AppRole authentication mount with tuned TTLs
  jomrr.bao.mount:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: approle
    kind: auth
    type: approle
    default_lease_ttl: 1h
    max_lease_ttl: 24h

- name: Remove a secrets engine and its data
  jomrr.bao.mount:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: legacy
    state: absent
"""

RETURN = r"""
# The module returns only the standard fields; the diff holds type, options and tuning.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _mount
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    run_module,
    typed_spec,
)

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        typed_spec(
            {
                "kind": {
                    "type": "str",
                    "choices": ["secret", "auth"],
                    "default": "secret",
                },
                "default_lease_ttl": {"type": "str"},
                "max_lease_ttl": {"type": "str"},
            }
        ),
        _mount.run,
        required_if=[("state", "present", ("type",))],
    )


if __name__ == "__main__":
    main()
