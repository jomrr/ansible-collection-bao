# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""HTTP client for the OpenBao API shared by modules and the kv2 lookup."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
from collections.abc import Callable
from http.client import HTTPResponse
from typing import Any, Protocol, cast

from ansible.module_utils.urls import ConnectionError as UrlConnectionError
from ansible.module_utils.urls import SSLValidationError, open_url

Json = dict[str, Any]
CONTENT_TYPES = {"PATCH": "application/merge-patch+json"}


class BaoError(Exception):
    """Failed OpenBao request carrying the HTTP status and the server's error list."""

    def __init__(
        self, message: str, status: int | None = None, body: Json | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class Api(Protocol):
    """Request interface implemented by BaoClient and by test doubles."""

    def get(self, path: str, query: dict[str, str] | None = None) -> Json | None:
        """Return the data mapping of a GET response or None for HTTP 404."""
        raise NotImplementedError

    def read(self, path: str, query: dict[str, str] | None = None) -> Json | None:
        """Return the full GET response body, including the body of an HTTP 404."""
        raise NotImplementedError

    def write(self, path: str, body: Json | None = None) -> Json | None:
        """POST a JSON body and return the response body."""
        raise NotImplementedError

    def patch(self, path: str, body: Json) -> Json | None:
        """Send a JSON merge patch and return the response body."""
        raise NotImplementedError

    def delete(self, path: str) -> None:
        """DELETE a path."""
        raise NotImplementedError

    def list_keys(self, path: str) -> Json:
        """Return the data of a list request, empty when the path has no entries."""
        raise NotImplementedError

    def login(self, mount: str, role_id: str, secret_id: str) -> Json:
        """Log in with an AppRole and return the auth mapping."""
        raise NotImplementedError

    def revoke_self(self) -> None:
        """Revoke the client's own token."""
        raise NotImplementedError

    def with_token(self, token: str) -> Api:
        """Return a client for the same server using another token."""
        raise NotImplementedError


def validate_url(value: str) -> str:
    """Return the normalized HTTPS origin or raise ValueError."""
    url = str(value or "").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("url must be an absolute https URL")
    if parsed.username or parsed.password:
        raise ValueError("url must not contain credentials")
    if parsed.path or parsed.query or parsed.fragment:
        raise ValueError("url must not contain a path, query or fragment")
    return url


def _decode(raw: bytes) -> Json | None:
    """Parse a JSON response body; empty bodies return None."""
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BaoError("OpenBao returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise BaoError("OpenBao returned an unexpected JSON document")
    return cast(Json, value)


def _error_body(raw: bytes) -> Json | None:
    """Parse an error body without raising on unexpected content."""
    try:
        return _decode(raw)
    except BaoError:
        return None


def _errors(body: Json | None) -> list[str]:
    """Return the server's error strings from an error body."""
    errors = body.get("errors") if body else None
    if not isinstance(errors, list):
        return []
    return [str(error).strip() for error in errors if str(error).strip()]


def _reason(exc: Exception) -> str:
    """Describe a transport failure without request content."""
    if isinstance(exc, urllib.error.URLError):
        return str(exc.reason)
    return str(exc)


def _http_error(method: str, path: str, exc: urllib.error.HTTPError) -> BaoError:
    """Translate an HTTP error into a BaoError with the server's error list."""
    error_body = _error_body(exc.read())
    errors = _errors(error_body)
    detail = "; ".join(errors) if errors else "no error detail"
    return BaoError(
        f"{method} {path} failed with HTTP {exc.code}: {detail}", exc.code, error_body
    )


class BaoClient:
    """Small urllib based client with mandatory TLS verification."""

    def __init__(self, url: str, token: str, ca_file: str | None, timeout: int) -> None:
        """Validate the origin and keep the connection settings."""
        self.url = validate_url(url)
        self.token = token
        self.ca_file = ca_file
        self.timeout = timeout

    def with_token(self, token: str) -> BaoClient:
        """Return a client for the same server using another token."""
        return BaoClient(self.url, token, self.ca_file, self.timeout)

    def _url(self, path: str, query: dict[str, str] | None) -> str:
        """Build the absolute request URL below /v1."""
        url = f"{self.url}/v1/{urllib.parse.quote(path.strip('/'), safe='/')}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        return url

    def _headers(self, method: str, body: Json | None) -> dict[str, str]:
        """Return the token and content type headers for a request."""
        headers: dict[str, str] = {}
        if self.token:
            headers["X-Vault-Token"] = self.token
        if body is not None:
            headers["Content-Type"] = CONTENT_TYPES.get(method, "application/json")
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Json | None = None,
        query: dict[str, str] | None = None,
    ) -> Json | None:
        """Execute one API request below /v1 and return the parsed body."""
        data = None if body is None else json.dumps(body).encode("utf-8")
        try:
            with cast(Callable[..., HTTPResponse], open_url)(
                self._url(path, query),
                data=data,
                headers=self._headers(method, body),
                method=method,
                timeout=self.timeout,
                validate_certs=True,
                ca_path=self.ca_file,
                follow_redirects="none",
                use_netrc=False,
            ) as response:
                return _decode(response.read())
        except urllib.error.HTTPError as exc:
            raise _http_error(method, path, exc) from exc
        except (
            urllib.error.URLError,
            UrlConnectionError,
            SSLValidationError,
            OSError,
        ) as exc:
            raise BaoError(f"{method} {path} failed: {_reason(exc)}") from exc

    def get(self, path: str, query: dict[str, str] | None = None) -> Json | None:
        """Return the data mapping of a GET response or None for HTTP 404."""
        try:
            response = self.request("GET", path, query=query)
        except BaoError as exc:
            if exc.status == 404:
                return None
            raise
        if response is None:
            return None
        return cast("Json | None", response.get("data"))

    def read(self, path: str, query: dict[str, str] | None = None) -> Json | None:
        """Return the full GET response body, including the body of an HTTP 404."""
        try:
            return self.request("GET", path, query=query)
        except BaoError as exc:
            if exc.status == 404:
                return exc.body
            raise

    def write(self, path: str, body: Json | None = None) -> Json | None:
        """POST a JSON body and return the response body."""
        return self.request("POST", path, body={} if body is None else body)

    def patch(self, path: str, body: Json) -> Json | None:
        """Send a JSON merge patch and return the response body."""
        return self.request("PATCH", path, body=body)

    def delete(self, path: str) -> None:
        """DELETE a path."""
        self.request("DELETE", path)

    def list_keys(self, path: str) -> Json:
        """Return the data of a list request, empty when the path has no entries."""
        data = self.get(path, query={"list": "true"})
        return data if data is not None else {"keys": [], "key_info": {}}

    def login(self, mount: str, role_id: str, secret_id: str) -> Json:
        """Log in with an AppRole and return the auth mapping."""
        response = self.with_token("").request(
            "POST",
            f"auth/{mount}/login",
            body={"role_id": role_id, "secret_id": secret_id},
        )
        auth = response.get("auth") if response else None
        if not isinstance(auth, dict):
            raise BaoError(f"login at auth/{mount} returned no auth data")
        return cast(Json, auth)

    def revoke_self(self) -> None:
        """Revoke the client's own token."""
        self.request("POST", "auth/token/revoke-self", body={})
