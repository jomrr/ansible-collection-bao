# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Health state read for ready, sealed, uninitialized and standby servers."""

from __future__ import annotations

import unittest
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import health_info
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

QUERY = {"standbyok": "true", "sealedcode": "200", "uninitcode": "200"}
READY = {"initialized": True, "sealed": False, "standby": False, "version": "2.7.0"}


def read(body: Any, *, check_mode: bool = False) -> tuple[dict[str, Any], FakeClient]:
    """Run the module against one health response."""
    client = FakeClient({("READ", "sys/health"): body})
    return run_module_under_test(health_info, {}, client, check_mode=check_mode), client


class HealthInfoTests(unittest.TestCase):
    """The state comes from the body and the module never reports a change."""

    def test_states(self) -> None:
        """Ready requires an initialized, unsealed and active server."""
        cases: list[tuple[dict[str, Any], bool]] = [
            (READY, True),
            ({**READY, "sealed": True, "standby": True}, False),
            ({**READY, "initialized": False, "sealed": True, "standby": True}, False),
            ({**READY, "standby": True}, False),
        ]
        for body, ready in cases:
            with self.subTest(body=body):
                result, client = read(body)
                self.assertFalse(result["changed"])
                self.assertEqual(result["ready"], ready)
                for name in ("initialized", "sealed", "standby"):
                    self.assertEqual(result[name], body[name])
                self.assertEqual(result["version"], "2.7.0")
                self.assertEqual(client.calls, [("READ", "sys/health", QUERY)])

    def test_check_mode_reads_the_same_state(self) -> None:
        """Check mode performs the read and returns the same fields."""
        result, client = read(READY, check_mode=True)
        self.assertTrue(result["ready"])
        self.assertFalse(result["changed"])
        self.assertEqual(len(client.calls), 1)

    def test_failures(self) -> None:
        """An unreachable server or a response without state fails."""
        error = BaoError("GET sys/health failed: [Errno 111] Connection refused")
        bodies: tuple[Any, ...] = (error, None, {"errors": []})
        for body in bodies:
            with self.subTest(body=body):
                result, _client = read(body)
                self.assertTrue(result["failed"])
                self.assertIn("sys/health", result["msg"])
