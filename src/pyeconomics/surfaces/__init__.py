# src/pyeconomics/surfaces/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The framework-free core every programmatic surface shares (ADR-0012).

The command line, the REST API, the MCP server and the exports are generated from
the registry on top of these modules, which import no framework:

- :mod:`~pyeconomics.surfaces.invoke`: :func:`invoke`, the one way a surface runs
  a model, and :class:`BindRequest`, a request to bind its data first;
- :mod:`~pyeconomics.surfaces.problems`: the error table, :func:`problem_for` and
  :class:`Problem` (an RFC 9457 problem with an exit code), and :func:`report`;
- :mod:`~pyeconomics.surfaces.codec`: input decoding with size and depth limits;
- :mod:`~pyeconomics.surfaces.envelope`: the canonical bytes, the entity tag and
  a text summary;
- :mod:`~pyeconomics.surfaces.budgets`: the hosted time budgets and size limits.

Importing this package loads no data module: the data layer arrives with the
first bind. The function :func:`invoke` hides the module of that name here;
import from the module by its path.

Examples
--------
>>> from pyeconomics.core import InputError
>>> from pyeconomics.surfaces import problem_for
>>> problem = problem_for(InputError("coupon_rate: 5 is above its bound 1"))
>>> problem.exit_code, problem.status, problem.type_uri
(3, 422, 'https://pyeconomics.dev/problems/invalid-input')
"""

from pyeconomics.surfaces.invoke import BindRequest, invoke
from pyeconomics.surfaces.problems import FieldError, Problem, problem_for, report

__all__ = ["BindRequest", "FieldError", "Problem", "invoke", "problem_for", "report"]
