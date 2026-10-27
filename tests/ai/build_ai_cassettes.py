# tests/ai/build_ai_cassettes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Write the AI providers' synthetic cassettes under tests/ai/cassettes/.

Run ``uv run --no-sync python tests/ai/build_ai_cassettes.py`` after a change to
the prompt, a provider's request or the narrated model's card; the drift test
(test_ai_cassettes.py) names this command when the files are out of date. The
answers are synthetic in each API's shape: no live answer is ever recorded.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai_support import CASSETTES, build_cassette

from pyeconomics.ai.providers import PROVIDERS


def main() -> None:
    """Write one cassette per provider."""
    for provider in sorted(PROVIDERS):
        path = CASSETTES / provider / "narrate.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(build_cassette(provider).document())


if __name__ == "__main__":
    main()
