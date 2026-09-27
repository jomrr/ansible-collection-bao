# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""ACL policy state; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import Fields
from ansible_collections.jomrr.bao.plugins.module_utils._state import (
    Resource,
    ensure,
    remove,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api

FIELDS: Fields = {"policy": "str"}


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one ACL policy; the document is compared without outer whitespace."""
    resource = Resource(
        client, f"sys/policies/acl/{params['name']}", FIELDS, check_mode
    )
    current = client.get(resource.path)
    if current is not None:
        current = {"policy": str(current.get("policy") or "").strip()}
    if params["state"] == "absent":
        return remove(resource, current, current or {})
    rules = params.get("rules")
    if rules is None:
        raise ValueError("rules is required when state is present")
    desired = {"policy": str(rules).strip()}
    return ensure(resource, current, desired, body={"policy": str(rules)})
