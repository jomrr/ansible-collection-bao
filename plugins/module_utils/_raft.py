# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Raft snapshot save and restore; not a public API."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._module import FileModule
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api, BaoError

SNAPSHOT = "sys/storage/raft/snapshot"
FORCE = "sys/storage/raft/snapshot-force"
GZIP_MAGIC = b"\x1f\x8b"
DEFAULT_MODE = "0600"
PRIVATE_UMASK = 0o077


def _result(module: FileModule, changed: bool, msg: str, path: str) -> dict[str, Any]:
    """Describe the snapshot file; size and checksum are null while it is missing."""
    exists = os.path.isfile(path)
    return {
        "changed": changed,
        "msg": msg,
        "path": path,
        "size": os.path.getsize(path) if exists else None,
        "checksum": module.sha256(path) if exists else None,
    }


def _file_args(module: FileModule) -> dict[str, Any]:
    """Return the requested file attributes; snapshots are private by default."""
    file_args = module.load_file_common_arguments(module.params)
    if file_args.get("mode") is None:
        file_args["mode"] = DEFAULT_MODE
    return file_args


def _download(client: Api, directory: str) -> str:
    """Download the snapshot into a private temporary file next to the target."""
    handle, temporary = tempfile.mkstemp(prefix=".bao-snapshot-", dir=directory)
    try:
        with os.fdopen(handle, "wb") as target:
            client.download(SNAPSHOT, target)
        with open(temporary, "rb") as written:
            if written.read(2) != GZIP_MAGIC:
                raise BaoError(f"GET {SNAPSHOT} returned no snapshot")
    except BaseException:
        os.unlink(temporary)
        raise
    return temporary


def _move(module: FileModule, temporary: str, path: str) -> None:
    """Move the download into place; a new file grants no access to others."""
    unsafe_writes = bool(module.params["unsafe_writes"])
    previous = os.umask(PRIVATE_UMASK)
    try:
        module.atomic_move(temporary, path, unsafe_writes=unsafe_writes)
    finally:
        os.umask(previous)
        if os.path.exists(temporary):
            os.unlink(temporary)


def _save(module: FileModule, client: Api, path: str) -> dict[str, Any]:
    """Save a snapshot unless the file exists and must not be replaced."""
    if os.path.isdir(path):
        raise ValueError(f"{path} is a directory")
    directory = os.path.dirname(path) or "."
    if not os.path.isdir(directory):
        raise ValueError(f"directory {directory} does not exist")
    file_args = _file_args(module)
    if os.path.exists(path) and not module.params["overwrite"]:
        changed = module.set_fs_attributes_if_different(file_args, False)
        return _result(module, changed, f"Snapshot file {path} exists", path)
    if module.check_mode:
        return _result(module, True, f"Would save a snapshot to {path}", path)
    _move(module, _download(client, directory), path)
    module.set_fs_attributes_if_different(file_args, True)
    return _result(module, True, f"Saved a snapshot to {path}", path)


def _restore(module: FileModule, client: Api, path: str) -> dict[str, Any]:
    """Install the snapshot file on the server."""
    if not os.path.isfile(path):
        raise ValueError(f"snapshot file {path} does not exist")
    size = os.path.getsize(path)
    if size == 0:
        raise ValueError(f"snapshot file {path} is empty")
    if module.check_mode:
        return _result(module, True, f"Would restore the snapshot {path}", path)
    with open(path, "rb") as source:
        client.upload(FORCE if module.params["force"] else SNAPSHOT, source, size)
    return _result(module, True, f"Restored the snapshot {path}", path)


def run(module: FileModule, client: Api) -> dict[str, Any]:
    """Save a snapshot to a file or restore one on request."""
    path = str(module.params["path"])
    if module.params["state"] == "restored":
        return _restore(module, client, path)
    return _save(module, client, path)
