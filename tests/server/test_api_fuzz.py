# tests/server/test_api_fuzz.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Schemathesis against openapi.json, in local and hosted modes (Phase 4 Step 7).

ci.yml's ``api-fuzz`` job runs this module alone (``-m fuzz``) on Python 3.14
from the ``fuzz`` dependency group, which the Wheel rule keeps off CPython 3.15
(PyYAML has no wheel there; ``test_fuzz_gap.py`` asserts the gap). Elsewhere the
module is not collected (tests/conftest.py) or, with the group installed, is
deselected by the ``fuzz`` marker.

Each mode's app runs with two spawned workers held to the hosted budgets, the
rate limits off, its own configuration and cache directories, a random key for
every keyed source, and every data request answered 404 by a recording pool
behind the real transport (``server_support.install_fuzz_world``), so no request
leaves the machine and no legitimate upstream failure (a missing key, an outage)
can pass for a server error. Every operation then gets the
Schemathesis cases Hypothesis draws, derandomized, at most :data:`MAX_EXAMPLES`
each, checked for no server error and for conformance of the status code, the
content type and the response body to the document.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error
from schemathesis.python import asgi
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_schema_conformance,
    status_code_conformance,
)
from server_support import LOCAL, LOOPBACK_ONLY, install_fuzz_world

from pyeconomics.server import ServerSettings, create_app
from pyeconomics.server.limits import RateLimits
from pyeconomics.surfaces.budgets import HOSTED_BUDGETS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from schemathesis.generation.case import Case
    from schemathesis.specs.openapi.schemas import OpenApiSchema

pytestmark = [LOOPBACK_ONLY, pytest.mark.fuzz]

#: The checks the job holds the API to.
CHECKS = [
    not_a_server_error,
    status_code_conformance,
    content_type_conformance,
    response_schema_conformance,
]
#: The most cases Hypothesis draws for one operation.
MAX_EXAMPLES = 12


@pytest.fixture(scope="module", params=["local", "hosted"])
def api_schema(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[OpenApiSchema]:
    """Serve one mode's app in this process and load its document."""
    root = tmp_path_factory.mktemp(f"fuzz-{request.param}")
    with pytest.MonkeyPatch.context() as environment:
        # The workers are spawned while this module's first test is set up,
        # before the per-test isolation: give them an isolated environment.
        for name in list(os.environ):
            if name.startswith("PYECONOMICS_") or name.endswith("_API_KEY"):
                environment.delenv(name)
        environment.setenv("PYECONOMICS_CONFIG_DIR", str(root / "config"))
        environment.setenv("PYECONOMICS_CACHE_DIR", str(root / "cache"))
        app = create_app(
            mode=request.param,
            settings=ServerSettings(
                workers=2,
                worker_setup=install_fuzz_world,
                budgets=HOSTED_BUDGETS,
                rate_limits=RateLimits.off(),
            ),
        )
        # Addressed to 127.0.0.1, as a local server requires (a loopback Host).
        schema = schemathesis.openapi.from_asgi(
            "/openapi.json", app, headers={"Host": "127.0.0.1"}
        )
        try:
            yield schema
        finally:
            asgi.shutdown_lifespans()


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
@settings(
    max_examples=MAX_EXAMPLES,
    derandomize=True,
    deadline=None,
    database=None,
    suppress_health_check=list(HealthCheck),
)
def test_every_operation_honours_the_document(case: Case[Any]) -> None:
    case.call_and_validate(base_url=LOCAL, checks=CHECKS)
