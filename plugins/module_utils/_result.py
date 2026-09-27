# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Result structures returned by the modules; not a public API."""

from __future__ import annotations

from typing import Any


def state_result(
    changed: bool, before: dict[str, Any], after: dict[str, Any], **extra: Any
) -> dict[str, Any]:
    """Return a state module result with a before and after diff."""
    return {"changed": changed, "diff": {"before": before, "after": after}, **extra}


def action_result(changed: bool, msg: str, **extra: Any) -> dict[str, Any]:
    """Return an action module result."""
    return {"changed": changed, "msg": msg, **extra}


def key_view(mapping: dict[str, Any] | None) -> dict[str, Any]:
    """Describe a secret mapping by its keys only."""
    return {"keys": sorted(mapping or {})}
