# Copyright (c) 2026 Jonas Mauer
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Connection options, client construction and result handling; not a public API."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, cast

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.jomrr.bao.plugins.module_utils.client import (
    Api,
    BaoClient,
    BaoError,
)

if TYPE_CHECKING:
    from typing import NoReturn

Params = dict[str, Any]
Spec = dict[str, dict[str, Any]]
Run = Callable[[Params, bool, Api], dict[str, Any]]
MASK = "********"
# Names that look secret to ansible-test's validate-modules heuristic but are not.
SECRET_LOOKALIKE = re.compile(r"pass|pwd|secret|token|key")


def connection_argument_spec(token: bool = True) -> Spec:
    """Return the connection options shared by every module."""
    spec: Spec = {
        "url": {"type": "str", "required": True},
        "ca_file": {"type": "path"},
        "timeout": {"type": "int", "default": 30},
    }
    if token:
        spec["token"] = {"type": "str", "required": True, "no_log": True}
    return spec


def state_spec() -> Spec:
    """Return the state option shared by the state modules."""
    return {
        "state": {"type": "str", "choices": ["present", "absent"], "default": "present"}
    }


def named_spec(fields: Spec) -> Spec:
    """Return the spec of a named resource below a mount with a state option."""
    return {
        "mount": {"type": "str", "required": True},
        "name": {"type": "str", "required": True},
        **fields,
        **state_spec(),
    }


def token_spec() -> Spec:
    """Return the token options shared by the identity modules."""
    return {
        "token_policies": {"type": "list", "elements": "str"},
        "token_bound_cidrs": {"type": "list", "elements": "str"},
        "token_ttl": {"type": "str"},
        "token_max_ttl": {"type": "str"},
        "token_explicit_max_ttl": {"type": "str"},
        "token_num_uses": {"type": "int"},
        "token_period": {"type": "str"},
        "token_no_default_policy": {"type": "bool"},
        "token_type": {"type": "str", "choices": ["default", "service", "batch"]},
    }


def build_client(params: Params) -> Api:
    """Create the API client from the connection options."""
    return BaoClient(
        url=str(params["url"]),
        token=str(params.get("token") or ""),
        ca_file=params.get("ca_file"),
        timeout=int(params["timeout"]),
    )


def _leaves(value: object) -> Iterable[str]:
    """Yield the non-empty strings inside a nested value."""
    if isinstance(value, str):
        if value:
            yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _leaves(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _leaves(item)


def secret_values(params: Params, spec: Spec) -> list[str]:
    """Return the values of no_log options, longest first."""
    values: set[str] = set()
    for name, options in spec.items():
        if options.get("no_log"):
            values.update(_leaves(params.get(name)))
    return sorted(values, key=len, reverse=True)


def sanitize(message: str, secrets: Iterable[str]) -> str:
    """Mask secret values inside a message."""
    for secret in secrets:
        message = message.replace(secret, MASK)
    return message


def run_module(
    argument_spec: Spec, run: Run, *, token: bool = True, **module_kwargs: Any
) -> None:
    """Run a module operation and finish through exit_json or fail_json."""
    spec = {**connection_argument_spec(token), **argument_spec}
    for name, options in spec.items():
        if "no_log" not in options and SECRET_LOOKALIKE.search(name):
            options["no_log"] = False
    module = cast(Callable[..., AnsibleModule], AnsibleModule)(
        argument_spec=spec, supports_check_mode=True, **module_kwargs
    )
    params = cast(Params, module.params)
    secrets = secret_values(params, spec)
    fail_json = cast("Callable[..., NoReturn]", module.fail_json)
    exit_json = cast("Callable[..., NoReturn]", module.exit_json)
    try:
        result = run(params, bool(module.check_mode), build_client(params))
    except (BaoError, ValueError, TypeError) as exc:
        fail_json(msg=sanitize(str(exc), secrets))
    exit_json(**result)
