# tests/providers/test_live_alarm.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The live run's alarm proof: a live test that fails only when asked to.

``providers-live.yml``'s ``simulate_failure`` dispatch input sets
``PROVIDERS_LIVE_SIMULATE_FAILURE=1`` for the live suite, and this test then
fails, so the run fails and its report job opens a ``provider-live`` issue
(Step 20 proves the alarm this way). On any other run it passes and touches no
network.
"""

from __future__ import annotations

import os

import pytest

#: The variable the dispatch input sets.
SIMULATE: str = "PROVIDERS_LIVE_SIMULATE_FAILURE"


@pytest.mark.live
def test_live_the_alarm_fails_only_when_a_failure_is_simulated() -> None:
    assert os.environ.get(SIMULATE, "") != "1", (
        "a failure was simulated on purpose (providers-live's simulate_failure)"
    )
