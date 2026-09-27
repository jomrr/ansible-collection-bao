# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Userpass user state module."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.modules import userpass_user
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

PATH = "auth/users/users/operator"
CURRENT = {
    "token_policies": ["operator"],
    "token_bound_cidrs": ["192.0.2.10"],
    "token_ttl": 1800,
}
PASSWORD = "recognizable-initial-password"


class UserpassTests(unittest.TestCase):
    """Passwords are written only at creation and never appear in output."""

    def test_create_requires_password(self) -> None:
        """A missing user without a password fails before writing."""
        client = FakeClient()
        result = run_module_under_test(
            userpass_user, {"name": "operator", "mount": "users"}, client
        )
        self.assertTrue(result["failed"])
        self.assertEqual(client.writes(), [])

    def test_create(self) -> None:
        """A missing user is created with the password."""
        client = FakeClient()
        inputs = {
            "name": "operator",
            "mount": "users",
            "password": PASSWORD,
            "token_policies": ["operator"],
        }
        result = run_module_under_test(userpass_user, inputs, client)
        self.assertTrue(result["changed"])
        expected = {"token_policies": ["operator"], "password": PASSWORD}
        self.assertEqual(client.writes(), [("POST", PATH, expected)])
        self.assertNotIn(PASSWORD, str(result["diff"]))

    def test_update_keeps_password(self) -> None:
        """An existing user is updated without sending a password."""
        client = FakeClient({("GET", PATH): CURRENT})
        inputs = {
            "name": "operator",
            "mount": "users",
            "password": "ignored",
            "token_policies": ["reader"],
        }
        result = run_module_under_test(userpass_user, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(
            client.writes(), [("POST", PATH, {"token_policies": ["reader"]})]
        )

    def test_unchanged_and_check_mode(self) -> None:
        """Matching settings produce no write; check mode predicts drift."""
        inputs = {
            "name": "operator",
            "mount": "users",
            "token_policies": ["operator"],
            "token_ttl": "30m",
        }
        client = FakeClient({("GET", PATH): CURRENT})
        self.assertFalse(
            run_module_under_test(userpass_user, inputs, client)["changed"]
        )
        inputs["token_ttl"] = "1h"
        client = FakeClient({("GET", PATH): CURRENT})
        result = run_module_under_test(userpass_user, inputs, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])

    def test_absent(self) -> None:
        """Absent deletes an existing user once."""
        client = FakeClient({("GET", PATH): CURRENT})
        inputs = {"name": "operator", "mount": "users", "state": "absent"}
        self.assertTrue(run_module_under_test(userpass_user, inputs, client)["changed"])
        self.assertEqual(client.writes(), [("DELETE", PATH, None)])
        client = FakeClient()
        self.assertFalse(
            run_module_under_test(userpass_user, inputs, client)["changed"]
        )
