# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Duration parsing for comparing OpenBao TTL values; not a public API."""

from __future__ import annotations

import re

_UNITS = {
    "ns": 1e-9,
    "us": 1e-6,
    "µs": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}
_PART = re.compile(r"(\d+(?:\.\d+)?)(ns|us|µs|ms|s|m|h|d)")


def to_seconds(value: object) -> int | None:
    """Convert seconds or a Go style duration such as C(1h30m) to whole seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    total = 0.0
    position = 0
    for match in _PART.finditer(text):
        if match.start() != position:
            break
        total += float(match.group(1)) * _UNITS[match.group(2)]
        position = match.end()
    if position != len(text) or position == 0:
        raise ValueError(f"invalid duration: {text!r}")
    return round(total)
