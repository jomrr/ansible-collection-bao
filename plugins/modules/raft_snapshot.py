# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Save and restore OpenBao raft snapshots."""

from __future__ import annotations

DOCUMENTATION = r"""
module: raft_snapshot
short_description: Save a raft snapshot to a file and restore it on request
version_added: 0.1.0
description:
- Save a snapshot of the integrated raft storage to a file on the host running the module.
- An existing file is kept unless O(overwrite) is set, so a path is written once; use a path with
  a timestamp for recurring backups.
- The snapshot is downloaded into a private temporary file in the target directory and moved
  into place only after the download completed.
- Restoring happens only with O(state=restored). It replaces the complete server state with the
  content of the snapshot.
- A snapshot contains all data of the server. The file mode defaults to V(0600).
- Large snapshots can take longer than the default O(timeout).
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, ansible.builtin.files]
attributes:
  check_mode:
    support: full
    description: Reports the pending download or restore from the state of the file without contacting the server.
  diff_mode:
    support: none
    description: The module returns no diff.
requirements:
- A server using the integrated raft storage.
options:
  path:
    description: Snapshot file on the host running the module; the directory must exist.
    type: path
    required: true
    version_added: 0.1.0
  state:
    description: V(saved) writes a snapshot to O(path); V(restored) installs the snapshot from O(path).
    type: str
    choices: [saved, restored]
    default: saved
    version_added: 0.1.0
  overwrite:
    description: Replace an existing file with a new snapshot.
    type: bool
    default: false
    version_added: 0.1.0
  force:
    description: Restore without the check that the seal keys match the snapshot.
    type: bool
    default: false
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Save a daily snapshot on the controller
  jomrr.bao.raft_snapshot:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: "/var/backups/openbao/raft-{{ ansible_date_time.date }}.snap"
    timeout: 300
  delegate_to: localhost

- name: Restore a snapshot
  jomrr.bao.raft_snapshot:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: /var/backups/openbao/raft-2026-09-28.snap
    state: restored
    timeout: 300
  delegate_to: localhost
"""

RETURN = r"""
path:
  description: Snapshot file.
  type: str
  returned: success
size:
  description: Size of the snapshot file in bytes; V(null) while the file does not exist.
  type: int
  returned: success
checksum:
  description: SHA-256 digest of the snapshot file; V(null) while the file does not exist.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _raft
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_file_module

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_file_module(
        {
            "path": {"type": "path", "required": True},
            "state": {
                "type": "str",
                "choices": ["saved", "restored"],
                "default": "saved",
            },
            "overwrite": {"type": "bool", "default": False},
            "force": {"type": "bool", "default": False},
        },
        _raft.run,
    )


if __name__ == "__main__":
    main()
