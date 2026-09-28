# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao audit devices."""

from __future__ import annotations

DOCUMENTATION = r"""
module: audit_device
short_description: Manage audit devices
version_added: 0.1.0
description:
- Enable or disable an audit device through the API, for servers whose configuration file is
  provisioned elsewhere.
- The server accepts new audit devices through the API only while its configuration sets
  C(unsafe_allow_api_audit_creation); the O(options[prefix]) option also needs C(allow_audit_log_prefixing).
- Audit devices cannot be modified. An existing device that differs from the requested settings
  fails the module unless O(replace) is set.
- Devices declared in the server configuration are compared like other devices, but the server
  refuses to disable them.
- The token needs the C(sudo) capability on C(sys/audit).
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.state, jomrr.bao.options]
options:
  path:
    description: Path of the audit device without surrounding slashes.
    type: str
    required: true
    version_added: 0.1.0
  type:
    description: Device type such as V(file), V(http), V(socket) or V(syslog); required when O(state=present).
    type: str
    version_added: 0.1.0
  description:
    description: Description of the audit device; not compared when omitted.
    type: str
    version_added: 0.1.0
  options:
    description:
    - Options of the device, such as C(file_path) of a V(file) device; not compared when omitted together with O(secret_options).
    - The server stores every value as string. Quote values such as C(mode) to keep their spelling.
    - The server resolves C(env://) and C(file://) references in C(uri) and header values of an V(http) device.
    type: dict
    version_added: 0.1.0
  secret_options:
    description:
    - Options of the device that hold credentials, such as C(headers) or a C(uri) with credentials of an V(http) device.
    - Merged into O(options) for the request and the comparison; the values are never shown.
    type: dict
    version_added: 0.1.0
  replace:
    description:
    - Disable an existing device that differs and enable it with the requested settings.
    - The new device creates a new salt, so values can no longer be compared with the hashes in earlier audit logs.
    - The device records nothing between both calls. When the new device is rejected, the previous one is enabled again.
    type: bool
    default: false
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Enable a file audit device
  jomrr.bao.audit_device:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: file
    type: file
    description: Audit log for the log collector
    options:
      file_path: /var/log/openbao/audit.json
      mode: "0640"

- name: Send audit records to a collector with credentials
  jomrr.bao.audit_device:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: collector
    type: http
    options:
      uri: https://logs.example.test/openbao
    secret_options:
      headers: "{{ {'Authorization': ['Bearer ' ~ collector_token]} | to_json }}"

- name: Replace a device to change its options
  jomrr.bao.audit_device:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: file
    type: file
    options:
      file_path: /var/log/openbao/audit.json
      elide_list_responses: true
    replace: true

- name: Disable an audit device
  jomrr.bao.audit_device:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    path: syslog
    state: absent
"""

RETURN = r"""
# The module returns only the standard fields; the diff holds type, description and options.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _audit
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
                "secret_options": {"type": "dict", "no_log": True},
                "replace": {"type": "bool", "default": False},
            }
        ),
        _audit.run,
        required_if=[("state", "present", ("type",))],
    )


if __name__ == "__main__":
    main()
