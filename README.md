# Ansible Collection: jomrr.bao

![GitHub](https://img.shields.io/github/license/jomrr/ansible-collection-bao)
![GitHub last commit](https://img.shields.io/github/last-commit/jomrr/ansible-collection-bao)
![GitHub issues](https://img.shields.io/github/issues-raw/jomrr/ansible-collection-bao)
[![dev](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-collection-bao/dev.yml?branch=dev&label=dev)](https://github.com/jomrr/ansible-collection-bao/actions/workflows/dev.yml?query=branch%3Adev)
[![main](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-collection-bao/main.yml?branch=main&label=main)](https://github.com/jomrr/ansible-collection-bao/actions/workflows/main.yml?query=branch%3Amain)

Manage OpenBao through its HTTP API: policies, mounts, AppRole, userpass, KV v2,
PKI and SSH.

## Purpose

Manage an OpenBao server through its HTTP API with independent modules for ACL
policies, auth and secrets mounts, AppRole and userpass identities, KV version 2
secrets, PKI and SSH certificate authorities, plus a KV v2 lookup that reads
with an existing session token.

## Requirements

- ansible-core >=2.20.0
- Modules run where the task runs, typically delegated to localhost; they use
  Python 3.12 and Ansible's HTTP helpers and need no additional Python packages
  or system programs.
- The kv2 lookup runs on the controller and needs no additional Python packages.

## Installation

```console
ansible-galaxy collection install jomrr.bao
```

## Contents

### Modules

| Name | idempotent | check_mode | Description |
| ---- | ---------- | ---------- | ----------- |
| [`jomrr.bao.approle`](plugins/modules/approle.py) | yes | yes | Manage AppRoles |
| [`jomrr.bao.approle_secret_id`](plugins/modules/approle_secret_id.py) | yes | yes | Register or revoke a custom Secret ID |
| [`jomrr.bao.kv2_secret`](plugins/modules/kv2_secret.py) | yes | yes | Manage KV version 2 secret data |
| [`jomrr.bao.login`](plugins/modules/login.py) | no (action) | yes | Log in with an AppRole and return a session token |
| [`jomrr.bao.logout`](plugins/modules/logout.py) | no (action) | yes | Revoke the session token |
| [`jomrr.bao.mount`](plugins/modules/mount.py) | yes | yes | Manage auth and secrets mounts |
| [`jomrr.bao.pki_acme`](plugins/modules/pki_acme.py) | yes | yes | Manage the ACME configuration of a PKI engine |
| [`jomrr.bao.pki_acme_eab`](plugins/modules/pki_acme_eab.py) | no (action) | yes | Create an ACME external account binding key |
| [`jomrr.bao.pki_ca`](plugins/modules/pki_ca.py) | yes (issuer name) | yes | Generate a root or intermediate certificate authority |
| [`jomrr.bao.pki_config`](plugins/modules/pki_config.py) | yes | yes | Manage PKI URL, CRL and cluster configuration |
| [`jomrr.bao.pki_crl_rotate`](plugins/modules/pki_crl_rotate.py) | no (action) | yes | Rotate the certificate revocation list |
| [`jomrr.bao.pki_issuer`](plugins/modules/pki_issuer.py) | yes | yes | Manage settings and default status of a PKI issuer |
| [`jomrr.bao.pki_role`](plugins/modules/pki_role.py) | yes | yes | Manage PKI certificate roles |
| [`jomrr.bao.policy`](plugins/modules/policy.py) | yes | yes | Manage ACL policies |
| [`jomrr.bao.ssh_ca`](plugins/modules/ssh_ca.py) | yes (public key) | yes | Generate or import the SSH certificate authority key |
| [`jomrr.bao.ssh_role`](plugins/modules/ssh_role.py) | yes | yes | Manage SSH certificate roles |
| [`jomrr.bao.userpass_user`](plugins/modules/userpass_user.py) | yes | yes | Manage userpass users |

### Documentation Fragments

| Name | idempotent | check_mode | Description |
| ---- | ---------- | ---------- | ----------- |
| [`jomrr.bao.connection`](plugins/doc_fragments/connection.py) | n/a | n/a | Shared connection and mode documentation for the jomrr.bao modules. |
| [`jomrr.bao.options`](plugins/doc_fragments/options.py) | n/a | n/a | Shared option documentation for the jomrr.bao modules. |

### Lookup Plugins

| Name | idempotent | check_mode | Description |
| ---- | ---------- | ---------- | ----------- |
| [`jomrr.bao.kv2`](plugins/lookup/kv2.py) | n/a | n/a | Read KV version 2 secrets with an existing session token |

### Module Utilities

| Name | idempotent | check_mode | Description |
| ---- | ---------- | ---------- | ----------- |
| [`ansible_collections.jomrr.bao.plugins.module_utils.client`](plugins/module_utils/client.py) | n/a | n/a | HTTP client for the OpenBao API shared by modules and the kv2 lookup. |

## Session and Token

Every module takes `url`, `token`, `ca_file` and `timeout`. TLS verification is always
enabled; `ca_file` selects the trust anchor when the server certificate is not in the
system trust store. Obtain a session once per run with `jomrr.bao.login`, keep the token
in a fact with `no_log`, and revoke it at the end with `jomrr.bao.logout`:

```yaml
- name: Open an OpenBao session
  jomrr.bao.login:
    url: "{{ bao_url }}"
    ca_file: "{{ bao_ca_file }}"
    role_id: "{{ bao_role_id }}"
    secret_id: "{{ bao_secret_id }}"
  register: bao_login
  no_log: true
  check_mode: false
  changed_when: false

- name: Keep the session token
  ansible.builtin.set_fact:
    bao_token: "{{ bao_login.token }}"
  no_log: true
```

Set the connection options once through `module_defaults` for the collection's action
group `group/jomrr.bao.all` and pass only the resource options to each task. `login` is
not part of the group because it takes no token; give it `url` and `ca_file` directly.
Revoke the session in an `always` block with `jomrr.bao.logout`.

## Ordering

Enable mounts with `jomrr.bao.mount` before configuring their contents. Write ACL policies
before the identities that reference them. Create the PKI root with `jomrr.bao.pki_ca`
before intermediate authorities, and configure `jomrr.bao.pki_config` and `jomrr.bao.pki_issuer`
before issuing roles or enabling ACME. Generate the SSH signing key with `jomrr.bao.ssh_ca`
before creating SSH roles.

## Lookup

The `jomrr.bao.kv2` lookup reads KV version 2 secrets with an existing session token and
never logs in itself. Terms are secret paths below the mount; `mount` is required, `key`
selects one value and `version` a specific version. Without `key` the lookup returns the
data mapping. The connection comes from the variables `bao_url`, `bao_ca_file` and
`bao_token`, with `BAO_ADDR`, `BAO_CACERT` and `BAO_TOKEN` as environment fallback.

```yaml
db_password: "{{ lookup('jomrr.bao.kv2', 'app/database', mount='automation', key='password') }}"
```

A missing path or key fails with the mount and path in the message; secret content is
never included. The lookup keeps no cache and no state between calls.

## PKI Lifecycle

`jomrr.bao.pki_ca` is idempotent by issuer name. With `type: root` it generates a root
issuer. With `type: intermediate` it generates a CSR and either returns it in `csr` for
external signing, imports a signed `certificate` with `set-signed`, or signs the CSR with
the issuer named by `signing_mount` and `signing_issuer` in the same server. The imported
issuer receives the configured name. `jomrr.bao.pki_issuer` manages AIA and CDP URLs and the
default issuer, `jomrr.bao.pki_config` the `urls`, `crl` and `cluster` configuration,
`jomrr.bao.pki_role` certificate templates including extended key usage OIDs, other SANs
and policy identifiers, and `jomrr.bao.pki_acme` the ACME configuration. `jomrr.bao.pki_crl_rotate`
and `jomrr.bao.pki_acme_eab` are actions and always report a change.

## SSH CA

`jomrr.bao.ssh_ca` generates or imports the signing key of an SSH secrets engine and is
idempotent by the existing public key; an existing key with a different imported public
key is reported as an error instead of being replaced. `jomrr.bao.ssh_role` manages CA
roles for host and user certificates with `allowed_users`, `allowed_domains`, default and
allowed extensions, TTLs and `algorithm_signer`.

## Security

Tokens, Secret IDs, passwords, private keys and KV data are `no_log`
options and never appear in messages, diffs or return values. The KV diff lists keys and
the version only. Returned credentials from `login`, `approle_secret_id`, `pki_acme_eab`
and `pki_ca` with `type: exported` require `no_log: true` on the calling task.

## Check Mode

State modules read the current state in check mode and report the predicted
change and diff without writing. Action modules report the pending call without
contacting the server, so a check-mode run with `login` yields no token unless
that task sets `check_mode: false`.

## References

- [Collection documentation](https://github.com/jomrr/ansible-collection-bao)

## Author

- Jonas Mauer

## License

License: GPL-3.0-or-later.
See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jonas Mauer.
