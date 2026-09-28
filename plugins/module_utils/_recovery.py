# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Recovery key generation and rotation; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._result import action_result
from ansible_collections.jomrr.bao.plugins.module_utils.client import (
    Api,
    BaoError,
    Json,
)

INIT = "sys/rotate/recovery/init"
UPDATE = "sys/rotate/recovery/update"


def _data(response: Json | None) -> Json:
    """Return the data mapping of a response."""
    return dict((response or {}).get("data") or {})


def _validate(params: dict[str, Any]) -> None:
    """Check the requested share layout before contacting the server."""
    shares = int(params["shares"])
    threshold = int(params["threshold"])
    if shares < 1 or threshold < 1 or threshold > shares:
        raise ValueError("threshold must be between 1 and shares")
    pgp_keys = params.get("pgp_keys")
    if pgp_keys and len(pgp_keys) != shares:
        raise ValueError("pgp_keys must contain one key per share")


def _request(params: dict[str, Any]) -> Json:
    """Build the request that starts a generation or rotation."""
    body: Json = {
        "secret_shares": int(params["shares"]),
        "secret_threshold": int(params["threshold"]),
    }
    if params.get("pgp_keys"):
        body["pgp_keys"] = list(params["pgp_keys"])
        body["backup"] = bool(params.get("backup"))
    return body


def _layout(client: Api) -> tuple[int, int]:
    """Return the current number of shares and the threshold."""
    status = client.read("sys/seal-status") or {}
    return int(status.get("n") or 0), int(status.get("t") or 0)


def _cancel(client: Api) -> str:
    """Cancel the running attempt and describe the outcome."""
    try:
        client.delete(INIT)
    except BaoError:
        return "the attempt could not be cancelled"
    return "the attempt was cancelled"


def _rotate(client: Api, params: dict[str, Any], required: int) -> Json:
    """Start the rotation and submit the existing shares until it completes."""
    started = _data(client.write(INIT, _request(params)))
    if started.get("complete"):
        return started
    nonce = str(started.get("nonce") or "")
    shares = [str(share) for share in params.get("keys") or []][:required]
    try:
        for share in shares:
            progress = _data(client.write(UPDATE, {"key": share, "nonce": nonce}))
            if progress.get("complete"):
                return progress
    except BaoError as exc:
        raise BaoError(f"{exc}; {_cancel(client)}", exc.status) from exc
    raise BaoError(f"the given shares did not complete the rotation; {_cancel(client)}")


def _result(changed: bool, msg: str, data: Json, client: Api) -> dict[str, Any]:
    """Return the module result; shares are only present after a change."""
    shares, threshold = _layout(client)
    return action_result(
        changed,
        msg,
        recovery_keys=list(data.get("keys") or []),
        recovery_keys_base64=list(data.get("keys_base64") or []),
        pgp_fingerprints=list(data.get("pgp_fingerprints") or []),
        shares=shares,
        threshold=threshold,
    )


def run(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Generate missing recovery keys or rotate them on request."""
    _validate(params)
    status = client.get(INIT) or {}
    required = int(status.get("required") or 0)
    if required and params["state"] == "present":
        return _result(False, "Recovery keys exist", {}, client)
    action = "rotate" if required else "generate"
    if status.get("started") and not params.get("force"):
        raise ValueError(
            "a recovery key rotation is already in progress; set force to cancel it"
        )
    given = len(params.get("keys") or [])
    if given < required:
        raise ValueError(f"rotation needs {required} existing shares, {given} given")
    if check_mode:
        return _result(True, f"Would {action} the recovery keys", {}, client)
    if status.get("started"):
        client.delete(INIT)
    data = _rotate(client, params, required)
    return _result(True, f"Recovery keys {action}d", data, client)
