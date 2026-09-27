# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""KV version 2 secret state and reads; not a public API."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._result import (
    key_view,
    state_result,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api, Json

CHARACTER_CLASSES = {
    "ascii_letters": string.ascii_letters,
    "ascii_lowercase": string.ascii_lowercase,
    "ascii_uppercase": string.ascii_uppercase,
    "digits": string.digits,
    "hexdigits": string.hexdigits,
    "punctuation": string.punctuation,
}
DEFAULT_LENGTH = 32
DEFAULT_CHARS = ["ascii_letters", "digits"]


def data_path(mount: str, path: str) -> str:
    """Return the data API path of a secret."""
    return f"{mount}/data/{path}"


def metadata_path(mount: str, path: str) -> str:
    """Return the metadata API path of a secret."""
    return f"{mount}/metadata/{path}"


def generate_value(spec: dict[str, Any] | None) -> str:
    """Generate a random value from the requested length and character classes."""
    options = spec or {}
    length = DEFAULT_LENGTH if options.get("length") is None else int(options["length"])
    if length < 1:
        raise ValueError("generate length must be positive")
    alphabet = "".join(
        CHARACTER_CLASSES.get(str(name), str(name))
        for name in (options.get("chars") or DEFAULT_CHARS)
    )
    if not alphabet:
        raise ValueError("generate chars must not be empty")
    return "".join(secrets.choice(alphabet) for _index in range(length))


def _values(body: Json | None) -> tuple[bool, Json | None, int]:
    """Split a data read into existence, current values and version."""
    if body is None or "data" not in body:
        return False, None, 0
    data = body.get("data") or {}
    values = data.get("data")
    version = int((data.get("metadata") or {}).get("version") or 0)
    return True, (dict(values) if isinstance(values, dict) else None), version


def read_for_lookup(client: Api, mount: str, path: str, version: int | None) -> Json:
    """Return the data mapping of a secret version for the lookup plugin."""
    query = None if version is None else {"version": str(version)}
    exists, values, _version = _values(client.read(data_path(mount, path), query))
    if not exists:
        raise ValueError(f"KV secret {mount}/{path} not found")
    if values is None:
        raise ValueError(f"KV secret {mount}/{path} has no readable version")
    return values


@dataclass(frozen=True)
class _Secret:
    """One KV secret with its API paths and the run mode."""

    client: Api
    mount: str
    path: str
    check_mode: bool

    def current(self) -> tuple[bool, Json | None, int]:
        """Read metadata and data; values are None when the version was deleted."""
        exists = self.client.get(metadata_path(self.mount, self.path)) is not None
        _found, values, version = _values(
            self.client.read(data_path(self.mount, self.path))
        )
        return exists, values, version

    def write(self, version: int, data: Json) -> int:
        """Write the data with check and set and return the new version."""
        response = self.client.write(
            data_path(self.mount, self.path),
            {"options": {"cas": version}, "data": data},
        )
        written = ((response or {}).get("data") or {}).get("version")
        return int(written or version + 1)


def _present(
    secret: _Secret,
    params: dict[str, Any],
    exists: bool,
    values: Json | None,
    version: int,
) -> dict[str, Any]:
    """Reconcile data and generated keys of an existing or new secret."""
    if exists and values is None:
        raise ValueError(
            f"KV secret {secret.mount}/{secret.path} has metadata but no readable"
            " current version; restore it or delete its metadata first"
        )
    data: Json = dict(params.get("data") or {})
    generate: dict[str, Any] = dict(params.get("generate") or {})
    merged = {**(values or {}), **data}
    missing = [key for key in generate if key not in merged]
    changed = values is None or merged != values or bool(missing)
    new_version = version + 1 if changed else version
    if changed and not secret.check_mode:
        merged.update({key: generate_value(generate[key]) for key in missing})
        new_version = secret.write(version, merged)
    before = {**key_view(values), "version": version} if values is not None else {}
    after = {"keys": sorted(set(merged) | set(generate)), "version": new_version}
    return state_result(changed, before, after, version=new_version)


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile the data of one KV version 2 secret with check and set."""
    overlap = sorted(set(params.get("data") or {}) & set(params.get("generate") or {}))
    if overlap:
        raise ValueError(f"data and generate share keys: {', '.join(overlap)}")
    secret = _Secret(
        client,
        str(params["mount"]).strip("/"),
        str(params["path"]).strip("/"),
        check_mode,
    )
    exists, values, version = secret.current()
    if params["state"] != "absent":
        return _present(secret, params, exists, values, version)
    if not exists:
        return state_result(False, {}, {}, version=0)
    if not check_mode:
        client.delete(metadata_path(secret.mount, secret.path))
    before = {**key_view(values), "version": version} if values is not None else {}
    return state_result(True, before, {}, version=0)
