# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""PKI actions: authority generation, CRL rotation, ACME EAB keys; not a public API."""

from __future__ import annotations

from typing import Any

from ansible_collections.jomrr.bao.plugins.module_utils._pki_issuer import (
    find_issuer,
    find_key,
)
from ansible_collections.jomrr.bao.plugins.module_utils._result import action_result
from ansible_collections.jomrr.bao.plugins.module_utils.client import Api, Json

SUBJECT_FIELDS = (
    "common_name",
    "ou",
    "organization",
    "country",
    "locality",
    "province",
    "street_address",
    "postal_code",
)
GENERATE_FIELDS = SUBJECT_FIELDS + (
    "alt_names",
    "ip_sans",
    "uri_sans",
    "other_sans",
    "ttl",
    "not_after",
    "key_type",
    "key_bits",
    "key_name",
    "max_path_length",
    "permitted_dns_domains",
    "exclude_cn_from_sans",
)
SIGN_FIELDS = SUBJECT_FIELDS + ("max_path_length", "permitted_dns_domains")


def _data(response: Json | None) -> Json:
    """Return the data mapping of a response."""
    return dict((response or {}).get("data") or {})


def _body(params: dict[str, Any], names: tuple[str, ...]) -> Json:
    """Collect the given request fields from the parameters."""
    return {name: params[name] for name in names if params.get(name) is not None}


def _existing(client: Api, mount: str, issuer_name: str) -> dict[str, Any] | None:
    """Return the result for an already existing issuer."""
    issuer_id = find_issuer(client, mount, issuer_name)
    if issuer_id is None:
        return None
    issuer = client.get(f"{mount}/issuer/{issuer_id}") or {}
    return action_result(
        False,
        f"Issuer {issuer_name} exists in {mount}",
        issuer_id=issuer_id,
        certificate=issuer.get("certificate"),
        csr=None,
    )


def _generate_root(client: Api, mount: str, params: dict[str, Any]) -> dict[str, Any]:
    """Generate a root issuer."""
    body = {**_body(params, GENERATE_FIELDS), "issuer_name": params["issuer_name"]}
    data = _data(client.write(f"{mount}/issuers/generate/root/{params['mode']}", body))
    result = action_result(
        True,
        f"Generated root issuer {params['issuer_name']} in {mount}",
        issuer_id=data.get("issuer_id"),
        certificate=data.get("certificate"),
        csr=None,
    )
    if params["mode"] == "exported":
        result["private_key"] = data.get("private_key")
    return result


def _sign(client: Api, params: dict[str, Any], csr: str) -> str:
    """Sign the CSR with the issuer of another mount and return the chain."""
    signing_mount = str(params["signing_mount"]).strip("/")
    body = {**_body(params, SIGN_FIELDS), "csr": csr}
    if params.get("signing_ttl") is not None:
        body["ttl"] = params["signing_ttl"]
    path = f"{signing_mount}/issuer/{params['signing_issuer']}/sign-intermediate"
    data = _data(client.write(path, body))
    chain = [str(item) for item in (data.get("ca_chain") or []) if item]
    return "\n".join([str(data.get("certificate") or ""), *chain])


def _set_signed(
    client: Api, mount: str, params: dict[str, Any], key_id: str, certificate: str
) -> str:
    """Import the signed certificate and name the issuer using the generated key."""
    data = _data(
        client.write(f"{mount}/intermediate/set-signed", {"certificate": certificate})
    )
    mapping = data.get("mapping") or {}
    matches = [issuer for issuer, key in mapping.items() if key == key_id]
    imported = matches or [str(item) for item in (data.get("imported_issuers") or [])]
    if not imported:
        raise ValueError(f"set-signed in {mount} did not import an issuer for the key")
    issuer_id = str(imported[0])
    client.patch(f"{mount}/issuer/{issuer_id}", {"issuer_name": params["issuer_name"]})
    return issuer_id


def _generate_intermediate(
    client: Api, mount: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Generate an intermediate CSR and import its signed certificate when available."""
    mode = str(params["mode"])
    body = _body(params, GENERATE_FIELDS)
    key_name = params.get("key_name")
    key_id = find_key(client, mount, str(key_name)) if key_name else None
    if key_id is not None and mode != "exported":
        mode = "existing"
        body["key_ref"] = key_id
    data = _data(client.write(f"{mount}/issuers/generate/intermediate/{mode}", body))
    csr = str(data.get("csr") or "")
    key_id = str(data.get("key_id") or key_id or "")
    certificate = params.get("certificate")
    if certificate is None and params.get("signing_mount"):
        certificate = _sign(client, params, csr)
    result = action_result(True, "", issuer_id=None, certificate=None, csr=csr)
    if mode == "exported":
        result["private_key"] = data.get("private_key")
    if certificate is None:
        result["msg"] = (
            f"Generated intermediate CSR for {params['issuer_name']} in {mount}"
        )
        return result
    result["issuer_id"] = _set_signed(client, mount, params, key_id, str(certificate))
    result["certificate"] = str(certificate).split("\n-----BEGIN", 1)[0].strip() + "\n"
    result["msg"] = f"Imported signed intermediate {params['issuer_name']} into {mount}"
    return result


def run_ca(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Create a root or intermediate issuer unless its name already exists."""
    mount = str(params["mount"]).strip("/")
    issuer_name = str(params["issuer_name"])
    existing = _existing(client, mount, issuer_name)
    if existing is not None:
        return existing
    if check_mode:
        message = f"Would create {params['type']} issuer {issuer_name} in {mount}"
        return action_result(True, message, issuer_id=None, certificate=None, csr=None)
    if params["type"] == "root":
        return _generate_root(client, mount, params)
    return _generate_intermediate(client, mount, params)


def run_crl_rotate(
    params: dict[str, Any], check_mode: bool, client: Api
) -> dict[str, Any]:
    """Rotate the CRL or the delta CRL."""
    mount = str(params["mount"]).strip("/")
    action = "rotate-delta" if params.get("delta") else "rotate"
    if check_mode:
        return action_result(True, f"Would run crl/{action} in {mount}", success=None)
    data = client.get(f"{mount}/crl/{action}") or {}
    return action_result(
        True, f"Ran crl/{action} in {mount}", success=data.get("success")
    )


def run_eab(params: dict[str, Any], check_mode: bool, client: Api) -> dict[str, Any]:
    """Create an external account binding key for an ACME client."""
    mount = str(params["mount"]).strip("/")
    path = mount
    if params.get("issuer"):
        path = f"{path}/issuer/{params['issuer']}"
    if params.get("role"):
        path = f"{path}/roles/{params['role']}"
    path = f"{path}/acme/new-eab"
    if check_mode:
        return action_result(
            True, f"Would create an EAB key at {path}", id=None, key=None
        )
    data = _data(client.write(path))
    return action_result(
        True,
        f"Created EAB key {data.get('id')} at {path}",
        id=data.get("id"),
        key=data.get("key"),
        key_type=data.get("key_type"),
        acme_directory=data.get("acme_directory"),
    )
