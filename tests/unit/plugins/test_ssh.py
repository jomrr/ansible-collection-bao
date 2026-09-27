# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""SSH CA action and SSH role state modules."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import ssh_ca, ssh_role
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

CA = "ssh/config/ca"
PUBLIC = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample ca"
NO_ISSUER = BaoError(
    "GET ssh/config/ca failed with HTTP 400: no default issuer currently configured",
    400,
)
ROLE = "ssh/roles/hosts"
CURRENT_ROLE = {
    "key_type": "ca",
    "allow_host_certificates": True,
    "allow_user_certificates": False,
    "allowed_domains": "example.test,other.test",
    "allowed_users": "",
    "ttl": 28800,
    "max_ttl": 0,
    "default_extensions": {"permit-pty": ""},
    "algorithm_signer": "rsa-sha2-512",
}


class SshCaTests(unittest.TestCase):
    """The signing key is created once and never replaced silently."""

    def test_generate_when_missing(self) -> None:
        """An engine without an issuer gets a generated key."""
        responses = {
            ("GET", CA): NO_ISSUER,
            ("POST", CA): {"data": {"public_key": PUBLIC}},
        }
        client = FakeClient(responses)
        result = run_module_under_test(
            ssh_ca, {"mount": "ssh", "key_type": "ed25519"}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["public_key"], PUBLIC)
        self.assertEqual(
            client.writes(),
            [("POST", CA, {"generate_signing_key": True, "key_type": "ed25519"})],
        )

    def test_existing_and_check_mode(self) -> None:
        """An existing key is unchanged; check mode never writes."""
        client = FakeClient({("GET", CA): {"public_key": PUBLIC}})
        result = run_module_under_test(
            ssh_ca, {"mount": "ssh", "public_key": f"  {PUBLIC} "}, client
        )
        self.assertFalse(result["changed"])
        self.assertEqual(result["public_key"], PUBLIC)
        client = FakeClient({("GET", CA): NO_ISSUER})
        result = run_module_under_test(
            ssh_ca, {"mount": "ssh"}, client, check_mode=True
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])

    def test_import_and_conflict(self) -> None:
        """Imported keys are sent once; a different existing key fails."""
        responses = {("GET", CA): NO_ISSUER, ("POST", CA): None}
        client = FakeClient(responses)
        inputs = {
            "mount": "ssh",
            "private_key": "recognizable-private-key",
            "public_key": PUBLIC,
        }
        result = run_module_under_test(ssh_ca, inputs, client)
        self.assertTrue(result["changed"])
        body = client.writes()[0][2]
        assert body is not None
        self.assertFalse(body["generate_signing_key"])
        self.assertEqual(body["private_key"], "recognizable-private-key")
        client = FakeClient({("GET", CA): {"public_key": "ssh-ed25519 OTHER ca"}})
        result = run_module_under_test(ssh_ca, inputs, client)
        self.assertTrue(result["failed"])
        self.assertIn("different signing key", result["msg"])
        self.assertNotIn("recognizable-private-key", result["msg"])
        self.assertEqual(client.writes(), [])


class SshRoleTests(unittest.TestCase):
    """Lists map to comma strings and writes send the merged role."""

    def test_unchanged(self) -> None:
        """List options equal the stored comma strings and durations."""
        client = FakeClient({("GET", ROLE): CURRENT_ROLE})
        inputs = {
            "mount": "ssh",
            "name": "hosts",
            "allow_host_certificates": True,
            "allowed_domains": ["other.test", "example.test"],
            "ttl": "8h",
            "default_extensions": {"permit-pty": ""},
        }
        self.assertFalse(run_module_under_test(ssh_role, inputs, client)["changed"])
        self.assertEqual(client.writes(), [])

    def test_update_sends_merged_role(self) -> None:
        """A changed TTL is written together with the current settings."""
        client = FakeClient({("GET", ROLE): CURRENT_ROLE})
        inputs = {"mount": "ssh", "name": "hosts", "ttl": "4h"}
        result = run_module_under_test(ssh_role, inputs, client)
        self.assertTrue(result["changed"])
        body = client.writes()[0][2]
        assert body is not None
        self.assertEqual(body["ttl"], "4h")
        self.assertEqual(body["allowed_domains"], "example.test,other.test")
        self.assertEqual(body["algorithm_signer"], "rsa-sha2-512")
        self.assertEqual(result["diff"]["after"]["ttl"], 14400)

    def test_create_and_absent(self) -> None:
        """A missing role is created with comma strings; absent deletes it."""
        client = FakeClient()
        inputs = {
            "mount": "ssh",
            "name": "hosts",
            "allow_user_certificates": True,
            "allowed_users": ["root", "admin"],
        }
        run_module_under_test(ssh_role, inputs, client)
        expected = {
            "key_type": "ca",
            "allow_user_certificates": True,
            "allowed_users": "root,admin",
        }
        self.assertEqual(client.writes(), [("POST", ROLE, expected)])
        client = FakeClient({("GET", ROLE): CURRENT_ROLE})
        result = run_module_under_test(
            ssh_role, {"mount": "ssh", "name": "hosts", "state": "absent"}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", ROLE, None)])
