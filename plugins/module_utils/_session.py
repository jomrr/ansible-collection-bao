# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Session actions: AppRole login and logout; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._result import action_result
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api


def login(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Log in with an AppRole and return the session token."""
    mount = str(params["mount"])
    if check_mode:
        return action_result(
            True,
            f"Would log in at auth/{mount}",
            token=None,
            accessor=None,
            lease_duration=0,
            policies=[],
        )
    auth = client.login(mount, str(params["role_id"]), str(params["secret_id"]))
    return action_result(
        True,
        f"Logged in at auth/{mount}",
        token=auth.get("client_token"),
        accessor=auth.get("accessor"),
        lease_duration=int(auth.get("lease_duration") or 0),
        policies=list(auth.get("token_policies") or auth.get("policies") or []),
    )


def logout(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Revoke the session token given as the connection token."""
    del params
    if check_mode:
        return action_result(True, "Would revoke the session token")
    client.revoke_self()
    return action_result(True, "Revoked the session token")
