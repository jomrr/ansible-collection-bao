# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OpenBao PKI engine configuration."""

from __future__ import annotations

DOCUMENTATION = r"""
module: pki_config
short_description: Manage PKI URL, CRL and cluster configuration
version_added: 0.1.0
description:
- Reconcile the C(config/urls), C(config/crl) and C(config/cluster) endpoints of a PKI secrets engine.
- Only the given sections and keys are compared and written.
extends_documentation_fragment: [jomrr.bao.connection, jomrr.bao.connection.token,
  jomrr.bao.connection.state, jomrr.bao.options.pki_mount]
options:
  urls:
    description: Authority information access and distribution point URLs used in issued certificates.
    type: dict
    version_added: 0.1.0
    suboptions:
      issuing_certificates:
        description: AIA URLs of the issuing certificate.
        type: list
        elements: str
      crl_distribution_points:
        description: CRL distribution point URLs.
        type: list
        elements: str
      delta_crl_distribution_points:
        description: Delta CRL distribution point URLs.
        type: list
        elements: str
      ocsp_servers:
        description: OCSP responder URLs.
        type: list
        elements: str
      enable_templating:
        description: Allow issuer and cluster templates in the URLs.
        type: bool
  crl:
    description: Certificate revocation list settings.
    type: dict
    version_added: 0.1.0
    suboptions:
      expiry:
        description: CRL lifetime as seconds or duration.
        type: str
      disable:
        description: Disable CRL generation.
        type: bool
      ocsp_disable:
        description: Disable the OCSP responder.
        type: bool
      ocsp_expiry:
        description: OCSP response lifetime as seconds or duration.
        type: str
      auto_rebuild:
        description: Rebuild the CRL before it expires.
        type: bool
      auto_rebuild_grace_period:
        description: Time before expiry at which the CRL is rebuilt, as seconds or duration.
        type: str
      enable_delta:
        description: Build delta CRLs between full rebuilds.
        type: bool
      delta_rebuild_interval:
        description: Interval between delta CRL builds as seconds or duration.
        type: str
  cluster:
    description: Cluster local paths used by ACME and templated URLs.
    type: dict
    version_added: 0.1.0
    suboptions:
      path:
        description: Base URL of this mount as reachable by clients.
        type: str
      aia_path:
        description: Base URL used in templated AIA and CRL URLs.
        type: str
"""

EXAMPLES = r"""
- name: Configure distribution URLs and CRL rebuilds
  jomrr.bao.pki_config:
    url: https://bao.example.test:8200
    token: "{{ bao_token }}"
    mount: pki-int
    urls:
      issuing_certificates: ["{{ '{{cluster_aia_path}}' }}/issuer/{{ '{{issuer_id}}' }}/der"]
      crl_distribution_points: ["{{ '{{cluster_aia_path}}' }}/issuer/{{ '{{issuer_id}}' }}/crl/der"]
      enable_templating: true
    crl:
      expiry: 72h
      auto_rebuild: true
      auto_rebuild_grace_period: 12h
    cluster:
      path: https://bao.example.test:8200/v1/pki-int
      aia_path: https://bao.example.test:8200/v1/pki-int
"""

RETURN = r"""
# The module returns only the standard fields; the diff is grouped by section.
"""

# Ansible requires DOCUMENTATION, EXAMPLES and RETURN before normal imports.
# pylint: disable=wrong-import-position
from ansible_collections.jomrr.bao.plugins.module_utils import _pki_config
from ansible_collections.jomrr.bao.plugins.module_utils._module import run_module

# pylint: enable=wrong-import-position

LIST = {"type": "list", "elements": "str"}
DURATION = {"type": "str"}
BOOL = {"type": "bool"}


def main() -> None:
    """Run the module."""
    run_module(
        {
            "mount": {"type": "str", "required": True},
            "urls": {
                "type": "dict",
                "options": {
                    "issuing_certificates": LIST,
                    "crl_distribution_points": LIST,
                    "delta_crl_distribution_points": LIST,
                    "ocsp_servers": LIST,
                    "enable_templating": BOOL,
                },
            },
            "crl": {
                "type": "dict",
                "options": {
                    "expiry": DURATION,
                    "disable": BOOL,
                    "ocsp_disable": BOOL,
                    "ocsp_expiry": DURATION,
                    "auto_rebuild": BOOL,
                    "auto_rebuild_grace_period": DURATION,
                    "enable_delta": BOOL,
                    "delta_rebuild_interval": DURATION,
                },
            },
            "cluster": {
                "type": "dict",
                "options": {"path": {"type": "str"}, "aia_path": {"type": "str"}},
            },
        },
        _pki_config.run_config,
        required_one_of=[("urls", "crl", "cluster")],
    )


if __name__ == "__main__":
    main()
