# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Shared connection and mode documentation for the jomrr.bao modules."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class ModuleDocFragment:
    """Ansible documentation fragments."""

    DOCUMENTATION: ClassVar[str] = r"""
author: [Jonas Mauer (@jomrr)]
requirements:
- Python 3.12 on the host running the module, typically the controller via C(delegate_to).
notes:
- TLS verification is always enabled; use O(ca_file) for a private trust anchor.
- The token and other secret options are never logged, returned or shown in diffs.
options:
  url:
    description: HTTPS API origin of the OpenBao server without a trailing slash or path.
    type: str
    required: true
    version_added: 0.1.0
  ca_file:
    description: CA bundle verifying the server certificate; omitted to use the system trust store.
    type: path
    version_added: 0.1.0
  timeout:
    description: HTTP request timeout in seconds.
    type: int
    default: 30
    version_added: 0.1.0
"""

    TOKEN: ClassVar[str] = r"""
options:
  token:
    description: Session token, typically obtained with M(jomrr.bao.login).
    type: str
    required: true
    version_added: 0.1.0
"""

    STATE: ClassVar[str] = r"""
attributes:
  check_mode:
    support: full
    description: Reads the current state and reports the predicted change without writing.
  diff_mode:
    support: full
    description: Returns before and after views without secret values.
options: {}
"""

    ACTION: ClassVar[str] = r"""
attributes:
  check_mode:
    support: full
    description: Reports the pending action without contacting the server.
  diff_mode:
    support: none
    description: Actions return no diff.
options: {}
"""
