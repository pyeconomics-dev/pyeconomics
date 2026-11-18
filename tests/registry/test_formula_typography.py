# tests/registry/test_formula_typography.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A formula sets a word in a subscript or superscript upright (issue #350).

In mathematical typesetting a script that is a variable is italic (``t_j``) and
one that is a word or an abbreviation is upright (``D_{\\mathrm{Mac}}``). The
formulas wrote both alike, so "Mac" read as the product of three variables;
round 0 and round 1 of the site's dogfooding protocol each noted it. A formula
and a symbol now write a word as ``\\mathrm{...}`` (or ``\\text{...}``), and
this test fails on a script that holds a bare run of letters, unless the run is
a product of variables or a pair of indices listed in ``PRODUCTS``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest

from pyeconomics import registry

if TYPE_CHECKING:
    from pyeconomics.core import Model

#: Runs of letters a script may hold as they are: each is a product of
#: variables (``e^{-rT}``) or a pair of indices (``\sigma_{ij}``), never a word.
PRODUCTS = frozenset({"iT", "ij", "it", "mT", "qT", "rT"})

#: Text a formula has already set upright, and the commands' own names.
UPRIGHT = re.compile(r"\\(?:mathrm|text|mathbf|operatorname)\{[^{}]*\}")
COMMAND = re.compile(r"\\[A-Za-z]+")
RUN = re.compile(r"[A-Za-z]{2,}")

MODELS = registry.models()


def scripts(latex: str) -> list[str]:
    """Return the braced argument of every ``_`` and ``^`` in a formula."""
    found: list[str] = []
    for start, character in enumerate(latex[:-1]):
        if character not in "_^" or latex[start + 1] != "{":
            continue
        depth = 0
        for end in range(start + 1, len(latex)):
            depth += (latex[end] == "{") - (latex[end] == "}")
            if depth == 0:
                found.append(latex[start + 2 : end])
                break
    return found


def bare_words(latex: str) -> list[str]:
    """Return the runs of letters a formula's scripts leave in italic."""
    words: list[str] = []
    for script in scripts(latex):
        plain = COMMAND.sub(" ", UPRIGHT.sub(" ", script))
        words += [run for run in RUN.findall(plain) if run not in PRODUCTS]
    return words


def test_the_scan_reads_braced_scripts_and_skips_upright_text() -> None:
    assert scripts(r"D_{Mac} = e^{-rT} + x_t^{2}") == ["Mac", "-rT", "2"]
    assert scripts(r"k^{\frac{1}{1-\alpha}}") == [r"\frac{1}{1-\alpha}"]
    assert bare_words(r"D_{Mac} + V_{2,up}") == ["Mac", "up"]
    assert bare_words(r"D_{\mathrm{Mac}} + \sigma_{\text{annual},h}") == []
    assert bare_words(r"e^{-rT} \sigma_{ij} k^{\frac{1}{1-\alpha}} x_{t-1}") == []
    # A script nested in another is read with the outer one and on its own.
    assert bare_words(r"e^{x_{up}}") == ["up", "up"]


@pytest.mark.parametrize("model", MODELS, ids=[model.spec.id for model in MODELS])
def test_no_script_of_a_formula_holds_a_word_in_italic(
    model: Model[Any, Any],
) -> None:
    spec = model.spec
    texts = [*spec.formula, *(symbol.symbol for symbol in spec.symbols)]
    found = {text: bare_words(text) for text in texts if bare_words(text)}
    assert not found, (
        f"{spec.id}: write a word or an abbreviation in a subscript or a "
        r"superscript as \mathrm{...}; a product of variables or a pair of "
        f"indices joins PRODUCTS: {found}"
    )


def test_every_listed_product_is_still_written() -> None:
    written: set[str] = set()
    for model in MODELS:
        for text in model.spec.formula:
            for script in scripts(text):
                plain = COMMAND.sub(" ", UPRIGHT.sub(" ", script))
                written.update(RUN.findall(plain))
    assert written >= PRODUCTS, sorted(PRODUCTS - written)
