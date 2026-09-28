# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Server health state read; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils.client import Api, BaoError

# Every state answers HTTP 200, so the state comes from the body.
QUERY = {"standbyok": "true", "sealedcode": "200", "uninitcode": "200"}


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Read the initialization, seal and readiness state; identical in check mode."""
    del params, check_mode
    body = client.read("sys/health", QUERY)
    if not body or "initialized" not in body or "sealed" not in body:
        raise BaoError("GET sys/health returned no health state")
    initialized = bool(body["initialized"])
    sealed = bool(body["sealed"])
    standby = bool(body.get("standby"))
    return {
        "changed": False,
        "initialized": initialized,
        "sealed": sealed,
        "standby": standby,
        "ready": initialized and not sealed and not standby,
        "version": str(body.get("version") or ""),
    }
