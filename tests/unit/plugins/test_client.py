# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Transport contract of BaoClient with the HTTP boundary simulated."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from email.message import Message
from typing import Any
from unittest.mock import Mock, patch

from ansible.module_utils.urls import SSLValidationError
from ansible_collections.jomrr.bao.plugins.module_utils import client as client_module
from ansible_collections.jomrr.bao.plugins.module_utils.client import (
    BaoClient,
    BaoError,
    validate_url,
)


def response(body: bytes) -> Mock:
    """Build a context manager response returning the body."""
    result = Mock()
    result.read.return_value = body
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


def http_error(code: int, body: bytes) -> urllib.error.HTTPError:
    """Build an HTTPError with a readable body."""
    return urllib.error.HTTPError(
        "https://bao.example.test:8200/v1/x", code, "error", Message(), io.BytesIO(body)
    )


class ClientTests(unittest.TestCase):
    """Check request construction, response decoding and error mapping."""

    def setUp(self) -> None:
        self.client = BaoClient(
            "https://bao.example.test:8200/", "recognizable-token", "/etc/ca.pem", 7
        )

    def test_request_arguments(self) -> None:
        """Requests carry the token header, TLS settings and JSON body."""
        with patch.object(
            client_module, "open_url", return_value=response(b'{"data": {"a": 1}}')
        ) as open_url:
            self.assertEqual(self.client.get("sys/policies/acl/my policy"), {"a": 1})
            self.client.write("sys/mounts/kv", {"type": "kv"})
            self.client.patch("pki/roles/r", {"ttl": "1h"})
            self.client.delete("sys/mounts/kv")
            self.client.list_keys("pki/issuers")
        calls = open_url.call_args_list
        self.assertEqual(
            calls[0].args[0],
            "https://bao.example.test:8200/v1/sys/policies/acl/my%20policy",
        )
        for call in calls:
            self.assertIs(call.kwargs["validate_certs"], True)
            self.assertEqual(call.kwargs["ca_path"], "/etc/ca.pem")
            self.assertEqual(call.kwargs["timeout"], 7)
            self.assertEqual(call.kwargs["follow_redirects"], "none")
            self.assertIs(call.kwargs["use_netrc"], False)
            self.assertEqual(
                call.kwargs["headers"]["X-Vault-Token"], "recognizable-token"
            )
        self.assertEqual(calls[1].kwargs["method"], "POST")
        self.assertEqual(json.loads(calls[1].kwargs["data"]), {"type": "kv"})
        self.assertEqual(calls[1].kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(
            calls[2].kwargs["headers"]["Content-Type"], "application/merge-patch+json"
        )
        self.assertEqual(calls[3].kwargs["method"], "DELETE")
        self.assertTrue(calls[4].args[0].endswith("/v1/pki/issuers?list=true"))

    def test_empty_and_missing_responses(self) -> None:
        """Empty bodies return None, 404 maps to None or the error body."""
        with patch.object(client_module, "open_url", return_value=response(b"")):
            self.assertIsNone(self.client.write("auth/token/revoke-self"))
        tombstone = b'{"data": {"data": null, "metadata": {"version": 1}}}'

        def missing(*args: Any, **kwargs: Any) -> None:
            raise http_error(404, tombstone)

        with patch.object(client_module, "open_url", side_effect=missing):
            self.assertIsNone(self.client.get("kv/data/app"))
            body = self.client.read("kv/data/app")
            self.assertIsNotNone(body)
            assert body is not None
            self.assertEqual(body["data"]["metadata"]["version"], 1)
            self.assertEqual(
                self.client.list_keys("pki/issuers"), {"keys": [], "key_info": {}}
            )

    def test_http_error_message(self) -> None:
        """HTTP failures report status and server errors, never the request body."""
        error = http_error(
            400, b'{"errors": ["check-and-set parameter did not match"]}'
        )
        with (
            patch.object(client_module, "open_url", side_effect=error),
            self.assertRaises(BaoError) as raised,
        ):
            self.client.write(
                "kv/data/app", {"data": {"password": "recognizable-secret"}}
            )
        self.assertEqual(raised.exception.status, 400)
        self.assertIn(
            "HTTP 400: check-and-set parameter did not match", str(raised.exception)
        )
        self.assertNotIn("recognizable-secret", str(raised.exception))

    def test_transport_errors(self) -> None:
        """Connection and TLS failures become BaoError without a status."""
        failures: list[Any] = [
            urllib.error.URLError("Connection refused"),
            SSLValidationError("certificate verify failed"),
            TimeoutError("timed out"),
        ]
        for failure in failures:
            with (
                self.subTest(failure=repr(failure)),
                patch.object(client_module, "open_url", side_effect=failure),
                self.assertRaises(BaoError) as raised,
            ):
                self.client.get("sys/health")
            self.assertIsNone(raised.exception.status)
            self.assertIn("GET sys/health failed", str(raised.exception))

    def test_invalid_json(self) -> None:
        """Non JSON bodies fail instead of being returned as data."""
        with (
            patch.object(client_module, "open_url", return_value=response(b"<html>")),
            self.assertRaisesRegex(BaoError, "invalid JSON"),
        ):
            self.client.get("sys/health")

    def test_login_and_revoke(self) -> None:
        """Login sends no token header and revoke-self uses the given token."""
        auth = b'{"auth": {"client_token": "new-token", "accessor": "acc"}}'
        with patch.object(
            client_module, "open_url", return_value=response(auth)
        ) as open_url:
            result = self.client.login("approle", "role", "recognizable-secret-id")
            self.client.with_token("new-token").revoke_self()
        self.assertEqual(result["client_token"], "new-token")
        login_call, revoke_call = open_url.call_args_list
        self.assertNotIn("X-Vault-Token", login_call.kwargs["headers"])
        self.assertTrue(login_call.args[0].endswith("/v1/auth/approle/login"))
        self.assertEqual(revoke_call.kwargs["headers"]["X-Vault-Token"], "new-token")
        self.assertTrue(revoke_call.args[0].endswith("/v1/auth/token/revoke-self"))

    def test_login_without_auth_data(self) -> None:
        """A login response without auth data is an error."""
        with (
            patch.object(
                client_module, "open_url", return_value=response(b'{"data": {}}')
            ),
            self.assertRaisesRegex(BaoError, "returned no auth data"),
        ):
            self.client.login("approle", "role", "secret")

    def test_validate_url(self) -> None:
        """Only credential free https origins are accepted."""
        self.assertEqual(
            validate_url("https://bao.example.test:8200/"),
            "https://bao.example.test:8200",
        )
        invalid = (
            "http://bao.example.test",
            "https://user:pw@bao.example.test",
            "https://bao.example.test/v1",
            "",
            "bao.example.test",
        )
        for bad in invalid:
            with self.subTest(url=bad), self.assertRaises(ValueError):
                validate_url(bad)
