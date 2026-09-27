# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""State comparison helpers shared by the state modules; not a public API."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from typing import Any, Literal

from ansible_collections.jomrr.bao.plugins.module_utils._duration import to_seconds

Kind = Literal["str", "int", "bool", "list", "csv", "cidrs", "duration", "map"]
Fields = dict[str, Kind]
Mapping = dict[str, Any]


def as_list(value: object) -> list[str]:
    """Return a value as a list of strings; comma strings are split."""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _mapping(value: object) -> dict[str, Any]:
    """Return a mapping with string keys."""
    if not isinstance(value, dict):
        raise TypeError(f"expected a mapping, got {type(value).__name__}")
    return {str(key): item for key, item in value.items()}


def _cidr(value: str) -> str:
    """Return a network as OpenBao reports it: host networks without a suffix."""
    text = value.strip()
    address, _separator, prefix = text.partition("/")
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return text
    if prefix in ("", str(parsed.max_prefixlen)):
        return str(parsed)
    return f"{parsed}/{prefix}"


_NORMALIZERS: dict[str, Callable[[object], object]] = {
    "str": str,
    "int": lambda value: int(str(value)),
    "bool": bool,
    "duration": to_seconds,
    "list": lambda value: sorted(as_list(value)),
    "csv": lambda value: sorted(as_list(value)),
    "cidrs": lambda value: sorted(_cidr(item) for item in as_list(value)),
    "map": _mapping,
}
# OpenBao reports unset collections as null or as an empty collection.
_EMPTY: dict[str, Callable[[], object]] = {
    "list": list,
    "csv": list,
    "cidrs": list,
    "map": dict,
}


def normalize(kind: Kind, value: object) -> object:
    """Return a comparable representation of a field value."""
    if value is None:
        empty = _EMPTY.get(kind)
        return None if empty is None else empty()
    return _NORMALIZERS[kind](value)


def desired_from(params: Mapping, fields: Fields) -> Mapping:
    """Collect the requested field values, leaving out unset options."""
    return {name: params[name] for name in fields if params.get(name) is not None}


def plan(fields: Fields, current: Mapping | None, desired: Mapping) -> Mapping:
    """Return the desired fields whose normalized value differs from current."""
    changes: Mapping = {}
    for name, value in desired.items():
        if value is None:
            continue
        kind = fields[name]
        current_value = None if current is None else current.get(name)
        if normalize(kind, current_value) != normalize(kind, value):
            changes[name] = value
    return changes


def view(fields: Fields, mapping: Mapping | None) -> Mapping:
    """Return the normalized view of the known fields for diff output."""
    if not mapping:
        return {}
    known = {
        name: normalize(kind, mapping[name])
        for name, kind in fields.items()
        if name in mapping
    }
    return {name: value for name, value in known.items() if value is not None}


def merge(current: Mapping | None, desired: Mapping) -> Mapping:
    """Overlay the requested values on the current state."""
    merged = dict(current or {})
    merged.update({name: value for name, value in desired.items() if value is not None})
    return merged


def to_api(fields: Fields, values: Mapping) -> Mapping:
    """Convert values to the request representation expected by OpenBao."""
    body: Mapping = {}
    for name, value in values.items():
        if value is None:
            continue
        if fields.get(name) == "csv":
            body[name] = ",".join(as_list(value))
        else:
            body[name] = value
    return body
