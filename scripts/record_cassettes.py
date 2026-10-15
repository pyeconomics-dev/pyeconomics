# scripts/record_cassettes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Record a provider's cassettes live: a deliberate, local act (the Recording rule).

Usage, from the repository root, with the maintainer's keys in the key chain::

    uv run --no-config python scripts/record_cassettes.py <provider> [<case> ...]
    uv run --no-config python scripts/record_cassettes.py <provider> --list

Each *case* a provider declares (``DataProvider.cases``) is run live through the
real transport, and what the provider saw is written, scrubbed, to
``tests/providers/cassettes/<provider>/<case>.json`` as canonical JSON and one
line feed:

- every registered secret, credential parameter, credential header and cookie is
  removed (:meth:`~pyeconomics.data.transport.cassette.Cassette.from_exchanges`);
- a case asks for at most 24 observations per series, and a file holds at most
  32 KiB;
- a source that is not hosted-safe, or whose terms forbid storage, is recorded
  through the provider's ``synthesize()`` hook, which replaces every observed
  value, and the cassette is marked ``"synthetic": true``;
- a case that expects an error (``Case.expect``) must raise exactly it, and one
  that does not must not; a case with ``invalid_key`` sends a random made-up key,
  to record a 401 or a 403;
- the scan every cassette must pass (``scan_text``) runs before anything is
  written, and a hit names the pattern, never the value.

It is a script, never a test: it refuses to run under pytest, and the tests only
ever read what it wrote. It prints no key and no URL.

