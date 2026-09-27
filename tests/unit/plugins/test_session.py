# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Login and token revocation actions."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import login, token_revoke
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

AUTH = {
    "client_token": "new-session-token",
    "accessor": "accessor-1",
    "lease_duration": 900,
    "token_policies": ["default", "app"],
}


class SessionTests(unittest.TestCase):
    """Actions always report a change and skip the API in check mode."""

    def test_login(self) -> None:
        """A login returns the token and is always changed."""
        client = FakeClient({("LOGIN", "auth/ansible/login"): AUTH})
        inputs = {
            "mount": "ansible",
            "role_id": "rid",
            "secret_id": "recognizable-secret",
        }
        result = run_module_under_test(login, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["token"], "new-session-token")
        self.assertEqual(result["accessor"], "accessor-1")
        self.assertEqual(result["lease_duration"], 900)
        self.assertEqual(result["policies"], ["default", "app"])
        self.assertEqual(
            client.calls[0][2], {"role_id": "rid", "secret_id": "recognizable-secret"}
        )

    def test_login_check_mode(self) -> None:
        """Check mode reports the login without calling the API."""
        client = FakeClient()
        inputs = {"role_id": "rid", "secret_id": "recognizable-secret"}
        result = run_module_under_test(login, inputs, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertIsNone(result["token"])
        self.assertEqual(client.calls, [])

    def test_login_failure_masks_secret(self) -> None:
        """A rejected login fails without exposing the secret ID."""
        error = BaoError(
            "POST auth/approle/login failed with HTTP 400: bad recognizable-secret"
        )
        client = FakeClient({("LOGIN", "auth/approle/login"): error})
        inputs = {"role_id": "rid", "secret_id": "recognizable-secret"}
        result = run_module_under_test(login, inputs, client)
        self.assertTrue(result["failed"])
        self.assertNotIn("recognizable-secret", result["msg"])
        self.assertIn("HTTP 400", result["msg"])

    def test_revoke(self) -> None:
        """Revocation uses the connection token and skips the call in check mode."""
        client = FakeClient()
        self.assertTrue(run_module_under_test(token_revoke, {}, client)["changed"])
        self.assertEqual(
            client.calls, [("POST", "auth/token/revoke-self", {"token": "fake-token"})]
        )
        client = FakeClient()
        run_module_under_test(token_revoke, {}, client, check_mode=True)
        self.assertEqual(client.calls, [])
