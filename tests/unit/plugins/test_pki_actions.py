# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""PKI action modules: authority generation, CRL rotation and ACME EAB keys."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.modules import (
    pki_acme_eab,
    pki_ca,
    pki_crl_rotate,
)
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

ROOT = {
    "mount": "pki-root",
    "issuer_name": "root",
    "type": "root",
    "common_name": "Root",
}
INTERMEDIATE = {
    "mount": "pki-int",
    "issuer_name": "int",
    "type": "intermediate",
    "common_name": "Issuing",
    "key_name": "int-key",
}
EXISTING = {
    ("LIST", "pki-root/issuers"): {
        "keys": ["r1"],
        "key_info": {"r1": {"issuer_name": "root"}},
    },
    ("GET", "pki-root/issuer/r1"): {"certificate": "ROOT PEM"},
}
CSR = {"data": {"csr": "CSR PEM", "key_id": "k1"}}
SIGNED = {"data": {"certificate": "INT PEM", "ca_chain": ["INT PEM", "ROOT PEM"]}}
IMPORTED = {
    "data": {"imported_issuers": ["i1", "i2"], "mapping": {"i1": "k1", "i2": ""}}
}


class PkiCaTests(unittest.TestCase):
    """Authorities are created once per issuer name."""

    def test_existing_issuer_is_unchanged(self) -> None:
        """An issuer with the requested name is reported without writes."""
        client = FakeClient(EXISTING)
        result = run_module_under_test(pki_ca, ROOT, client)
        self.assertFalse(result["changed"])
        self.assertEqual(result["issuer_id"], "r1")
        self.assertEqual(result["certificate"], "ROOT PEM")
        self.assertEqual(client.writes(), [])

    def test_generate_root_and_check_mode(self) -> None:
        """A missing root is generated with its name; check mode only reports."""
        client = FakeClient()
        result = run_module_under_test(
            pki_ca, {**ROOT, "ttl": "87600h"}, client, check_mode=True
        )
        self.assertTrue(result["changed"])
        self.assertIsNone(result["issuer_id"])
        self.assertEqual(client.writes(), [])
        generated = {
            "data": {"issuer_id": "r1", "certificate": "ROOT PEM", "private_key": "KEY"}
        }
        client = FakeClient(
            {("POST", "pki-root/issuers/generate/root/internal"): generated}
        )
        result = run_module_under_test(pki_ca, {**ROOT, "ttl": "87600h"}, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["issuer_id"], "r1")
        self.assertNotIn("private_key", result)
        body = client.writes()[0][2]
        self.assertEqual(
            body, {"common_name": "Root", "ttl": "87600h", "issuer_name": "root"}
        )

    def test_intermediate_csr_only(self) -> None:
        """Without a certificate or signing mount the CSR is returned."""
        client = FakeClient(
            {("POST", "pki-int/issuers/generate/intermediate/internal"): CSR}
        )
        result = run_module_under_test(pki_ca, INTERMEDIATE, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["csr"], "CSR PEM")
        self.assertIsNone(result["issuer_id"])
        self.assertEqual(len(client.writes()), 1)

    def test_intermediate_reuses_key_and_signs_in_server(self) -> None:
        """An existing key is reused, the CSR signed by the root, the issuer named."""
        responses = {
            ("LIST", "pki-int/keys"): {
                "keys": ["k1"],
                "key_info": {"k1": {"key_name": "int-key"}},
            },
            ("POST", "pki-int/issuers/generate/intermediate/existing"): CSR,
            ("POST", "pki-root/issuer/root/sign-intermediate"): SIGNED,
            ("POST", "pki-int/intermediate/set-signed"): IMPORTED,
        }
        client = FakeClient(responses)
        inputs = {
            **INTERMEDIATE,
            "signing_mount": "pki-root",
            "signing_issuer": "root",
            "signing_ttl": "43800h",
        }
        result = run_module_under_test(pki_ca, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["issuer_id"], "i1")
        self.assertEqual(result["csr"], "CSR PEM")
        writes = client.writes()
        self.assertEqual(writes[0][1], "pki-int/issuers/generate/intermediate/existing")
        assert writes[0][2] is not None
        self.assertEqual(writes[0][2]["key_ref"], "k1")
        assert writes[1][2] is not None
        self.assertEqual(writes[1][2]["csr"], "CSR PEM")
        self.assertEqual(writes[1][2]["ttl"], "43800h")
        self.assertEqual(
            writes[2],
            (
                "POST",
                "pki-int/intermediate/set-signed",
                {"certificate": "INT PEM\nINT PEM\nROOT PEM"},
            ),
        )
        self.assertEqual(
            writes[3], ("PATCH", "pki-int/issuer/i1", {"issuer_name": "int"})
        )

    def test_intermediate_with_external_certificate(self) -> None:
        """A supplied certificate is imported without a signing call."""
        responses = {
            ("POST", "pki-int/issuers/generate/intermediate/internal"): CSR,
            ("POST", "pki-int/intermediate/set-signed"): IMPORTED,
        }
        client = FakeClient(responses)
        result = run_module_under_test(
            pki_ca, {**INTERMEDIATE, "certificate": "INT PEM\n"}, client
        )
        self.assertEqual(result["issuer_id"], "i1")
        self.assertEqual(result["certificate"], "INT PEM\n")
        self.assertEqual(
            [call[1] for call in client.writes()],
            [
                "pki-int/issuers/generate/intermediate/internal",
                "pki-int/intermediate/set-signed",
                "pki-int/issuer/i1",
            ],
        )


class PkiActionTests(unittest.TestCase):
    """CRL rotation and EAB keys are always changed and skipped in check mode."""

    def test_crl_rotate(self) -> None:
        """Rotation calls the full or delta endpoint."""
        client = FakeClient({("GET", "pki/crl/rotate-delta"): {"success": True}})
        result = run_module_under_test(
            pki_crl_rotate, {"mount": "pki", "delta": True}, client
        )
        self.assertTrue(result["changed"])
        self.assertTrue(result["success"])
        self.assertEqual(client.calls[0][1], "pki/crl/rotate-delta")
        client = FakeClient()
        result = run_module_under_test(
            pki_crl_rotate, {"mount": "pki"}, client, check_mode=True
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.calls, [])

    def test_eab(self) -> None:
        """EAB keys are created below the role or issuer directory."""
        created = {
            "data": {
                "id": "eab-1",
                "key": "recognizable-eab-key",
                "key_type": "hs",
                "acme_directory": "pki/roles/web/acme/directory",
            }
        }
        client = FakeClient({("POST", "pki/roles/web/acme/new-eab"): created})
        result = run_module_under_test(
            pki_acme_eab, {"mount": "pki", "role": "web"}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["id"], "eab-1")
        self.assertEqual(result["key"], "recognizable-eab-key")
        self.assertNotIn("recognizable-eab-key", result["msg"])
        client = FakeClient()
        result = run_module_under_test(
            pki_acme_eab, {"mount": "pki", "issuer": "int"}, client, check_mode=True
        )
        self.assertIsNone(result["key"])
        self.assertIn("pki/issuer/int/acme/new-eab", result["msg"])
        self.assertEqual(client.calls, [])
