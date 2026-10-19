# src/pyeconomics/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics: open economics and finance models.

The version is read from the installed distribution's metadata, so
``pyproject.toml`` is its only source. :mod:`pyeconomics.registry` finds the
registered models; importing the package discovers none of them. :func:`run` and
:func:`run_batch` run a registered model and return a result with its manifest.
:func:`bind` resolves a model's data bindings through the data layer, which it
imports on first use, so ``import pyeconomics`` loads no data module;
``run(model_id, bound)`` then records every series, vintage and retrieval time in
the manifest.

Examples
--------
>>> import pyeconomics
>>> isinstance(pyeconomics.__version__, str)
True
>>> pyeconomics.__version__
'1.0.0...'

"""

from importlib.metadata import version

__version__: str = version("pyeconomics")

from typing import TYPE_CHECKING

from pyeconomics import registry
from pyeconomics.core.runner import run, run_batch

if TYPE_CHECKING:
    from pyeconomics.data.bindings import bind

__all__ = ["__version__", "bind", "registry", "run", "run_batch"]


def __getattr__(name: str) -> object:
    """Import ``bind`` from the data layer when it is first asked for."""
    if name == "bind":
        from pyeconomics.data.bindings import bind as function  # noqa: PLC0415

        return function
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
