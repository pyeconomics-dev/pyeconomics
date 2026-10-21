# src/pyeconomics/models/asset_pricing/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Asset pricing: factor regressions and tests of factor models.

The launch catalog's asset-pricing entries, registered through the
``asset_pricing`` entry point in the ``pyeconomics.models`` group. Each binds the
Ken French factor and portfolio sets as library-only demonstration data; the
asset side is the user's own returns.
"""

from pyeconomics.models.asset_pricing.factor_model_tests import factor_model_tests
from pyeconomics.models.asset_pricing.factor_regression import factor_regression

__all__ = ["factor_model_tests", "factor_regression"]
