# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Recovery key generation and explicit rotation."""

from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import recovery_key
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

INIT = "sys/rotate/recovery/init"
UPDATE = "sys/rotate/recovery/update"
OLD = ["recognizable-old-share-1", "recognizable-old-share-2"]
NEW = {
    "keys": ["new-1", "new-2", "new-3"],
    "keys_base64": ["bmV3LTE=", "bmV3LTI=", "bmV3LTM="],
}
NONE = {"started": False, "required": 0, "n": 0, "t": 0}
EXISTING = {"started": False, "required": 2, "n": 0, "t": 0}
RUNNING = {"started": True, "required": 2, "nonce": "other", "progress": 1}
ROTATE = {"state": "rotated", "shares": 3, "threshold": 2, "keys": OLD}


def server(status: dict[str, Any]) -> FakeClient:
    """Build a client with a rotation status and a seal layout."""
    layout = {"n": 3, "t": 2, "type": "static"}
    return FakeClient({("GET", INIT): status, ("READ", "sys/seal-status"): layout})


def updates(required: int) -> tuple[Callable[[Any], dict[str, Any]], list[Any]]:
    """Answer share submissions: progress first, completion at the threshold."""
    seen: list[Any] = []

    def answer(body: Any) -> dict[str, Any]:
        seen.append(body)
        if len(seen) < required:
            return {"data": {"started": True, "progress": len(seen)}}
        return {"data": {"complete": True, **NEW}}

    return answer, seen


class RecoveryKeyTests(unittest.TestCase):
    """Shares are generated once and rotated only on request."""

    def test_generate_when_none_exist(self) -> None:
        """Without existing shares the first request returns the new ones."""
        client = server(NONE)
        client.responses[("POST", INIT)] = {"data": {"complete": True, **NEW}}
        result = run_module_under_test(
            recovery_key, {"shares": 3, "threshold": 2}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["recovery_keys"], NEW["keys"])
        self.assertEqual(result["recovery_keys_base64"], NEW["keys_base64"])
        self.assertEqual((result["shares"], result["threshold"]), (3, 2))
        body = {"secret_shares": 3, "secret_threshold": 2}
        self.assertEqual(client.writes(), [("POST", INIT, body)])
        self.assertNotIn("new-1", result["msg"])

    def test_present_keeps_existing_keys(self) -> None:
        """Existing shares are never replaced by the default state."""
        client = server(EXISTING)
        result = run_module_under_test(
            recovery_key, {"shares": 5, "threshold": 3}, client
        )
        self.assertFalse(result["changed"])
        self.assertEqual(result["recovery_keys"], [])
        self.assertEqual((result["shares"], result["threshold"]), (3, 2))
        self.assertEqual(client.writes(), [])

    def test_rotate_submits_the_existing_shares(self) -> None:
        """A rotation starts, submits the threshold of shares and returns new ones."""
        answer, seen = updates(2)
        client = server(EXISTING)
        client.responses[("POST", INIT)] = {"data": {"started": True, "nonce": "n-1"}}
        client.responses[("POST", UPDATE)] = answer
        inputs = {**ROTATE, "keys": [*OLD, "unused-share"]}
        result = run_module_under_test(recovery_key, inputs, client)
        self.assertTrue(result["changed"])
        self.assertEqual(result["recovery_keys"], NEW["keys"])
        expected = [{"key": share, "nonce": "n-1"} for share in OLD]
        self.assertEqual(seen, expected)
        self.assertNotIn(OLD[0], str(result))

    def test_failed_rotation_is_cancelled(self) -> None:
        """A rejected share cancels the attempt; the message contains no share."""
        error = BaoError(f"POST {UPDATE} failed with HTTP 400: bad {OLD[0]}", 400)
        client = server(EXISTING)
        client.responses[("POST", INIT)] = {"data": {"started": True, "nonce": "n-1"}}
        client.responses[("POST", UPDATE)] = error
        result = run_module_under_test(recovery_key, ROTATE, client)
        self.assertTrue(result["failed"])
        self.assertIn("the attempt was cancelled", result["msg"])
        self.assertNotIn(OLD[0], result["msg"])
        self.assertEqual(client.writes()[-1], ("DELETE", INIT, None))

    def test_running_rotation_needs_force(self) -> None:
        """Another attempt blocks the rotation unless force cancels it first."""
        client = server(RUNNING)
        result = run_module_under_test(recovery_key, ROTATE, client)
        self.assertTrue(result["failed"])
        self.assertIn("already in progress", result["msg"])
        self.assertEqual(client.writes(), [])
        client = server(RUNNING)
        client.responses[("POST", INIT)] = {"data": {"started": True, "nonce": "n-2"}}
        client.responses[("POST", UPDATE)] = updates(2)[0]
        result = run_module_under_test(recovery_key, {**ROTATE, "force": True}, client)
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes()[0], ("DELETE", INIT, None))

    def test_invalid_requests_fail_before_writing(self) -> None:
        """Too few shares and impossible layouts never start a rotation."""
        cases: list[dict[str, Any]] = [
            {**ROTATE, "keys": OLD[:1]},
            {**ROTATE, "threshold": 4},
            {**ROTATE, "pgp_keys": ["only-one"]},
        ]
        for inputs in cases:
            with self.subTest(inputs=sorted(inputs)):
                client = server(EXISTING)
                result = run_module_under_test(recovery_key, inputs, client)
                self.assertTrue(result["failed"])
                self.assertEqual(client.writes(), [])

    def test_check_mode_reports_without_writing(self) -> None:
        """Check mode predicts generation and rotation from the status."""
        for status, inputs, word in (
            (NONE, {}, "generate"),
            (EXISTING, ROTATE, "rotate"),
        ):
            with self.subTest(word=word):
                client = server(status)
                result = run_module_under_test(
                    recovery_key, inputs, client, check_mode=True
                )
                self.assertTrue(result["changed"])
                self.assertIn(f"Would {word}", result["msg"])
                self.assertEqual(result["recovery_keys"], [])
                self.assertEqual(client.writes(), [])

    def test_pgp_request(self) -> None:
        """PGP keys and the backup flag are passed to the server."""
        client = server(NONE)
        client.responses[("POST", INIT)] = {
            "data": {"complete": True, **NEW, "pgp_fingerprints": ["f1", "f2"]}
        }
        inputs = {"shares": 2, "threshold": 2, "pgp_keys": ["a", "b"], "backup": True}
        result = run_module_under_test(recovery_key, inputs, client)
        body = client.writes()[0][2]
        assert body is not None
        self.assertEqual(body["pgp_keys"], ["a", "b"])
        self.assertTrue(body["backup"])
        self.assertEqual(result["pgp_fingerprints"], ["f1", "f2"])
