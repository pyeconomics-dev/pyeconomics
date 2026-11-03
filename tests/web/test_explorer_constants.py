# tests/web/test_explorer_constants.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data explorer's lists are the library's (Phase 5 Steps 9 to 11).

``web/src/lib/explorer.ts`` offers the transforms ``data.get`` takes
(``core.transforms.SERIES_TRANSFORMS``) and downloads in the formats the series
route answers (``server/formats.py SERIES_FORMATS``), its concept ids follow
the catalog's pattern, and the islands' modes are the ones ``GET /version``
answers (``server/settings.py MODES``). Each is read from the TypeScript source
and held equal here, so a change to one side fails until the other follows.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

import pytest

from pyeconomics.core.transforms import SERIES_TRANSFORMS, parse_series_transform

WEB: Final = Path(__file__).resolve().parents[2] / "web"
EXPLORER: Final = WEB / "src" / "lib" / "explorer.ts"


def _array(name: str) -> tuple[str, ...]:
    """Read a ``const NAME = [...] as const`` array of strings from explorer.ts."""
    source = EXPLORER.read_text(encoding="utf-8")
    match = re.search(rf"export const {name} = (\[[^\]]*\]) as const;", source)
    assert match is not None, f"explorer.ts has no {name}"
    return tuple(ast.literal_eval(match[1]))


def test_the_transforms_are_the_ones_data_get_takes() -> None:
    assert _array("SERIES_TRANSFORMS") == SERIES_TRANSFORMS
    texts = [
        n if n != "convert" else "convert(to=annual,method=mean)"
        for n in SERIES_TRANSFORMS
    ]
    names = tuple(parse_series_transform(text).name for text in texts)
    assert names == SERIES_TRANSFORMS


def test_the_formats_are_the_series_routes() -> None:
    pytest.importorskip("fastapi")
    from pyeconomics.server.formats import SERIES_FORMATS  # noqa: PLC0415

    assert _array("SERIES_FORMATS") == SERIES_FORMATS


def test_the_convert_methods_are_core_transforms() -> None:
    from pyeconomics.core.transforms import TRANSFORMS  # noqa: PLC0415

    methods = TRANSFORMS["convert"].parameter("method").choices
    assert _array("CONVERT_METHODS") == methods


def test_the_local_app_command_is_the_guides() -> None:
    # The site tells a reader to run the app; docs/how-to/local-app.md is the guide
    # that says how, so the two give one command (Phase 5 Step 11).
    source = EXPLORER.read_text(encoding="utf-8")
    match = re.search(r"export const LOCAL_APP = '([^']+)';", source)
    assert match is not None, "explorer.ts has no LOCAL_APP"
    install, serve = match[1].split(" then ")
    guide = WEB.parent / "docs" / "how-to" / "local-app.md"
    assert f"```text\n{install}\n{serve}\n```" in guide.read_text(encoding="utf-8")


def test_the_modes_are_the_servers() -> None:
    # GET /version's mode decides what the islands offer (Phase 5 Step 10): a
    # mode the server never answers would leave local mode dark.
    from pyeconomics.server.settings import MODES  # noqa: PLC0415

    sources = {
        "ServerMode": WEB / "src" / "lib" / "series-request.ts",
        "ExplorerMode": EXPLORER,
    }
    for name, path in sources.items():
        source = path.read_text(encoding="utf-8")
        match = re.search(rf"export type {name} = ([^;]+);", source)
        assert match is not None, f"{path.name} has no {name}"
        assert sorted(re.findall(r'"([a-z]+)"', match[1])) == sorted(MODES), name
