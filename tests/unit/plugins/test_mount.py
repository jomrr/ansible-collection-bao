# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Mount state module."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.modules import mount
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

KV = {
    "type": "kv",
    "description": "Application secrets",
    "options": {"version": "2"},
    "config": {"default_lease_ttl": 0, "max_lease_ttl": 0},
}
LISTING = {("GET", "sys/mounts"): {"kv/": KV, "cubbyhole/": {"type": "cubbyhole"}}}


class MountTests(unittest.TestCase):
    """Enable, tune, protect and disable mounts."""

    def test_create_kv_defaults_to_version_2(self) -> None:
        """A missing KV mount is enabled with version 2 and tuning config."""
        client = FakeClient()
        inputs = {
            "path": "kv",
            "type": "kv",
            "description": "x",
            "max_lease_ttl": "24h",
        }
        result = run_module_under_test(mount, inputs, client)
        self.assertTrue(result["changed"])
        body = {
            "type": "kv",
            "description": "x",
            "config": {"max_lease_ttl": "24h"},
            "options": {"version": "2"},
        }
        self.assertEqual(client.writes(), [("POST", "sys/mounts/kv", body)])
        self.assertEqual(result["diff"]["after"]["options"], {"version": "2"})

    def test_create_auth_mount(self) -> None:
        """Authentication methods use the sys/auth API."""
        client = FakeClient()
        run_module_under_test(
            mount, {"path": "approle", "kind": "auth", "type": "approle"}, client
        )
        self.assertEqual(
            client.writes(), [("POST", "sys/auth/approle", {"type": "approle"})]
        )

    def test_unchanged(self) -> None:
        """Matching description and TTLs produce no write."""
        client = FakeClient(LISTING)
        inputs = {
            "path": "kv",
            "type": "kv",
            "description": "Application secrets",
            "max_lease_ttl": 0,
        }
        self.assertFalse(run_module_under_test(mount, inputs, client)["changed"])
        self.assertEqual(client.writes(), [])

    def test_tune_only_changed_fields(self) -> None:
        """Drifted tuning is written through the tune endpoint, not in check mode."""
        inputs = {
            "path": "kv",
            "type": "kv",
            "description": "Changed",
            "max_lease_ttl": "2h",
        }
        client = FakeClient(LISTING)
        result = run_module_under_test(mount, inputs, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])
        self.assertEqual(result["diff"]["before"]["max_lease_ttl"], 0)
        self.assertEqual(result["diff"]["after"]["max_lease_ttl"], 7200)
        client = FakeClient(LISTING)
        run_module_under_test(mount, inputs, client)
        expected = {"description": "Changed", "max_lease_ttl": "2h"}
        self.assertEqual(client.writes(), [("POST", "sys/mounts/kv/tune", expected)])

    def test_type_and_version_protection(self) -> None:
        """Another type or KV version fails without writing."""
        for inputs in (
            {"path": "kv", "type": "pki"},
            {"path": "kv", "type": "kv", "options": {"version": "1"}},
        ):
            with self.subTest(inputs=inputs):
                client = FakeClient(LISTING)
                result = run_module_under_test(mount, inputs, client)
                self.assertTrue(result["failed"])
                self.assertIn("migrate it explicitly", result["msg"])
                self.assertEqual(client.writes(), [])

    def test_absent(self) -> None:
        """Absent disables an existing mount once."""
        client = FakeClient(LISTING)
        result = run_module_under_test(mount, {"path": "kv", "state": "absent"}, client)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", "sys/mounts/kv", None)])
        client = FakeClient()
        self.assertFalse(
            run_module_under_test(mount, {"path": "kv", "state": "absent"}, client)[
                "changed"
            ]
        )
