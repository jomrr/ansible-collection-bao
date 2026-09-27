# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Shared option documentation for the jomrr.bao modules."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class ModuleDocFragment:
    """Ansible documentation fragments."""

    DOCUMENTATION: ClassVar[str] = r"""
options:
  state:
    description: Whether the resource exists.
    type: str
    choices: [present, absent]
    default: present
    version_added: 0.1.0
"""

    TOKEN: ClassVar[str] = r"""
options:
  token_policies:
    description: Policies attached to issued tokens.
    type: list
    elements: str
    version_added: 0.1.0
  token_bound_cidrs:
    description: Networks allowed to use issued tokens; a host address equals its C(/32) or C(/128) network.
    type: list
    elements: str
    version_added: 0.1.0
  token_ttl:
    description: Initial token TTL as seconds or duration.
    type: str
    version_added: 0.1.0
  token_max_ttl:
    description: Maximum token TTL as seconds or duration.
    type: str
    version_added: 0.1.0
  token_explicit_max_ttl:
    description: Explicit maximum token TTL as seconds or duration.
    type: str
    version_added: 0.1.0
  token_num_uses:
    description: Number of uses per token; V(0) is unlimited.
    type: int
    version_added: 0.1.0
  token_period:
    description: Period for periodic tokens as seconds or duration.
    type: str
    version_added: 0.1.0
  token_no_default_policy:
    description: Do not attach the default policy to issued tokens.
    type: bool
    version_added: 0.1.0
  token_type:
    description: Token type.
    type: str
    choices: [default, service, batch]
    version_added: 0.1.0
"""

    APPROLE_MOUNT: ClassVar[str] = r"""
options:
  mount:
    description: AppRole authentication mount.
    type: str
    default: approle
    version_added: 0.1.0
"""

    PKI_MOUNT: ClassVar[str] = r"""
options:
  mount:
    description: PKI secrets engine mount.
    type: str
    required: true
    version_added: 0.1.0
"""

    SSH_MOUNT: ClassVar[str] = r"""
options:
  mount:
    description: SSH secrets engine mount.
    type: str
    required: true
    version_added: 0.1.0
"""
