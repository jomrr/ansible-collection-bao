# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""KV version 2 secret state module."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.module_utils import _kv2
from ansible_collections.jomrr.bao.plugins.modules import kv2_secret
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

DATA = "kv/data/app/db"
META = "kv/metadata/app/db"
SECRET = "recognizable-secret-value"
CURRENT = {
    ("GET", META): {"current_version": 3},
    ("READ", DATA): {
        "data": {
            "data": {"username": "app", "password": SECRET, "extra": "keep"},
            "metadata": {"version": 3},
        }
    },
}
INPUTS = {"mount": "kv", "path": "app/db", "data": {"username": "app"}}


class Kv2SecretTests(unittest.TestCase):
    """Data is reconciled with check and set; values stay out of the output."""

    def test_create_with_generated_key(self) -> None:
        """A missing secret is written with data and generated keys."""
        client = FakeClient({("POST", DATA): {"data": {"version": 1}}})
        inputs = {
            **INPUTS,
            "generate": {"password": {"length": 12, "chars": ["digits"]}},
        }
        result = run_module_under_test(kv2_secret, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["version"], 1)
        method, path, body = client.writes()[0]
        assert body is not None
        self.assertEqual((method, path), ("POST", DATA))
        self.assertEqual(body["options"], {"cas": 0})
        self.assertEqual(body["data"]["username"], "app")
        self.assertTrue(body["data"]["password"].isdigit())
        self.assertEqual(len(body["data"]["password"]), 12)
        self.assertEqual(
            result["diff"],
            {"before": {}, "after": {"keys": ["password", "username"], "version": 1}},
        )

    def test_unchanged_keeps_extra_keys_and_generated_values(self) -> None:
        """Matching data with extra keys and an existing generated key is unchanged."""
        client = FakeClient(CURRENT)
        inputs = {**INPUTS, "generate": {"password": {}}}
        result = run_module_under_test(kv2_secret, inputs, client)
        self.assertFalse(result["changed"])
        self.assertEqual(result["version"], 3)
        self.assertEqual(client.writes(), [])
        self.assertNotIn(SECRET, str(result))

    def test_update_uses_cas_and_preserves_extra_keys(self) -> None:
        """Changed data is merged over the current data and written with cas."""
        client = FakeClient({**CURRENT, ("POST", DATA): {"data": {"version": 4}}})
        inputs = {**INPUTS, "data": {"username": "changed"}}
        result = run_module_under_test(kv2_secret, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["version"], 4)
        body = client.writes()[0][2]
        assert body is not None
        self.assertEqual(body["options"], {"cas": 3})
        self.assertEqual(
            body["data"], {"username": "changed", "password": SECRET, "extra": "keep"}
        )
        self.assertEqual(
            result["diff"]["before"],
            {"keys": ["extra", "password", "username"], "version": 3},
        )
        self.assertNotIn(SECRET, str(result))

    def test_check_mode_predicts_without_writing(self) -> None:
        """Check mode reports the change and the next version without a write."""
        client = FakeClient(CURRENT)
        inputs = {**INPUTS, "generate": {"token": {}}}
        result = run_module_under_test(kv2_secret, inputs, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertEqual(result["version"], 4)
        self.assertEqual(client.writes(), [])
        self.assertIn("token", result["diff"]["after"]["keys"])

    def test_deleted_version_is_not_recreated(self) -> None:
        """Metadata without readable data fails before writing."""
        responses = {
            ("GET", META): {"current_version": 1},
            ("READ", DATA): {
                "data": {"data": None, "metadata": {"version": 1, "deletion_time": "x"}}
            },
        }
        client = FakeClient(responses)
        result = run_module_under_test(kv2_secret, INPUTS, client)
        self.assertTrue(result["failed"])
        self.assertIn("no readable current version", result["msg"])
        self.assertEqual(client.writes(), [])
        client = FakeClient(responses)
        inputs = {"mount": "kv", "path": "app/db", "state": "absent"}
        result = run_module_under_test(kv2_secret, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", META, None)])

    def test_overlapping_keys(self) -> None:
        """Keys in both data and generate are rejected."""
        client = FakeClient()
        inputs = {**INPUTS, "generate": {"username": {}}}
        result = run_module_under_test(kv2_secret, inputs, client)
        self.assertTrue(result["failed"])
        self.assertEqual(client.calls, [])

    def test_absent(self) -> None:
        """Absent deletes the metadata once."""
        client = FakeClient(CURRENT)
        inputs = {"mount": "kv", "path": "app/db", "state": "absent"}
        result = run_module_under_test(kv2_secret, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", META, None)])
        client = FakeClient()
        self.assertFalse(run_module_under_test(kv2_secret, inputs, client)["changed"])

    def test_generate_value(self) -> None:
        """Generated values honor length and character classes."""
        value = _kv2.generate_value({"length": 8, "chars": ["hexdigits"]})
        self.assertEqual(len(value), 8)
        self.assertTrue(all(char in "0123456789abcdefABCDEF" for char in value))
        self.assertEqual(len(_kv2.generate_value(None)), 32)
        with self.assertRaises(ValueError):
            _kv2.generate_value({"length": 0})
