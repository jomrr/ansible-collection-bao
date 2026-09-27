# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Userpass user state; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._compare import Mapping, to_api
from ansible_collections.jomrr.bao.plugins.module_utils._state import (
    TOKEN_FIELDS,
    Resource,
    reconcile,
)
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Reconcile one userpass user; the password is sent only at creation."""
    path = f"auth/{params['mount']}/users/{params['name']}"
    resource = Resource(client, path, TOKEN_FIELDS, check_mode)

    def creation_body(current: Mapping | None, desired: Mapping) -> Mapping | None:
        if current is not None:
            return None
        if not params.get("password"):
            raise ValueError(
                f"user {params['name']} does not exist and needs a password"
            )
        return {**to_api(TOKEN_FIELDS, desired), "password": str(params["password"])}

    return reconcile(resource, params, body=creation_body)[0]
