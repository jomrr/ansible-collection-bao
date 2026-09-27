# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Field normalization and change planning shared by the state modules."""

from __future__ import annotations

import unittest

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    as_list,
    desired_from,
    merge,
    plan,
    to_api,
    view,
)

FIELDS: Fields = {
    "description": "str",
    "count": "int",
    "enabled": "bool",
    "policies": "list",
    "domains": "csv",
    "ttl": "duration",
    "extensions": "map",
}


class CompareTests(unittest.TestCase):
    """Normalized comparison ignores representation differences."""

    def test_as_list(self) -> None:
        """Comma strings, lists and None become lists of strings."""
        self.assertEqual(as_list(None), [])
        self.assertEqual(as_list("a, b,,c"), ["a", "b", "c"])
        self.assertEqual(as_list(["b", 1]), ["b", "1"])

    def test_plan_ignores_representation(self) -> None:
        """Equivalent values in different representations produce no change."""
        current = {
            "description": "x",
            "count": "3",
            "enabled": True,
            "policies": ["b", "a"],
            "domains": "one.test,two.test",
            "ttl": 3600,
            "extensions": {"permit-pty": ""},
        }
        desired = {
            "description": "x",
            "count": 3,
            "enabled": True,
            "policies": ["a", "b"],
            "domains": ["two.test", "one.test"],
            "ttl": "1h",
            "extensions": {"permit-pty": ""},
            "ignored": None,
        }
        self.assertEqual(plan(FIELDS, current, desired), {})

    def test_plan_reports_differences(self) -> None:
        """Changed, added and unknown current values appear in the plan."""
        current = {"description": "x", "ttl": 60}
        desired = {"description": "y", "ttl": "1m", "count": 1}
        self.assertEqual(
            plan(FIELDS, current, desired), {"description": "y", "count": 1}
        )
        self.assertEqual(plan(FIELDS, None, desired), desired)

    def test_view_merge_desired_and_api(self) -> None:
        """Views normalize known fields; merge and to_api build request bodies."""
        params = {"description": "x", "domains": ["b", "a"], "count": None, "other": 1}
        desired = desired_from(params, FIELDS)
        self.assertEqual(desired, {"description": "x", "domains": ["b", "a"]})
        self.assertEqual(
            view(FIELDS, {"domains": "b,a", "ttl": "2m", "extra": 1}),
            {"domains": ["a", "b"], "ttl": 120},
        )
        self.assertEqual(view(FIELDS, None), {})
        self.assertEqual(
            merge({"description": "old", "count": 2}, desired),
            {"description": "x", "count": 2, "domains": ["b", "a"]},
        )
        self.assertEqual(
            to_api(FIELDS, {"domains": ["b", "a"], "ttl": "1h", "count": None}),
            {"domains": "b,a", "ttl": "1h"},
        )