Exit status: 0 when every case was recorded, 1 when a case failed, 2 when the
script refuses to run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import secrets
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pyeconomics.data import (
    DataError,
    DataProvider,
    LicenceClass,
    Query,
    cache,
    registry,
)
from pyeconomics.data.transport import default_transport
from pyeconomics.data.transport.cassette import (
    MAX_CASSETTE_BYTES,
    MAX_OBSERVATIONS,
    Cassette,
    scan_text,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import Case, ProviderInfo
    from pyeconomics.data.transport.base import Request, Response, Transport

__all__ = ["CASSETTES", "RecordingTransport", "main", "needs_synthetic", "record_case"]

CASSETTES: Final = (
    Path(__file__).resolve().parents[1] / "tests" / "providers" / "cassettes"
)


class RecordingError(Exception):
    """A case could not be recorded; the message says why and holds no secret."""


class RecordingTransport:
    """Wraps a transport and keeps every request and the response it got."""

    def __init__(self, inner: Transport) -> None:
        self.inner = inner
        self.exchanges: list[tuple[Request, Response]] = []

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Send through the wrapped transport and remember the exchange."""
        response = self.inner.send(info, request, key=key)
        self.exchanges.append((request, response))
        return response


def needs_synthetic(provider: type[DataProvider]) -> bool:
    """Whether the Recording rule makes a provider's cassettes synthetic.

    That is a source not classed hosted-safe, or one whose terms forbid storage.
    """
    terms = provider.info.terms
    return (
        terms.licence is not LicenceClass.HOSTED_SAFE
        or terms.cache.value == "forbidden"
    )


def _check_case(case: Case) -> None:
    if (
        isinstance(case.argument, Query)
        and case.argument.max_observations > MAX_OBSERVATIONS
    ):
        msg = (
            f"{case.name} asks for {case.argument.max_observations} observations; "
            f"a cassette keeps at most {MAX_OBSERVATIONS} per series"
        )
        raise RecordingError(msg)


def _synthesize(
    provider: DataProvider, exchanges: Sequence[tuple[Request, Response]], case: Case
) -> list[tuple[Request, Response]]:
    """Replace the observed values of every successful response."""
    out: list[tuple[Request, Response]] = []
    for position, (request, original) in enumerate(exchanges):
        response = original
        if original.ok:
            seed = request.series or f"{case.name}-{position}"
            try:
                response = provider.synthesize(request, original, seed=seed)
            except NotImplementedError:
                msg = (
                    f"{provider.info.id} is not hosted-safe or forbids storage, so its "
                    "cassettes are synthetic: implement synthesize()"
                )
                raise RecordingError(msg) from None
        out.append((request, response))
    return out


def record_case(
    provider: DataProvider,
    case: Case,
    transport: Transport,
    now: dt.datetime,
) -> Cassette:
    """Run one case through ``transport`` and return its scrubbed cassette.

    Raises
    ------
    RecordingError
        If the case asks for too much, fails (or fails to fail) as declared,
        needs a ``synthesize`` hook the provider lacks, or the result is too big
        or fails the secret scan. Nothing is written.
    """
    _check_case(case)
    recorder = RecordingTransport(transport)
    key = secrets.token_hex(16) if case.invalid_key else None
    try:
        with cache.bypass():  # a recording must reach the source, not the cache
            provider.run_case(case, key=key, transport=recorder)
    except DataError as error:
        if case.expect is None or not isinstance(error, case.expect):
            msg = f"{case.name} raised {type(error).__name__}: {error}"
            raise RecordingError(msg) from None
    else:
        if case.expect is not None:
            msg = f"{case.name} should have raised {case.expect.__name__} and did not"
            raise RecordingError(msg)
    if not recorder.exchanges:
        msg = f"{case.name} sent no request"
        raise RecordingError(msg)
    synthetic = needs_synthetic(type(provider))
    exchanges = (
        _synthesize(provider, recorder.exchanges, case)
        if synthetic
        else recorder.exchanges
    )
    cassette = Cassette.from_exchanges(
        provider.info.id,
        now.replace(microsecond=0),
        exchanges,
        synthetic=synthetic,
    )
    document = cassette.document()
    if len(document) > MAX_CASSETTE_BYTES:
        msg = (
            f"{case.name} is {len(document)} bytes; a cassette holds at most "
            f"{MAX_CASSETTE_BYTES}"
        )
        raise RecordingError(msg)
    found = scan_text(document.decode("utf-8", "replace"))
    if found:
        msg = (
            f"{case.name} matches the {', '.join(found)} pattern(s); it was not written"
        )
        raise RecordingError(msg)
    return cassette


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("provider", help="a registered provider id")
    parser.add_argument("cases", nargs="*", help="case names; all of them by default")
    parser.add_argument("--list", action="store_true", help="list the provider's cases")
    parser.add_argument(
        "--directory",
        type=Path,
        default=CASSETTES,
        help="where cassettes are written (default: tests/providers/cassettes)",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None, *, transport: Transport | None = None
) -> int:
    """Record the named cases (all by default); return the exit status.

    ``transport`` replaces the real HTTPS transport, for the script's own tests.
    """
    args = _parse(argv)
    if "pytest" in sys.modules and transport is None and not args.list:
        sys.stderr.write(
            "record: recording is a deliberate local act, never part of a test run\n"
        )
        return 2
    try:
        provider = registry.get(args.provider)
    except DataError as error:
        sys.stderr.write(f"record: {error}\n")
        return 2
    cases = {case.name: case for case in provider.cases}
    if args.list:
        for case in provider.cases:
            outcome = case.expect.__name__ if case.expect else "ok"
            sys.stdout.write(f"{case.name}\t{case.operation.value}\t{outcome}\n")
        return 0
    unknown = sorted(set(args.cases) - set(cases))
    if unknown:
        sys.stderr.write(f"record: {args.provider} has no case {', '.join(unknown)}\n")
        return 2
    chosen = (
        [cases[name] for name in args.cases] if args.cases else list(provider.cases)
    )
    active = transport if transport is not None else default_transport()
    failed = 0
    for case in chosen:
        try:
            cassette = record_case(provider, case, active, dt.datetime.now(dt.UTC))
        except RecordingError as error:
            sys.stderr.write(f"record: {error}\n")
            failed += 1
            continue
        path = args.directory / args.provider / f"{case.name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(cassette.document())
        label = "synthetic" if cassette.synthetic else "real"
        sys.stdout.write(
            f"recorded {case.name} ({len(cassette.requests)} request(s), "
            f"{path.stat().st_size} bytes, {label})\n"
        )
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
