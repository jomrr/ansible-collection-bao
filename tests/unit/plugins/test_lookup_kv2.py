# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""kv2 lookup plugin contract with the API client simulated."""

from __future__ import annotations

import os
import unittest
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import Mock, patch

from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader
from ansible_collections.jomrr.bao.plugins.lookup import kv2
from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.tests.unit.plugins.support import FakeClient

SECRET = "recognizable-secret-value"
VARS = {
    "bao_url": "https://bao.example.test:8200",
    "bao_ca_file": "/etc/ca.pem",
    "bao_token": "recognizable-token",
}
ENV = {
    "BAO_ADDR": "https://env.example.test:8200",
    "BAO_TOKEN": "env-token",
    "BAO_CACERT": "/env/ca.pem",
}
RESPONSES = {
    ("READ", "kv/data/app/db"): {
        "data": {
            "data": {"username": "app", "password": SECRET},
            "metadata": {"version": 2},
        }
    },
    ("READ", "kv/data/app/gone"): {"errors": []},
    ("READ", "kv/data/app/deleted"): {
        "data": {"data": None, "metadata": {"version": 1}}
    },
}


class LookupTests(unittest.TestCase):
    """Terms, options and errors follow the documented contract."""

    def setUp(self) -> None:
        self.client = FakeClient(RESPONSES)
        self.created: list[dict[str, Any]] = []

        def build(
            url: str, token: str, ca_file: str | None, timeout: int
        ) -> FakeClient:
            self.created.append(
                {"url": url, "token": token, "ca_file": ca_file, "timeout": timeout}
            )
            return self.client

        patcher = patch.object(kv2, "BaoClient", side_effect=build)
        patcher.start()
        self.addCleanup(patcher.stop)

    def lookup(
        self, terms: list[str], variables: dict[str, Any] | None = None, **kwargs: Any
    ) -> list[Any]:
        """Run the plugin through Ansible's loader with VARS unless given."""
        plugin = cast(Callable[[str], Any], lookup_loader.get)("jomrr.bao.kv2")
        self.assertIsNotNone(plugin)
        chosen = VARS if variables is None else variables
        return list(plugin.run(terms, variables=chosen, **kwargs))

    def test_mapping_key_and_version(self) -> None:
        """Results are mappings, single keys or a selected version."""
        self.assertEqual(
            self.lookup(["app/db"], mount="kv"),
            [{"username": "app", "password": SECRET}],
        )
        self.assertEqual(self.lookup(["app/db"], mount="kv", key="username"), ["app"])
        self.lookup(["/app/db/"], mount="kv", version=2)
        self.assertEqual(
            self.client.calls[-1], ("READ", "kv/data/app/db", {"version": "2"})
        )
        self.assertEqual(self.created[0]["url"], VARS["bao_url"])
        self.assertEqual(self.created[0]["token"], VARS["bao_token"])
        self.assertEqual(self.created[0]["ca_file"], VARS["bao_ca_file"])
        self.assertEqual(self.created[0]["timeout"], 30)

    def test_missing_path_key_and_version(self) -> None:
        """Failures name mount and path but never content or the token."""
        cases: list[tuple[list[str], dict[str, Any], str]] = [
            (["app/gone"], {"mount": "kv"}, "kv/app/gone not found"),
            (
                ["app/deleted"],
                {"mount": "kv"},
                "kv/app/deleted has no readable version",
            ),
            (
                ["app/db"],
                {"mount": "kv", "key": "missing"},
                "key 'missing' not found in KV secret kv/app/db",
            ),
        ]
        for terms, options, expected in cases:
            with (
                self.subTest(expected=expected),
                self.assertRaises(AnsibleError) as raised,
            ):
                self.lookup(terms, **options)
            self.assertIn(expected, str(raised.exception))
            self.assertNotIn(SECRET, str(raised.exception))
            self.assertNotIn("recognizable-token", str(raised.exception))

    def test_transport_error(self) -> None:
        """Client errors are wrapped with mount and path."""
        self.client.responses[("READ", "kv/data/app/db")] = BaoError(
            "GET failed with HTTP 403: permission denied", 403
        )
        with self.assertRaisesRegex(
            AnsibleError, "reading KV secret kv/app/db failed: .*403"
        ):
            self.lookup(["app/db"], mount="kv")

    def test_environment_fallback_and_precedence(self) -> None:
        """Variables win over the environment; direct options win over variables."""
        with patch.dict(os.environ, ENV):
            self.lookup(["app/db"], variables={}, mount="kv")
            self.assertEqual(self.created[-1]["url"], ENV["BAO_ADDR"])
            self.assertEqual(self.created[-1]["token"], ENV["BAO_TOKEN"])
            self.assertEqual(self.created[-1]["ca_file"], ENV["BAO_CACERT"])
            self.lookup(["app/db"], mount="kv")
            self.assertEqual(self.created[-1]["url"], VARS["bao_url"])
            self.lookup(
                ["app/db"], mount="kv", url="https://direct.example.test", timeout=5
            )
            self.assertEqual(self.created[-1]["url"], "https://direct.example.test")
            self.assertEqual(self.created[-1]["timeout"], 5)

    def test_missing_connection_options(self) -> None:
        """Absent url, token or mount fail with a hint before any request."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(AnsibleError, "bao_url or BAO_ADDR"):
                self.lookup(["app/db"], variables={}, mount="kv")
            with self.assertRaisesRegex(AnsibleError, "bao_token or BAO_TOKEN"):
                self.lookup(
                    ["app/db"], variables={"bao_url": VARS["bao_url"]}, mount="kv"
                )
        with self.assertRaisesRegex(AnsibleError, "mount"):
            self.lookup(["app/db"])
        self.assertEqual(self.client.calls, [])

    def test_templated_variables(self) -> None:
        """Variable values that are still templates are rendered before use."""
        templates = {"{{ url }}": VARS["bao_url"], "{{ ca }}": "~/ca.pem"}
        templar = Mock(template=lambda value: templates.get(value, value))
        plugin = cast(Callable[..., Any], lookup_loader.get)(
            "jomrr.bao.kv2", templar=templar
        )
        variables = {**VARS, "bao_url": "{{ url }}", "bao_ca_file": "{{ ca }}"}
        plugin.run(["app/db"], variables=variables, mount="kv")
        self.assertEqual(self.created[-1]["url"], VARS["bao_url"])
        self.assertEqual(self.created[-1]["ca_file"], os.path.expanduser("~/ca.pem"))

    def test_invalid_url(self) -> None:
        """A plain http URL is rejected by the client validation."""
        patch.stopall()
        with self.assertRaisesRegex(AnsibleError, "https"):
            self.lookup(
                ["app/db"],
                variables={**VARS, "bao_url": "http://bao.example.test"},
                mount="kv",
            )
