# src/pyeconomics/models/econometrics/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Econometrics: ordinary least squares over statsmodels, the econometrics extra.

Each entry is registered through the ``econometrics`` entry point in the
``pyeconomics.models`` group. Importing this package does not import
statsmodels; a model imports it when it runs.
"""

from pyeconomics.models.econometrics.ols import ols

__all__ = ["ols"]
