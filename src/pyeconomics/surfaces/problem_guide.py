# src/pyeconomics/surfaces/problem_guide.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What each problem type means and what to do about it (ADR-0013 decision 1).

Every problem's ``type`` is ``https://pyeconomics.dev/problems/<slug>``, and the
site answers each of those addresses with a page generated from
:data:`~pyeconomics.surfaces.problems.ROWS` and this guide. :data:`GUIDES` holds
one :class:`Guide` per slug of the table, in its order; a test holds the two
equal, so a new row without its guide fails. A guide is fixed text for a reader:
it names no key, host, path or value, as a problem's detail never does.

:data:`EXIT_CODES` names what each command-line exit code means, for the problem
pages and the documentation's problem types page.

Examples
--------
>>> GUIDES["invalid-input"].local
False
>>> GUIDES["budget-exceeded"].local
True
>>> EXIT_CODES[3]
'invalid input'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = ["EXIT_CODES", "GUIDES", "Guide"]


@dataclass(frozen=True, slots=True)
class Guide:
    """What a problem means, what to do, and whether local mode is the answer."""

    meaning: str
    action: str
    local: bool = False
    """The problem points to local mode, whose command the page gives
    (:func:`~pyeconomics.surfaces.budgets.local_command`)."""


#: What each command-line exit code means.
EXIT_CODES: Final = {
    0: "success",
    1: "internal error",
    2: "usage",
    3: "invalid input",
    4: "no defined result",
    5: "not found",
    6: "not permitted (a licence refusal)",
    7: "data unavailable",
    8: "missing extra",
}

_RETRY: Final = "Try again later; if it persists, report it as an issue on GitHub."
_REPORT: Final = (
    "Report it as an issue on GitHub with the model id and the inputs, if you "
    "can share them; the problem holds no key, path or host to remove."
)

