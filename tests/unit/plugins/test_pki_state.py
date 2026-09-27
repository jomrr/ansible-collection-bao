# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""PKI configuration, ACME, role and issuer state modules."""

from __future__ import annotations

import unittest
from typing import Any

from ansible_collections.jomrr.bao.plugins.modules import (
    pki_acme,
    pki_config,
    pki_issuer,
    pki_role,
)
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

URLS = {
    "issuing_certificates": [],
    "crl_distribution_points": [],
    "delta_crl_distribution_points": [],
    "ocsp_servers": [],
    "enable_templating": False,
}
CRL = {"expiry": "72h", "disable": False, "auto_rebuild": False, "ocsp_expiry": "12h"}
ISSUERS = {
    "keys": ["id-1"],
    "key_info": {"id-1": {"issuer_name": "root", "is_default": True}},
}
ISSUER: dict[str, Any] = {
    "issuer_id": "id-1",
    "issuer_name": "root",
    "usage": "crl-signing,issuing-certificates,ocsp-signing,read-only",
    "issuing_certificates": [],
    "crl_distribution_points": [],
    "manual_chain": None,
    "leaf_not_after_behavior": "err",
}


class PkiConfigTests(unittest.TestCase):
    """Sections are compared by their given keys only."""

    def test_unchanged_sections(self) -> None:
        """Matching URL lists and CRL durations produce no write."""
        responses = {("GET", "pki/config/urls"): URLS, ("GET", "pki/config/crl"): CRL}
        client = FakeClient(responses)
        inputs = {
            "mount": "pki",
            "urls": {"issuing_certificates": [], "enable_templating": False},
            "crl": {"expiry": 259200, "auto_rebuild": False},
        }
        result = run_module_under_test(pki_config, inputs, client)
        self.assertFalse(result["changed"])
        self.assertEqual(client.writes(), [])
        self.assertEqual(set(result["diff"]["before"]), {"urls", "crl"})

    def test_changed_section_writes_only_that_section(self) -> None:
        """A drifted cluster path is written; untouched sections are not read."""
        responses = {("GET", "pki/config/cluster"): {"path": "", "aia_path": ""}}
        client = FakeClient(responses)
        inputs = {
            "mount": "pki",
            "cluster": {"path": "https://bao.example.test/v1/pki"},
        }
        result = run_module_under_test(pki_config, inputs, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])
        client = FakeClient(responses)
        run_module_under_test(pki_config, inputs, client)
        expected = {"path": "https://bao.example.test/v1/pki"}
        self.assertEqual(client.writes(), [("POST", "pki/config/cluster", expected)])
        self.assertEqual(
            [call[1] for call in client.calls if call[0] == "GET"],
            ["pki/config/cluster"],
        )

    def test_acme(self) -> None:
        """ACME settings are written when they differ."""
        current = {
            "enabled": False,
            "allowed_roles": ["*"],
            "eab_policy": "not-required",
        }
        client = FakeClient({("GET", "pki/config/acme"): current})
        inputs = {"mount": "pki", "enabled": True, "allowed_roles": ["*"]}
        result = run_module_under_test(pki_acme, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(
            client.writes(),
            [("POST", "pki/config/acme", {"enabled": True, "allowed_roles": ["*"]})],
        )
        client = FakeClient({("GET", "pki/config/acme"): {**current, "enabled": True}})
        self.assertFalse(run_module_under_test(pki_acme, inputs, client)["changed"])


class PkiRoleTests(unittest.TestCase):
    """Roles are created with POST and updated with a merge patch."""

    def test_create(self) -> None:
        """A missing role is posted with the given fields."""
        client = FakeClient()
        inputs = {
            "mount": "pki",
            "name": "web",
            "allowed_domains": ["example.test"],
            "ttl": "24h",
        }
        result = run_module_under_test(pki_role, inputs, client)
        self.assertTrue(result["changed"])
        expected = {"allowed_domains": ["example.test"], "ttl": "24h"}
        self.assertEqual(client.writes(), [("POST", "pki/roles/web", expected)])

    def test_update_patches_and_unchanged(self) -> None:
        """Duration and list differences patch the role; equal values do not."""
        current = {
            "allowed_domains": ["example.test"],
            "ttl": 86400,
            "server_flag": True,
        }
        inputs: dict[str, Any] = {
            "mount": "pki",
            "name": "web",
            "allowed_domains": ["example.test"],
            "ttl": "12h",
        }
        client = FakeClient({("GET", "pki/roles/web"): current})
        result = run_module_under_test(pki_role, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(
            client.writes(),
            [
                (
                    "PATCH",
                    "pki/roles/web",
                    {"allowed_domains": ["example.test"], "ttl": "12h"},
                )
            ],
        )
        inputs["ttl"] = 86400
        client = FakeClient({("GET", "pki/roles/web"): current})
        self.assertFalse(run_module_under_test(pki_role, inputs, client)["changed"])

    def test_absent(self) -> None:
        """Absent deletes an existing role once."""
        client = FakeClient({("GET", "pki/roles/web"): {"ttl": 1}})
        inputs = {"mount": "pki", "name": "web", "state": "absent"}
        self.assertTrue(run_module_under_test(pki_role, inputs, client)["changed"])
        self.assertEqual(client.writes(), [("DELETE", "pki/roles/web", None)])


class PkiIssuerTests(unittest.TestCase):
    """Issuers are resolved by name and patched; the default is set once."""

    def test_unchanged_with_comma_usage(self) -> None:
        """A comma separated usage string equals the requested list."""
        responses = {
            ("LIST", "pki/issuers"): ISSUERS,
            ("GET", "pki/issuer/id-1"): ISSUER,
            ("GET", "pki/config/issuers"): {"default": "id-1"},
        }
        client = FakeClient(responses)
        inputs = {
            "mount": "pki",
            "name": "root",
            "default": True,
            "manual_chain": [],
            "usage": [
                "read-only",
                "issuing-certificates",
                "crl-signing",
                "ocsp-signing",
            ],
        }
        result = run_module_under_test(pki_issuer, inputs, client)
        self.assertFalse(result["changed"])
        self.assertEqual(result["issuer_id"], "id-1")
        self.assertEqual(client.writes(), [])

    def test_update_and_default(self) -> None:
        """AIA URLs are patched and the default issuer is configured."""
        responses = {
            ("LIST", "pki/issuers"): ISSUERS,
            ("GET", "pki/issuer/id-1"): ISSUER,
            ("GET", "pki/config/issuers"): {"default": "other"},
        }
        client = FakeClient(responses)
        inputs = {
            "mount": "pki",
            "name": "root",
            "default": True,
            "issuing_certificates": ["https://pki.example.test/root.der"],
        }
        result = run_module_under_test(pki_issuer, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(
            client.writes(),
            [
                (
                    "PATCH",
                    "pki/issuer/id-1",
                    {"issuing_certificates": ["https://pki.example.test/root.der"]},
                ),
                ("POST", "pki/config/issuers", {"default": "id-1"}),
            ],
        )
        self.assertFalse(result["diff"]["before"]["default"])
        self.assertTrue(result["diff"]["after"]["default"])

    def test_missing_issuer_and_absent(self) -> None:
        """An unknown name fails for present and is unchanged for absent."""
        client = FakeClient()
        result = run_module_under_test(
            pki_issuer, {"mount": "pki", "name": "nope"}, client
        )
        self.assertTrue(result["failed"])
        self.assertIn("not found", result["msg"])
        result = run_module_under_test(
            pki_issuer, {"mount": "pki", "name": "nope", "state": "absent"}, client
        )
        self.assertFalse(result["changed"])
        client = FakeClient({("LIST", "pki/issuers"): ISSUERS})
        result = run_module_under_test(
            pki_issuer, {"mount": "pki", "name": "root", "state": "absent"}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", "pki/issuer/id-1", None)])
