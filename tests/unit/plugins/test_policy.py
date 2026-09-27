# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""ACL policy state module."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.modules import policy
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

PATH = "sys/policies/acl/reader"
RULES = 'path "kv/data/app/*" { capabilities = ["read"] }\n'


class PolicyTests(unittest.TestCase):
    """Create, update, keep and remove policies with correct change reporting."""

    def test_create(self) -> None:
        """A missing policy is written."""
        client = FakeClient()
        result = run_module_under_test(
            policy, {"name": "reader", "rules": RULES}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("POST", PATH, {"policy": RULES})])
        self.assertEqual(
            result["diff"], {"before": {}, "after": {"policy": RULES.strip()}}
        )

    def test_unchanged_ignores_surrounding_whitespace(self) -> None:
        """Equal rules with different surrounding whitespace produce no change."""
        client = FakeClient({("GET", PATH): {"name": "reader", "policy": RULES}})
        result = run_module_under_test(
            policy, {"name": "reader", "rules": RULES.strip()}, client
        )
        self.assertFalse(result["changed"])
        self.assertEqual(client.writes(), [])

    def test_update_and_check_mode(self) -> None:
        """Different rules are written, but not in check mode."""
        responses = {("GET", PATH): {"name": "reader", "policy": 'path "old" {}'}}
        client = FakeClient(responses)
        result = run_module_under_test(
            policy, {"name": "reader", "rules": RULES}, client, check_mode=True
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [])
        self.assertEqual(result["diff"]["before"]["policy"], 'path "old" {}')
        client = FakeClient(responses)
        run_module_under_test(policy, {"name": "reader", "rules": RULES}, client)
        self.assertEqual(client.writes(), [("POST", PATH, {"policy": RULES})])

    def test_absent(self) -> None:
        """Absent deletes an existing policy once and is otherwise unchanged."""
        client = FakeClient({("GET", PATH): {"name": "reader", "policy": RULES}})
        result = run_module_under_test(
            policy, {"name": "reader", "state": "absent"}, client
        )
        self.assertTrue(result["changed"])
        self.assertEqual(client.writes(), [("DELETE", PATH, None)])
        client = FakeClient()
        result = run_module_under_test(
            policy, {"name": "reader", "state": "absent"}, client
        )
        self.assertFalse(result["changed"])
        self.assertEqual(client.writes(), [])

    def test_present_without_rules(self) -> None:
        """Present without rules fails before writing."""
        client = FakeClient()
        result = run_module_under_test(policy, {"name": "reader"}, client)
        self.assertTrue(result["failed"])
        self.assertEqual(client.writes(), [])
