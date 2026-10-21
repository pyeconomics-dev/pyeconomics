# src/pyeconomics/models/econometrics/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Econometrics over statsmodels and arch, the econometrics extra.

Ordinary least squares, GARCH-family volatility, and time series (ARIMA and
SARIMA, VARs and cointegration tests). Each entry is registered through the
``econometrics`` entry point in the ``pyeconomics.models`` group. Importing this
package imports neither library; a model imports its own when it runs.
"""

from pyeconomics.models.econometrics.garch import garch
from pyeconomics.models.econometrics.ols import ols
from pyeconomics.models.econometrics.time_series import time_series

__all__ = ["garch", "ols", "time_series"]
