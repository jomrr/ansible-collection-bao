# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Duration conversion used for TTL comparisons."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.module_utils._duration import to_seconds


class DurationTests(unittest.TestCase):
    """Go style durations, integers and numeric strings compare as seconds."""

    def test_values(self) -> None:
        """Known inputs convert to whole seconds."""
        cases: list[tuple[object, int | None]] = [
            (None, None),
            (0, 0),
            (3600, 3600),
            ("3600", 3600),
            ("", 0),
            ("1h", 3600),
            ("1h30m", 5400),
            ("72h", 259200),
            ("30s", 30),
            ("1.5h", 5400),
            ("2d", 172800),
            ("500ms", 0),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(to_seconds(value), expected)

    def test_invalid(self) -> None:
        """Unknown units and booleans are rejected."""
        for value in ("1x", "h", "1h2", "1 h"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                to_seconds(value)
