# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""AppRole and Secret ID state modules."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import approle, approle_secret_id
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

ROLE = "auth/approle/role/app"
CURRENT = {
    "bind_secret_id": True,
    "secret_id_bound_cidrs": ["10.1.0.0/24", "10.0.0.1/32"],
    "token_policies": ["b", "a"],
    "token_ttl": 900,
    "token_max_ttl": 3600,
    "secret_id_ttl": 0,
    "secret_id_num_uses": 0,
    "token_bound_cidrs": [],
}
SECRET = "recognizable-secret-id-0123456789abcdef"
LOOKUP = {
    "data": {
        "secret_id_accessor": "acc-1",
        "cidr_list": [],
        "token_bound_cidrs": [],
        "secret_id_ttl": 0,
        "secret_id_num_uses": 0,
        "metadata": {},
    }
}


class AppRoleTests(unittest.TestCase):
    """Role comparison ignores ordering and duration representation."""

    def test_create_with_role_id(self) -> None:
        """A missing role is written and its Role ID pinned."""
        client = FakeClient({("GET", f"{ROLE}/role-id"): {"role_id": "generated"}})
        inputs = {
            "name": "app",
            "role_id": "app",
            "token_policies": ["a"],
            "token_ttl": "15m",
        }
        result = run_module_under_test(approle, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(
            client.writes(),
            [
                ("POST", ROLE, {"token_policies": ["a"], "token_ttl": "15m"}),
                ("POST", f"{ROLE}/role-id", {"role_id": "app"}),
            ],
        )
        self.assertEqual(result["role_id"], "app")

    def test_unchanged(self) -> None:
        """Unsorted lists and duration strings match the current role."""
        responses = {
            ("GET", ROLE): CURRENT,
            ("GET", f"{ROLE}/role-id"): {"role_id": "app"},
        }
        client = FakeClient(responses)
        inputs = {
            "name": "app",
            "role_id": "app",
            "secret_id_bound_cidrs": ["10.0.0.1/32", "10.1.0.0/24"],
            "token_policies": ["a", "b"],
            "token_ttl": "15m",
            "token_max_ttl": 3600,
        }
        result = run_module_under_test(approle, inputs, client)
        self.assertFalse(result["changed"])
        self.assertEqual(client.writes(), [])
        self.assertEqual(result["role_id"], "app")

    def test_update_and_check_mode(self) -> None:
        """Changed settings are written with the full desired set, not in check mode."""
        responses = {
            ("GET", ROLE): CURRENT,
            ("GET", f"{ROLE}/role-id"): {"role_id": "old"},
        }
        inputs = {
            "name": "app",
            "role_id": "new",
            "token_policies": ["a"],
            "token_ttl": "20m",
        }
        client = FakeClient(responses)
        result = run_module_under_test(approle, inputs, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])
        self.assertEqual(result["diff"]["before"]["token_ttl"], 900)
        self.assertEqual(result["diff"]["after"]["token_ttl"], 1200)
        self.assertEqual(result["diff"]["before"]["role_id"], "old")
        client = FakeClient(responses)
        run_module_under_test(approle, inputs, client)
        self.assertEqual(
            client.writes(),
            [
                ("POST", ROLE, {"token_policies": ["a"], "token_ttl": "20m"}),
                ("POST", f"{ROLE}/role-id", {"role_id": "new"}),
            ],
        )

    def test_absent(self) -> None:
        """Absent deletes an existing role once."""
        client = FakeClient({("GET", ROLE): CURRENT})
        result = run_module_under_test(
            approle, {"name": "app", "state": "absent"}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", ROLE, None)])
        client = FakeClient()
        result = run_module_under_test(
            approle, {"name": "app", "state": "absent"}, client
        )
        self.assertFalse(result["changed"])


class SecretIdTests(unittest.TestCase):
    """Custom Secret IDs are registered once, verified on request and destroyed."""

    def test_register_and_verify(self) -> None:
        """A missing Secret ID is registered and the verification token revoked."""
        auth = {"client_token": "verify-token"}
        responses = {
            ("POST", f"{ROLE}/custom-secret-id"): {
                "data": {"secret_id_accessor": "acc-new"}
            },
            ("LOGIN", "auth/approle/login"): auth,
        }
        client = FakeClient(responses)
        inputs = {"role": "app", "secret_id": SECRET, "verify": True, "role_id": "app"}
        result = run_module_under_test(approle_secret_id, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["accessor"], "acc-new")
        self.assertEqual(
            client.writes(),
            [
                ("POST", f"{ROLE}/secret-id/lookup", {"secret_id": SECRET}),
                ("POST", f"{ROLE}/custom-secret-id", {"secret_id": SECRET}),
                (
                    "LOGIN",
                    "auth/approle/login",
                    {"role_id": "app", "secret_id": SECRET},
                ),
                ("POST", "auth/token/revoke-self", {"token": "verify-token"}),
            ],
        )
        self.assertNotIn(SECRET, str(result["diff"]))

    def test_existing_unchanged_and_check_mode(self) -> None:
        """A registered Secret ID is kept; check mode never registers."""
        client = FakeClient({("POST", f"{ROLE}/secret-id/lookup"): LOOKUP})
        result = run_module_under_test(
            approle_secret_id, {"role": "app", "secret_id": SECRET}, client
        )
        self.assertFalse(result["changed"])
        self.assertEqual(result["accessor"], "acc-1")
        self.assertEqual(len(client.writes()), 1)
        client = FakeClient()
        result = run_module_under_test(
            approle_secret_id,
            {"role": "app", "secret_id": SECRET},
            client,
            check_mode=True,
        )
        self.assertTrue(result["changed"])
        self.assertEqual(len(client.writes()), 1)

    def test_registration_options(self) -> None:
        """Restrictions and metadata are sent with the registration."""
        client = FakeClient()
        inputs = {
            "role": "app",
            "secret_id": SECRET,
            "cidr_list": ["192.0.2.0/24"],
            "ttl": "1h",
            "num_uses": 3,
            "metadata": {"team": "ops"},
        }
        run_module_under_test(approle_secret_id, inputs, client)
        body = client.writes()[1][2]
        assert body is not None
        self.assertEqual(body["cidr_list"], ["192.0.2.0/24"])
        self.assertEqual(body["ttl"], "1h")
        self.assertEqual(body["num_uses"], 3)
        self.assertEqual(body["metadata"], '{"team": "ops"}')

    def test_absent(self) -> None:
        """Absent destroys a registered Secret ID once."""
        client = FakeClient({("POST", f"{ROLE}/secret-id/lookup"): LOOKUP})
        inputs = {"role": "app", "secret_id": SECRET, "state": "absent"}
        result = run_module_under_test(approle_secret_id, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(
            client.writes()[1],
            ("POST", f"{ROLE}/secret-id/destroy", {"secret_id": SECRET}),
        )
        client = FakeClient()
        self.assertFalse(
            run_module_under_test(approle_secret_id, inputs, client)["changed"]
        )

    def test_failure_masks_secret(self) -> None:
        """A server error naming the secret is masked."""
        error = BaoError(
            f"POST {ROLE}/custom-secret-id failed with HTTP 400: bad {SECRET}", 400
        )
        client = FakeClient({("POST", f"{ROLE}/custom-secret-id"): error})
        result = run_module_under_test(
            approle_secret_id, {"role": "app", "secret_id": SECRET}, client
        )
        self.assertTrue(result["failed"])
        self.assertNotIn(SECRET, result["msg"])
