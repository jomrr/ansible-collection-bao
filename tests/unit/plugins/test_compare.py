# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Field normalization and change planning shared by the state modules."""

from __future__ import annotations

import unittest
from typing import Any

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
    "networks": "cidrs",
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
            "networks": ["10.0.0.1", "10.1.0.0/24", "2001:db8::1"],
            "ttl": 3600,
            "extensions": {"permit-pty": ""},
        }
        desired = {
            "description": "x",
            "count": 3,
            "enabled": True,
            "policies": ["a", "b"],
            "domains": ["two.test", "one.test"],
            "networks": ["2001:DB8::1/128", "10.0.0.1/32", "10.1.0.0/24"],
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

    def test_unset_collections_equal_empty_ones(self) -> None:
        """A null collection from the server equals an empty requested one."""
        current = {name: None for name in FIELDS}
        empty: dict[str, Any] = {
            "policies": [],
            "domains": [],
            "networks": [],
            "extensions": {},
        }
        self.assertEqual(plan(FIELDS, current, empty), {})
        self.assertEqual(view(FIELDS, current), empty)
        self.assertEqual(
            plan(FIELDS, current, {"description": ""}), {"description": ""}
        )

    def test_networks_keep_real_differences(self) -> None:
        """Only host suffixes are ignored; other prefixes and names still differ."""
        current = {"networks": ["10.0.0.0/24", "bao.example.test"]}
        self.assertEqual(
            plan(FIELDS, current, {"networks": ["10.0.0.0/24", "bao.example.test"]}), {}
        )
        for networks in (
            ["10.0.0.5/24", "bao.example.test"],
            ["10.0.0.0/32", "bao.example.test"],
        ):
            with self.subTest(networks=networks):
                self.assertEqual(
                    plan(FIELDS, current, {"networks": networks}),
                    {"networks": networks},
                )

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