#: One guide per slug of the error table, in its order.
GUIDES: Final = {
    "invalid-input": Guide(
        "An input failed validation: a wrong type, a value outside its bounds, a "
        "missing field or a number that is not finite. The problem's errors list "
        "each field at fault, without its value.",
        "Correct the fields the errors name. Each model's page lists its inputs "
        "with their units and bounds; rates are decimals (0.05, not 5).",
    ),
    "input-too-large": Guide(
        "The inputs are larger than the surface decodes: the hosted service "
        "takes a smaller body than a local run.",
        "Send fewer values, or run the model on your own machine, where the limit "
        "is larger, with the inputs in a JSON file.",
        local=True,
    ),
    "no-defined-result": Guide(
        "The inputs are valid, but the model's result as a whole is undefined "
        "for them: a growth rate at or above the required return, say, or a "
        "singular covariance matrix. Where only one output is undefined, the "
        "model returns null for it with a warning instead.",
        "Check the inputs against the model's assumptions and limitations; the "
        "detail says which condition failed.",
    ),
    "no-convergence": Guide(
        "A numerical method, a root search or an optimizer, found no answer "
        "within its limits for these inputs.",
        "Check that a solution exists for the inputs (a yield for a price, say), "
        "or move the inputs nearer to typical values.",
    ),
    "model-not-found": Guide(
        "No registered model, or alias, has the id asked for.",
        "Check the id, which is the domain and the name joined by a dot "
        "(fixed_income.duration). The detail suggests close matches, and the "
        "models index lists every id.",
    ),
    "provider-not-found": Guide(
        "No installed data provider has the id asked for.",
        "Check the provider id; the detail suggests close matches. A provider "
        "that needs an extra appears once the extra is installed.",
    ),
    "concept-not-found": Guide(
        "The data catalog has no concept with the id asked for.",
        "Check the concept id; the detail suggests close matches, and the "
        "catalog lists every concept.",
    ),
    "series-not-found": Guide(
        "The source has no series, or table, with the id asked for.",
        "Check the series id at the source; a catalog concept names the series "
        "each source holds for it.",
    ),
    "llm-use-forbidden": Guide(
        "The terms of every source that could answer do not let their data "
        "reach a language model, and the request was made for one (through the "
        "MCP server or the AI narrative).",
        "Run the model or fetch the data directly, outside the assistant, or "
        "choose a concept that a source with permissive terms serves.",
    ),
    "licence-refused": Guide(
        "The source's licence class does not permit this use. The hosted "
        "service serves only data whose terms allow it; the problem names the "
        "source and its terms page.",
        "Run pyeconomics on your own machine, where library-only sources are "
        "read under your own access and your own key, or choose a hosted-safe "
        "source.",
    ),
    "narrative-disabled": Guide(
        "The optional AI narrative is off, as it is by default.",
        "Turn it on with ai_enabled = true in pyeconomics.toml, or "
        "PYECONOMICS_AI_ENABLED=1, and set the AI provider's key.",
    ),
    "narrative-not-hosted": Guide(
        "The hosted service never writes an AI narrative.",
        "Run pyeconomics on your own machine with your own AI provider's key.",
    ),
    "credential-unavailable": Guide(
        "A key the source needs is missing, invalid or refused. The detail names "
        "where the key may be set, never the key.",
        "Set the source's key with pyeconomics keys set, or in its environment "
        "variable, and check it has not expired.",
    ),
    "upstream-unavailable": Guide(
        "A request to the data source failed: a timeout, a refused connection or "
        "a server error at the source.",
        _RETRY,
    ),
    "upstream-invalid-response": Guide(
        "The data source answered with something that could not be read, or "
        "that did not match the request.",
        "Try again later. A source that keeps answering this way may have "
        "changed its format: report it as an issue on GitHub.",
    ),
    "upstream-rate-limited": Guide(
        "The data source's rate limit still held after the permitted retries.",
        "Wait before asking again; a cached copy serves repeated requests "
        "where the source's terms allow storage.",
    ),
    "offline-cache-miss": Guide(
        "Offline mode serves only the cache, and the cache has no copy of the "
        "data asked for.",
        "Turn offline mode off and fetch the data once, or ask for data the cache "
        "already holds.",
    ),
    "source-disabled": Guide(
        "The disabled_providers setting turns the source off, so it is refused "
        "before any request. A concept fails over to its next source; this "
        "problem means no source was left.",
        "Remove the source from disabled_providers (or "
        "PYECONOMICS_DISABLED_PROVIDERS), or choose a concept another source "
        "serves.",
    ),
    "data-unavailable": Guide(
        "The data cannot answer this request: too few observations for a "
        "window, no observation on or before the date, or a vintage the source "
        "does not keep.",
        "Choose another date, a shorter window or another concept; the detail "
        "names what was missing.",
    ),
    "missing-extra": Guide(
        "An optional package the feature needs is not installed.",
        "Install the extra the detail names, such as pip install "
        "'pyeconomics[econometrics]'.",
    ),
    "budget-exceeded": Guide(
        "A hosted run took longer than its model's time budget and was stopped.",
        "Run the model on your own machine, where no budget applies, with the "
        "inputs in a JSON file.",
        local=True,
    ),
    "route-not-found": Guide(
        "No route of the API matches the request.",
        "Check the path against the API's OpenAPI document, at /openapi.json.",
    ),
    "method-not-allowed": Guide(
        "The route exists but does not take the request's method.",
        "Use a method the route takes; the Allow header lists them.",
    ),
    "host-not-allowed": Guide(
        "A local server answers only requests addressed to a loopback name, so "
        "a web page that points its own domain at 127.0.0.1 cannot read its "
        "answers.",
        "Address the server as 127.0.0.1 or localhost, or start it with "
        "--allow-remote if you mean to serve other machines.",
    ),
    "server-busy": Guide(
        "Every worker is busy and the queue of waiting requests is full.",
        "Try again shortly.",
    ),
    "edge-required": Guide(
        "The hosted server answers only requests its edge forwarded, and this "
        "one did not come through it.",
        "Call the API at https://pyeconomics.dev, not the server behind it.",
    ),
    "too-many-requests": Guide(
        "The client reached one of the hosted service's rate limits.",
        "Wait for the number of seconds the Retry-After header gives, or run "
        "pyeconomics on your own machine, where no limit applies.",
    ),
    "limits-unavailable": Guide(
        "The service cannot check its rate limits just now, so it refuses the "
        "costly requests they protect.",
        _RETRY,
    ),
    "registry-error": Guide(
        "The model registry is inconsistent: a duplicate or reused id, say, "
        "usually from an installed plugin.",
        "Run registry.validate() to list each problem by model and rule, then "
        "fix or remove the plugin it names.",
    ),
    "invalid-configuration": Guide(
        "A setting is invalid, or a configuration file holds a secret, which "
        "pyeconomics refuses to read.",
        "Correct the setting the detail names; keep keys in the keyring or the "
        "environment, never in pyeconomics.toml.",
    ),
    "pyeconomics-error": Guide(
        "pyeconomics stopped the request on purpose, for a reason no more "
        "specific problem type names.",
        _REPORT,
    ),
    "internal-error": Guide(
        "An unexpected error stopped the request. Its detail is fixed text, so "
        "it reveals nothing about the inputs or the server.",
        _REPORT,
    ),
}
