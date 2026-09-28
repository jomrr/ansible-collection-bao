# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Raft snapshot save and explicit restore with a temporary directory."""

from __future__ import annotations

import gzip
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils.client import BaoError
from ansible_collections.jomrr.bao.plugins.modules import raft_snapshot
from ansible_collections.jomrr.bao.tests.unit.plugins.support import (
    FakeClient,
    run_module_under_test,
)

SNAPSHOT = "sys/storage/raft/snapshot"
CONTENT = gzip.compress(b"recognizable-snapshot-content")


class RaftSnapshotTests(unittest.TestCase):
    """Snapshots are written once, atomically, and restored only on request."""

    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.path = self.directory / "raft.snap"
        self.client = FakeClient({("DOWNLOAD", SNAPSHOT): CONTENT})

    def run_module(self, check_mode: bool = False, **inputs: Any) -> dict[str, Any]:
        """Run the module for the snapshot path."""
        params = {"path": str(self.path), **inputs}
        return run_module_under_test(
            raft_snapshot, params, self.client, check_mode=check_mode
        )

    def test_save(self) -> None:
        """A missing file is written privately with size and checksum."""
        result = self.run_module()
        self.assertTrue(result["changed"])
        self.assertEqual(self.path.read_bytes(), CONTENT)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(result["size"], len(CONTENT))
        self.assertEqual(result["checksum"], hashlib.sha256(CONTENT).hexdigest())
        self.assertEqual(sorted(self.directory.iterdir()), [self.path])

    def test_existing_file_is_kept_unless_overwritten(self) -> None:
        """An existing file needs overwrite to be replaced."""
        self.path.write_bytes(b"earlier snapshot")
        result = self.run_module()
        self.assertFalse(result["changed"])
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.path.read_bytes(), b"earlier snapshot")
        result = self.run_module(overwrite=True)
        self.assertTrue(result["changed"])
        self.assertEqual(self.path.read_bytes(), CONTENT)

    def test_check_mode_writes_nothing(self) -> None:
        """Check mode predicts the download without calling the server."""
        result = self.run_module(check_mode=True)
        self.assertTrue(result["changed"])
        self.assertIsNone(result["size"])
        self.assertEqual(self.client.calls, [])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_failed_download_leaves_no_file(self) -> None:
        """Errors and responses that are no snapshot leave the directory empty."""
        error = BaoError(f"GET {SNAPSHOT} failed with HTTP 404: unsupported path", 404)
        for label, response in (
            ("error", error),
            ("no snapshot", b"<html>"),
            ("empty", b""),
        ):
            with self.subTest(response=label):
                self.client.responses[("DOWNLOAD", SNAPSHOT)] = response
                result = self.run_module()
                self.assertTrue(result["failed"])
                self.assertIn(SNAPSHOT, result["msg"])
                self.assertEqual(list(self.directory.iterdir()), [])

    def test_invalid_targets(self) -> None:
        """A directory as path or a missing directory fails before the download."""
        missing = self.directory / "missing" / "raft.snap"
        for path in (self.directory, missing):
            with self.subTest(path=path.name):
                result = self.run_module(path=str(path))
                self.assertTrue(result["failed"])
                self.assertEqual(self.client.calls, [])

    def test_restore(self) -> None:
        """Restore uploads the file; force selects the forced endpoint."""
        self.path.write_bytes(CONTENT)
        body = {"size": len(CONTENT), "sha256": hashlib.sha256(CONTENT).hexdigest()}
        for force, endpoint in ((False, SNAPSHOT), (True, f"{SNAPSHOT}-force")):
            with self.subTest(force=force):
                self.client.calls.clear()
                result = self.run_module(state="restored", force=force)
                self.assertTrue(result["changed"])
                self.assertEqual(self.client.calls, [("UPLOAD", endpoint, body)])

    def test_restore_needs_a_file_and_skips_check_mode(self) -> None:
        """A missing or empty file fails; check mode never uploads."""
        result = self.run_module(state="restored")
        self.assertTrue(result["failed"])
        self.path.write_bytes(b"")
        self.assertTrue(self.run_module(state="restored")["failed"])
        self.path.write_bytes(CONTENT)
        result = self.run_module(state="restored", check_mode=True)
        self.assertTrue(result["changed"])
        self.assertIn("Would restore", result["msg"])
        self.assertEqual(self.client.calls, [])
