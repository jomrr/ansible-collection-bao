# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Generic read, compare and write flow of the state modules; not a public API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import (
    Fields,
    Mapping,
    desired_from,
    merge,
    plan,
    to_api,
    view,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import state_result
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

if TYPE_CHECKING:
    from collections.abc import Callable

TOKEN_FIELDS: Fields = {
    "token_policies": "list",
    "token_bound_cidrs": "list",
    "token_ttl": "duration",
    "token_max_ttl": "duration",
    "token_explicit_max_ttl": "duration",
    "token_num_uses": "int",
    "token_period": "duration",
    "token_no_default_policy": "bool",
    "token_type": "str",
}


@dataclass(frozen=True)
class Resource:
    """One API resource with its comparable fields and the run mode."""

    client: Api
    path: str
    fields: Fields
    check_mode: bool

    def read(self) -> Mapping | None:
        """Read the current state; None when the resource does not exist."""
        return self.client.get(self.path)


def remove(
    resource: Resource, current: Mapping | None, before: Mapping
) -> dict[str, Any]:
    """Delete the resource when it exists."""
    if current is None:
        return state_result(False, {}, {})
    if not resource.check_mode:
        resource.client.delete(resource.path)
    return state_result(True, before, {})


def ensure(
    resource: Resource,
    current: Mapping | None,
    desired: Mapping,
    *,
    body: Mapping | None = None,
    patch: bool = False,
) -> dict[str, Any]:
    """Write the desired fields when they differ from the current state."""
    fields = resource.fields
    changes = plan(fields, current, desired)
    changed = current is None or bool(changes)
    if changed and not resource.check_mode:
        payload = to_api(fields, desired) if body is None else body
        if patch and current is not None:
            resource.client.patch(resource.path, payload)
        else:
            resource.client.write(resource.path, payload)
    after = view(fields, merge(current, desired))
    return state_result(changed, view(fields, current), after)


def reconcile(
    resource: Resource,
    params: Mapping,
    *,
    body: Callable[[Mapping | None, Mapping], Mapping | None] | None = None,
    patch: bool = False,
) -> tuple[dict[str, Any], Mapping | None]:
    """Read, then remove or ensure the resource; return the result and current state."""
    current = resource.read()
    if params["state"] == "absent":
        return remove(resource, current, view(resource.fields, current)), current
    desired = desired_from(params, resource.fields)
    payload = None if body is None else body(current, desired)
    return ensure(resource, current, desired, body=payload, patch=patch), current
