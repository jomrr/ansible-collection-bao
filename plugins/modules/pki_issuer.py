# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao PKI issuers."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_issuer
short_description: Manage settings and default status of a PKI issuer
version_added: 0.1.0
description:
- Reconcile the settings of an issuer addressed by its name, including AIA and CDP URLs, and make it the default issuer.
- The issuer must exist; create it with M(jomrr.bao.pki_ca).
- With O(state=absent) the issuer is deleted; its key remains in the engine.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token, jomrr.bao.connection.state,
  jomrr.bao.options, jomrr.bao.options.pki_mount]
options:
  name:
    description: Issuer name.
    type: str
    required: true
    version_added: 0.1.0
  default:
    description: Make this issuer the default issuer of the engine.
    type: bool
    version_added: 0.1.0
  leaf_not_after_behavior:
    description: Behavior when a leaf would outlive the issuer.
    type: str
    choices: [err, truncate, permit]
    version_added: 0.1.0
  usage:
    description: Allowed usages of the issuer.
    type: list
    elements: str
    version_added: 0.1.0
  manual_chain:
    description: Explicit chain of issuer references.
    type: list
    elements: str
    version_added: 0.1.0
  revocation_signature_algorithm:
    description: Signature algorithm for CRLs.
    type: str
    version_added: 0.1.0
  issuing_certificates:
    description: Issuer specific AIA URLs.
    type: list
    elements: str
    version_added: 0.1.0
  crl_distribution_points:
    description: Issuer specific CRL distribution points.
    type: list
    elements: str
    version_added: 0.1.0
  delta_crl_distribution_points:
    description: Issuer specific delta CRL distribution points.
    type: list
    elements: str
    version_added: 0.1.0
  ocsp_servers:
    description: Issuer specific OCSP responders.
    type: list
    elements: str
    version_added: 0.1.0
  enable_aia_url_templating:
    description: Allow templates in the issuer specific URLs.
    type: bool
    version_added: 0.1.0
"""

EXAMPLES = r"""
- name: Publish the intermediate under its own URLs and make it the default
  jomrr.bao.pki_issuer:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    name: intermediate
    default: true
    issuing_certificates: [https://pki.example.test/aia/intermediate.der]
    crl_distribution_points: [https://pki.example.test/crl/intermediate.crl]
    usage: [read-only, issuing-certificates, crl-signing, ocsp-signing]
"""

RETURN = r"""
issuer_id:
  description: ID of the issuer.
  type: str
  returned: success
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _pki_issuer
from ansible_collections.jomrr.bao.plugins.module_utils._module import (
    run_module,
    state_spec,
)

# pylint: enable=wrong-import-position


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "default": {"type": "bool"},
            "leaf_not_after_behavior": {
                "type": "str",
                "choices": ["err", "truncate", "permit"],
            },
            "usage": {"type": "list", "elements": "str"},
            "manual_chain": {"type": "list", "elements": "str"},
            "revocation_signature_algorithm": {"type": "str"},
            "issuing_certificates": {"type": "list", "elements": "str"},
            "crl_distribution_points": {"type": "list", "elements": "str"},
            "delta_crl_distribution_points": {"type": "list", "elements": "str"},
            "ocsp_servers": {"type": "list", "elements": "str"},
            "enable_aia_url_templating": {"type": "bool"},
            **state_spec(),
        },
        _pki_issuer.run,
    )


if __name__ == "__main__":
    main()
