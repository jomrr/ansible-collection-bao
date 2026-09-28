# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Audit device state module."""

from __future__ import annotations

import unittest
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import audit_device
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

FILE = {
    "type": "file",
    "description": "Audit log",
    "local": True,
    "options": {"file_path": "/var/log/audit.json", "elide_list_responses": "1"},
    "path": "file/",
}
HEADERS = '{"Authorization": ["Bearer recognizable-credential"]}'
WEB = {
    "type": "http",
    "description": "",
    "local": False,
    "options": {"uri": "https://logs.example.test", "headers": HEADERS},
    "path": "web/",
}
MATCHING = {
    "path": "file",
    "type": "file",
    "description": "Audit log",
    "options": {"file_path": "/var/log/audit.json", "elide_list_responses": True},
}
TARGET = "sys/audit/file"


def listing() -> FakeClient:
    """Return a client for a server with a file and an http device."""
    return FakeClient({("GET", "sys/audit"): {"file/": FILE, "web/": WEB}})


def run(client: FakeClient, check_mode: bool = False, **inputs: Any) -> dict[str, Any]:
    """Run the module with the matching file device settings and the inputs."""
    params = {**MATCHING, **inputs}
    return run_module_under_test(audit_device, params, client, check_mode=check_mode)


class AuditDeviceTests(unittest.TestCase):
    """Enable, keep, replace and disable audit devices."""

    def test_enable(self) -> None:
        """A missing device is enabled with string options, not in check mode."""
        client = FakeClient()
        self.assertTrue(run(client, check_mode=True)["changed"])
        self.assertEqual(client.writes(), [])
        result = run(client, path="/file/")
        self.assertTrue(result["changed"])
        options = {"file_path": "/var/log/audit.json", "elide_list_responses": "true"}
        body = {"type": "file", "description": "Audit log", "options": options}
        self.assertEqual(client.writes(), [("POST", TARGET, body)])
        self.assertEqual(result["diff"], {"before": {}, "after": body})
        self.assertEqual(
            run(listing(), check_mode=True)["diff"]["before"]["local"], True
        )

    def test_unchanged(self) -> None:
        """Equal settings and unset fields produce no write."""
        for inputs in (MATCHING, {"path": "file", "type": "file"}):
            with self.subTest(inputs=inputs):
                client = listing()
                result = run_module_under_test(audit_device, inputs, client)
                self.assertFalse(result["changed"])
                self.assertEqual(client.writes(), [])

    def test_difference_fails_without_replace(self) -> None:
        """A differing device is reported by field and never modified."""
        for field, value in (
            ("type", "syslog"),
            ("description", "Changed"),
            ("options", {"file_path": "/var/log/audit.json"}),
        ):
            with self.subTest(field=field):
                client = listing()
                inputs = {**MATCHING, field: value}
                result = run_module_under_test(audit_device, inputs, client)
                self.assertTrue(result["failed"])
                self.assertIn(f"differs in {field};", result["msg"])
                self.assertEqual(client.writes(), [])

    def test_replace(self) -> None:
        """Replace disables and enables the device and keeps its local flag."""
        options = {"file_path": "discard"}
        client = listing()
        result = run(client, check_mode=True, options=options, replace=True)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])
        self.assertFalse(run(client, replace=True)["changed"])
        result = run(client, options=options, replace=True)
        body = {
            "type": "file",
            "description": "Audit log",
            "options": options,
            "local": True,
        }
        self.assertEqual(
            client.writes(), [("DELETE", TARGET, None), ("POST", TARGET, body)]
        )
        self.assertEqual(result["diff"]["after"]["options"], options)

    def test_rejected_replacement_restores_the_device(self) -> None:
        """A rejected new device enables the previous one again and fails."""
        rejected = BaoError(f"POST {TARGET} failed with HTTP 400: rejected", 400)
        attempts = [rejected, None]
        client = listing()
        client.responses[("POST", TARGET)] = lambda _body: _raise(attempts.pop(0))
        result = run(client, options={"file_path": "/missing/audit"}, replace=True)
        self.assertTrue(result["failed"])
        self.assertIn("rejected", result["msg"])
        restored = {
            "type": "file",
            "description": "Audit log",
            "options": {
                "file_path": "/var/log/audit.json",
                "elide_list_responses": "true",
            },
            "local": True,
        }
        self.assertEqual(client.writes()[-1], ("POST", TARGET, restored))

    def test_secret_options_are_hidden(self) -> None:
        """Credentials are compared and sent but never shown."""
        inputs = {
            "path": "web",
            "type": "http",
            "options": {"uri": "https://logs.example.test"},
            "secret_options": {"headers": HEADERS},
        }
        client = listing()
        result = run_module_under_test(audit_device, inputs, client)
        self.assertFalse(result["changed"])
        absent = {"path": "web", "state": "absent"}
        removed = run_module_under_test(audit_device, absent, listing())
        inputs["secret_options"] = {"headers": "{}", "uri": "https://user:key@logs"}
        failed = run_module_under_test(audit_device, inputs, listing())
        self.assertIn("differs in options;", failed["msg"])
        replaced = run_module_under_test(
            audit_device, {**inputs, "replace": True}, listing()
        )
        for outcome in (result, removed, failed, replaced):
            self.assertNotIn("recognizable-credential", repr(outcome))
            self.assertNotIn("user:key", repr(outcome))

    def test_absent(self) -> None:
        """Absent disables an existing device once, not in check mode."""
        absent = {"path": "file", "state": "absent"}
        client = listing()
        result = run_module_under_test(audit_device, absent, client, check_mode=True)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])
        result = run_module_under_test(audit_device, absent, client)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", TARGET, None)])
        self.assertEqual(result["diff"]["after"], {})
        result = run_module_under_test(audit_device, absent, FakeClient())
        self.assertFalse(result["changed"])

    def test_empty_path(self) -> None:
        """A path of slashes names no device."""
        client = listing()
        self.assertTrue(run(client, path="/")["failed"])
        self.assertEqual(client.calls, [])


def _raise(outcome: BaoError | None) -> None:
    """Raise the outcome of a write attempt when it is an error."""
    if outcome is not None:
        raise outcome
