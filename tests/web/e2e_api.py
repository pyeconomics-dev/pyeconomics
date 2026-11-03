# tests/web/e2e_api.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The API the web app's Playwright tests run the calculators against (Step 6).

The site calls the API on its own origin, and ``wrangler dev``'s edge Worker has
no origin, so the end-to-end tests (``web/tests/e2e/``) forward the page's
``/v1/`` requests here. This is the REST app in hosted mode, as staging runs
it, in one process (an inline pool), with every provider replaced by the
catalog world's stand-ins (``tests/data/catalog/catalog_world.py``): each has
the real provider's metadata (licence class, attribution, notice, terms page)
and answers synthetic data, so a bound model's live data, its sources panel and
the attribution block of its CSV download are exercised with no network, no key
and no recorded response.

The process is isolated as the ``isolated`` fixture isolates a test: a
configuration and cache directory of its own, deleted on exit, which the
stand-ins require before they answer, so nothing synthetic reaches a user's
cache; no ``*_API_KEY`` or ``PYECONOMICS_*`` variable from the environment; a
keyring that holds nothing; and a random placeholder key for each keyed source,
which the stand-ins never send anywhere. It listens on 127.0.0.1 only.

With ``--local`` it is instead the app ``pyeconomics serve`` builds (Phase 5 Step
10): local mode, with the packaged web app at ``/`` (``pyeconomics_app``'s site,
which ``scripts/web/package_site.py`` fills) behind the API's routes and the
loopback guard, over the same stand-ins, so ``web/playwright.local.config.ts``
drives the site's local mode (live data from library-only sources, the whole
catalog) with no network and no key.

    uv run --locked --all-extras python -I tests/web/e2e_api.py --port 8799
    uv run --locked --all-extras python -I tests/web/e2e_api.py --local --port 8798
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi import FastAPI

TESTS: Final = Path(__file__).resolve().parents[1]
#: Where the catalog world and the helpers it imports live.
WORLD_PATHS: Final = (TESTS / "data" / "catalog", TESTS / "data", TESTS)
LOCALHOST: Final = "127.0.0.1"


def isolate(home: Path) -> None:
    """Give this process its own directories and no credentials of the user's."""
    for name in list(os.environ):
        if name.endswith("_API_KEY") or name.startswith("PYECONOMICS_"):
            del os.environ[name]
    os.environ["PYECONOMICS_CACHE_DIR"] = str(home / "cache")
    os.environ["PYECONOMICS_CONFIG_DIR"] = str(home / "config")
    import keyring  # noqa: PLC0415
    from keyring.backends import fail  # noqa: PLC0415

    keyring.set_keyring(fail.Keyring())  # type: ignore[no-untyped-call]


def install_world() -> None:
    """Make the catalog world's stand-ins the installed providers."""
    sys.path[:0] = [str(path) for path in WORLD_PATHS]
    import catalog_world  # noqa: PLC0415

    from pyeconomics.data import registry  # noqa: PLC0415

    world = catalog_world.world_registry()
    registry._CACHE.registry = world  # noqa: SLF001 - the stand-ins, as stub_world does
    for info in world.infos():
        if info.key_variable is not None:
            os.environ[info.key_variable] = secrets.token_hex(16)


def build_app(*, local: bool = False) -> FastAPI:
    """The REST app, inline, with no rate limits for the tests' bursts.

    Hosted mode by default; with ``local``, local mode serving the packaged site,
    as ``pyeconomics serve`` does.
    """
    from pyeconomics.server import create_app, site  # noqa: PLC0415
    from pyeconomics.server.limits import RateLimits  # noqa: PLC0415
    from pyeconomics.server.settings import ServerSettings  # noqa: PLC0415

    if not local:
        settings = ServerSettings(workers=0, rate_limits=RateLimits.off())
        return create_app(mode="hosted", settings=settings)
    directory = site.packaged_site()
    if directory is None:
        msg = f"{site.missing_hint()} (python scripts/web/package_site.py)"
        raise SystemExit(msg)
    settings = ServerSettings(workers=0, rate_limits=RateLimits.off(), site=directory)
    return create_app(mode="local", settings=settings)


def main(argv: Sequence[str] | None = None) -> int:
    """Serve the API until stopped; return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument(
        "--local", action="store_true", help="local mode, with the packaged site"
    )
    arguments = parser.parse_args(argv)
    import uvicorn  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="pyeconomics-e2e-") as home:
        isolate(Path(home))
        install_world()
        uvicorn.run(
            build_app(local=arguments.local),
            host=LOCALHOST,
            port=arguments.port,
            log_level="warning",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
