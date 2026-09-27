# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Test doubles: a recording API client and a module runner without Ansible."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import Any, cast
from unittest.mock import Mock, patch

from ansible_collections.jomrr.bao.plugins.module_utils import _module
from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError, Json

Call = tuple[str, str, Json | None]
WRITE_METHODS = ("POST", "PATCH", "DELETE", "LOGIN")
CONNECTION = {
    "url": "https://bao.example.test:8200",
    "token": "fake-token",
    "timeout": 30,
}


class FakeClient:
    """Serve canned responses keyed by (method, path) and record every call."""

    def __init__(
        self,
        responses: dict[tuple[str, str], Any] | None = None,
        token: str = "fake-token",
    ) -> None:
        self.responses: dict[tuple[str, str], Any] = dict(responses or {})
        self.calls: list[Call] = []
        self.token = token

    def _respond(self, method: str, path: str, body: Json | None = None) -> Any:
        self.calls.append((method, path, body))
        if (method, path) not in self.responses:
            return None
        value = self.responses[(method, path)]
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            return value(body)
        return value

    def get(self, path: str, query: dict[str, str] | None = None) -> Json | None:
        """Return the canned GET data; missing entries model HTTP 404."""
        return cast("Json | None", self._respond("GET", path, query))

    def read(self, path: str, query: dict[str, str] | None = None) -> Json | None:
        """Return the canned full response body."""
        return cast("Json | None", self._respond("READ", path, query))

    def write(self, path: str, body: Json | None = None) -> Json | None:
        """Record a POST and return its canned response."""
        return cast(
            "Json | None", self._respond("POST", path, {} if body is None else body)
        )

    def patch(self, path: str, body: Json) -> Json | None:
        """Record a PATCH and return its canned response."""
        return cast("Json | None", self._respond("PATCH", path, body))

    def delete(self, path: str) -> None:
        """Record a DELETE."""
        self._respond("DELETE", path)

    def list_keys(self, path: str) -> Json:
        """Return the canned list data or an empty listing."""
        value = self._respond("LIST", path)
        return cast(Json, value if value is not None else {"keys": [], "key_info": {}})

    def login(self, mount: str, role_id: str, secret_id: str) -> Json:
        """Record a login and return its canned auth mapping."""
        value = self._respond(
            "LOGIN", f"auth/{mount}/login", {"role_id": role_id, "secret_id": secret_id}
        )
        if value is None:
            raise BaoError(
                f"login at auth/{mount} failed with HTTP 400: invalid role", 400
            )
        return cast(Json, value)

    def revoke_self(self) -> None:
        """Record a revocation of the client's current token."""
        self._respond("POST", "auth/token/revoke-self", {"token": self.token})

    def with_token(self, token: str) -> FakeClient:
        """Return a client sharing the responses and call log with another token."""
        clone = FakeClient(self.responses, token)
        clone.calls = self.calls
        return clone

    def writes(self) -> list[Call]:
        """Return the recorded mutating calls."""
        return [call for call in self.calls if call[0] in WRITE_METHODS]


class ModuleResult(BaseException):
    """Carry the terminating module result out of the patched exit functions."""

    def __init__(self, **result: Any) -> None:
        super().__init__()
        self.result = result


def _exit(**result: Any) -> None:
    raise ModuleResult(**result)


def _fail(**result: Any) -> None:
    raise ModuleResult(failed=True, **result)


def run_module_under_test(
    module: ModuleType,
    inputs: dict[str, Any],
    client: FakeClient,
    *,
    check_mode: bool = False,
) -> dict[str, Any]:
    """Run a module's main() with argument defaults, the inputs and the fake client."""
    mock = Mock()
    mock.check_mode = check_mode
    mock.exit_json.side_effect = _exit
    mock.fail_json.side_effect = _fail

    def make_module(**kwargs: Any) -> Mock:
        spec: dict[str, dict[str, Any]] = kwargs["argument_spec"]
        mock.params = {key: options.get("default") for key, options in spec.items()}
        mock.params.update(CONNECTION)
        mock.params.update(inputs)
        return mock

    main: Callable[[], None] = module.main
    with (
        patch.object(_module, "AnsibleModule", side_effect=make_module),
        patch.object(_module, "build_client", return_value=client),
    ):
        try:
            main()
        except ModuleResult as done:
            return done.result
    raise AssertionError("module returned without exit_json or fail_json")
