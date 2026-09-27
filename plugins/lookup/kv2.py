# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Read OpenBao KV version 2 secrets with an existing session token."""

from __future__ import annotations

DOCUMENTATION = r"""
name: kv2
author: Jonas Mauer (@jomrr)
version_added: 0.1.0
short_description: Read KV version 2 secrets with an existing session token
description:
- Read KV version 2 secrets on the controller with a token obtained elsewhere; the lookup never logs in.
- Without O(key) each result is the secret's data mapping.
- Nothing is cached and no state is kept between calls.
options:
  _terms:
    description: Secret paths below the mount.
    required: true
    type: list
    elements: str
  mount:
    description: KV version 2 mount.
    type: str
    required: true
  key:
    description: Return only this key of each secret.
    type: str
  version:
    description: Secret version to read; the current version when omitted.
    type: int
  url:
    description: HTTPS API origin of the OpenBao server.
    type: str
    vars:
    - name: bao_url
    env:
    - name: BAO_ADDR
  ca_file:
    description: CA bundle verifying the server certificate; the system trust store when omitted.
    type: str
    vars:
    - name: bao_ca_file
    env:
    - name: BAO_CACERT
  token:
    description: Session token, typically from M(jomrr.bao.login).
    type: str
    vars:
    - name: bao_token
    env:
    - name: BAO_TOKEN
  timeout:
    description: HTTP request timeout in seconds.
    type: int
    default: 30
notes:
- A missing path or key fails with the mount and path in the message; secret content is never included.
- TLS verification is always enabled.
"""

EXAMPLES = r"""
- name: Use a database password from OpenBao
  ansible.builtin.set_fact:
    db_password: "{{ lookup('jomrr.bao.kv2', 'app/database', mount='automation', key='password') }}"
  vars:
    bao_url: https://bao.example.test:8200
    bao_ca_file: /etc/pki/tls/certs/bao-ca.pem
  no_log: true

- name: Read the whole secret mapping
  ansible.builtin.debug:
    msg: "{{ lookup('jomrr.bao.kv2', 'app/database', mount='automation') | dict2items | map(attribute='key') }}"
"""

RETURN = r"""
_raw:
  description: One entry per term, the data mapping or the value of O(key).
  type: list
  elements: raw
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
import os
from collections.abc import Callable
from typing import Any, cast

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible_collections.jomrr.bao.plugins.module_utils._kv2 import read_for_lookup
from ansible_collections.jomrr.bao.plugins.module_utils.client import (
    BaoClient,
    BaoError,
)

# pylint: enable=wrong-import-position


class LookupModule(LookupBase):
    """Read KV version 2 data with an existing token."""

    def _option(self, name: str) -> Any:
        """Return one resolved plugin option; variable values may still be templates."""
        value = cast(Callable[[str], Any], self.get_option)(name)
        templar = getattr(self, "_templar", None)
        if isinstance(value, str) and templar is not None:
            return cast(Callable[[str], Any], templar.template)(value)
        return value

    def _client(self) -> BaoClient:
        """Build the client from the resolved connection options."""
        url = self._option("url")
        token = self._option("token")
        if not url:
            raise AnsibleError("jomrr.bao.kv2 needs the variable bao_url or BAO_ADDR")
        if not token:
            raise AnsibleError(
                "jomrr.bao.kv2 needs the variable bao_token or BAO_TOKEN"
            )
        ca_file = self._option("ca_file")
        if ca_file:
            ca_file = os.path.expanduser(str(ca_file))
        try:
            return BaoClient(
                str(url), str(token), ca_file, int(self._option("timeout"))
            )
        except ValueError as exc:
            raise AnsibleError(f"jomrr.bao.kv2: {exc}") from exc

    def _read(self, client: BaoClient, mount: str, term: object) -> Any:
        """Return the data mapping or the selected key of one secret."""
        path = str(term).strip("/")
        key = self._option("key")
        try:
            values = read_for_lookup(client, mount, path, self._option("version"))
        except BaoError as exc:
            raise AnsibleError(
                f"reading KV secret {mount}/{path} failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise AnsibleError(str(exc)) from exc
        if key is None:
            return values
        if key not in values:
            raise AnsibleError(f"key '{key}' not found in KV secret {mount}/{path}")
        return values[key]

    def run(
        self,
        terms: list[object],
        variables: dict[str, object] | None = None,
        **kwargs: object,
    ) -> list[Any]:
        """Return the data mapping or the selected key for every term."""
        cast(Callable[..., None], self.set_options)(
            var_options=variables, direct=kwargs
        )
        mount = str(self._option("mount")).strip("/")
        client = self._client()
        return [self._read(client, mount, term) for term in terms]
