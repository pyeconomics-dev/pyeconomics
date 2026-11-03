# packages/pyeconomics-app/src/pyeconomics_app/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics-app: the built web app that ``pyeconomics serve`` serves.

The package holds the static site under ``site/`` and nothing else to run
(ADR-0013 decision 16); ``pyeconomics.server.site`` reads it through
:func:`site_path`. A checkout holds no ``site/`` until
``scripts/web/package_site.py`` copies a build there.
"""

from importlib.resources import files
from importlib.resources.abc import Traversable

__all__ = ["site_path"]


def site_path() -> Traversable:
    """Return the built site's directory inside the installed package."""
    return files(__name__) / "site"
