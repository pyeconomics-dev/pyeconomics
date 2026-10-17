# src/pyeconomics/data/providers/base.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The provider contract: ``ProviderInfo``, ``Query`` and ``DataProvider`` (ADR-0011).

One source is one :class:`DataProvider` subclass with a :class:`ProviderInfo`
that describes it and a typed pipeline that fetches it:

.. code-block:: text

    Query -> build_requests -> exchange (a Transport) -> parse -> Series | Table

The same shape serves ``search``, ``describe`` and ``vintages``, each with a
``build_*`` and a ``parse_*`` hook. A provider overrides the hooks for the
capabilities it declares and nothing else:

- ``build_requests(query)`` says what to ask for: :class:`~.transport.base.Request`
  values on the provider's allowlisted hosts. Credentials are attached by the
  transport from :class:`Authentication`, never by provider code.
- ``parse(responses, query)`` turns the answers into a
  :class:`~pyeconomics.data.types.Series` or :class:`~pyeconomics.data.types.Table`
  with full metadata: units, frequency, seasonal adjustment, licence class,
  attribution and, where the source keeps vintages, real-time periods. A rate is
  a decimal (convert percent with ``percent_to_decimal`` here), a missing marker
  is ``None``, and a period-start source is converted to period ends.
- ``classify_error`` maps a source's own error body to the error taxonomy when the
  status code alone does not.
- ``exchange`` is the seam a non-HTTP source overrides: the default sends each
  request through the :class:`~.transport.base.Transport`, and follows
  ``next_page`` for a source that pages its answers.
- :attr:`DataProvider.sends_key` tells the build and parse hooks whether the
  transport will attach a key, so a source whose key is optional (BLS) can
  choose its keyed or keyless API.

The public methods (:meth:`DataProvider.fetch`, :meth:`~DataProvider.search`,
:meth:`~DataProvider.describe`, :meth:`~DataProvider.vintages`) are final: they
check the capability and the platform, refuse a source hosted mode may not serve
before any request, map the final status of each response to the error taxonomy
(401 and 403 to ``CredentialError``, 404 to ``SeriesNotFoundError``, 429 to
``RateLimitError``, 5xx to ``TransportError``, other failures to
``ResponseError``) and check what ``parse`` returned. A subclass that defines
one is refused when it is created.

``DataProvider`` is not :class:`pyeconomics.core.Provider`, which names the
distribution that registered a model.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data import CachePolicy, LicenceClass, LlmUse, Terms
>>> info = ProviderInfo(
...     id="demo",
...     name="Demo source",
...     homepage="https://example.org",
...     terms=Terms(
...         licence=LicenceClass.HOSTED_SAFE,
...         terms_url="https://example.org/terms",
...         checked=dt.date(2026, 10, 15),
...         attribution="Source: Demo source.",
...         llm_use=LlmUse.ALLOWED,
...         cache=CachePolicy.ALLOWED,
...     ),
...     hosts=("api.example.org",),
...     rate_limits=(RateLimit(requests=60, per="minute"),),
... )
>>> info.capabilities, info.auth.kind.value, info.key_variable
((<Capability.FETCH: 'fetch'>,), 'none', None)
>>> Query(series=("GDP",), start="2020-01-01").start
datetime.date(2020, 1, 1)

"""

from __future__ import annotations

import contextlib
import datetime as dt  # noqa: TC003 - pydantic resolves Query's date fields
import re
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Final,
    Literal,
    NoReturn,
    final,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from pyeconomics.core import _fields as f
from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import DATA_DATE_BOUNDS, VINTAGE_LABEL_PATTERN
from pyeconomics.data import cache, modes, redaction
from pyeconomics.data.cache.policy import DEFAULT_TTL_SECONDS, Fetched, Origin
from pyeconomics.data.config import GUIDE_URL
from pyeconomics.data.credentials import has_key, key_variable, withheld
from pyeconomics.data.errors import (
    CredentialError,
    DataError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    TransportError,
)
from pyeconomics.data.records import Records
from pyeconomics.data.transport import default_transport
from pyeconomics.data.transport.base import (
    DEFAULT_MAX_RESPONSE_BYTES,
    MAX_REQUESTS_PER_OPERATION,
    Request,
    Response,
    retry_after_seconds,
)
from pyeconomics.data.types import (
    MAX_OBSERVATIONS,
    ObservationFrequency,
    Series,
    SeriesMeta,
    Table,
)
from pyeconomics.data.vintage import Vintage

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping, Sequence

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.terms import Terms
    from pyeconomics.data.transport.base import Transport

__all__ = [
    "MAX_QUERY_SERIES",
    "MAX_SEARCH_RESULTS",
    "SERIES_ID_PATTERN",
    "Access",
    "AuthKind",
    "Authentication",
    "Capability",
    "Case",
    "DataProvider",
    "KeyPlacement",
    "KeySlot",
    "Platform",
    "ProviderInfo",
    "Query",
    "RateLimit",
    "SearchHit",
    "current_platform",
    "sends_key",
    "tail",
]

#: The most series ids one query names (the most columns a table holds).
MAX_QUERY_SERIES: Final = 1_000
#: The most hits a search returns.
MAX_SEARCH_RESULTS: Final = 100
#: A series id: printable, with no space or character that could alter a path.
SERIES_ID_PATTERN: Final = r"[A-Za-z0-9^][A-Za-z0-9._:+*=@/^,-]{0,127}"
_SERIES_ID: Final = re.compile(SERIES_ID_PATTERN)
_ANCHORED_SERIES_ID: Final = f"^{SERIES_ID_PATTERN}$"
_ANCHORED_VINTAGE: Final = f"^(?:{VINTAGE_LABEL_PATTERN.pattern})$"

#: The methods a subclass must not override: they hold the gates every operation
#: passes through, whatever calls it.
_FINAL_METHODS: Final = (
    "fetch",
    "fetch_with_origin",
    "records",
    "search",
    "describe",
    "vintages",
    "run_case",
)
_SECONDS: Final = {"second": 1, "minute": 60, "day": 86_400}
#: The statuses a recorder may stand in for (``Case.simulate``): the failures no
#: well-behaved client provokes on purpose.
SIMULATED_STATUSES: Final = frozenset({429, 500, 502, 503, 504})
# Whether the operation running in this context sends a key (see sends_key).
_SENDS_KEY: ContextVar[bool | None] = ContextVar("sends_key", default=None)


class Capability(StrEnum):
    """What a provider can do beyond a fetch (ADR-0011 decision 9)."""

    FETCH = "fetch"
    """Turn a query into a series or a table."""
    SEARCH = "search"
    """Find series by text."""
    DESCRIBE = "describe"
    """Return a series' metadata without its observations."""
    VINTAGES = "vintages"
    """List the dates a series changed, and return real-time periods in a fetch."""
    RECORDS = "records"
    """Fetch typed identifier mappings or filings, separate from numeric frames."""
    BULK = "bulk"
    """One request returns a whole dataset or release as a table. Informational:
    the resolver prefers one bulk call to many single ones. Requires ``fetch``."""


class Platform(StrEnum):
    """An operating environment a provider can run in."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    PYODIDE = "pyodide"
    """The browser, through Pyodide."""


class Access(StrEnum):
    """How a provider reaches its source."""

    HTTPS = "https"
    """HTTPS requests to the provider's allowlisted hosts, sent by a transport."""
    SESSION = "session"
    """A local, non-HTTP session, such as a terminal's desktop API; the provider
    overrides :meth:`DataProvider.exchange` and declares no hosts."""


class AuthKind(StrEnum):
    """What a source asks of the caller."""

    NONE = "none"
    KEY = "key"
    """An API key from the key chain, sent as :class:`KeyPlacement` says."""
    CONTACT = "contact"
    """The user's configured contact (name and email), sent in the User-Agent."""


class KeyPlacement(StrEnum):
    """Where the transport puts a key."""

    QUERY = "query"
    BODY = "body"
    HEADER = "header"


@dataclass(frozen=True, slots=True)
class KeySlot:
    """Another place a request may ask for the key (``Request.key_placement``).

    A source whose API versions take the key differently declares one: FRED's
    v1 reads a query parameter, its v2 an ``Authorization`` header.
    """

    placement: KeyPlacement
    name: str
    scheme: str | None = None

    def __post_init__(self) -> None:
        """Turn the placement's value into a member; leave anything else."""
        object.__setattr__(self, "placement", _member(KeyPlacement, self.placement))


@dataclass(frozen=True, slots=True, kw_only=True)
class Authentication:
    """How a source is authenticated; the transport attaches it, never a provider.

    Examples
    --------
    >>> auth = Authentication.key("api_key", KeyPlacement.QUERY)
    >>> auth.kind.value, auth.placement.value, auth.name
    ('key', 'query', 'api_key')
    >>> Authentication.key(
    ...     "Authorization", KeyPlacement.HEADER, scheme="Bearer"
    ... ).scheme
    'Bearer'

    """

    kind: AuthKind = AuthKind.NONE
    placement: KeyPlacement | None = None
    """Where a key goes (``KEY`` only)."""
    name: str | None = None
    """The query parameter, body field or header that carries the key."""
    scheme: str | None = None
    """A header value's prefix, such as ``Bearer``."""
    required: bool = True
    """Whether a fetch fails without a key; ``False`` for a key that only raises
    limits (OpenFIGI, BLS), which is sent when the chain has one."""
    alternates: tuple[KeySlot, ...] = ()
    """Other places a request may ask for the key, each a different placement:
    a request names one with ``Request.key_placement``."""

    @classmethod
    def key(
        cls,
        name: str,
        placement: KeyPlacement,
        *,
        scheme: str | None = None,
        required: bool = True,
        alternates: tuple[KeySlot, ...] = (),
    ) -> Authentication:
        """Describe a key sent as a query parameter, a body field or a header."""
        return cls(
            kind=AuthKind.KEY,
            placement=placement,
            name=name,
            scheme=scheme,
            required=required,
            alternates=alternates,
        )

    def slot(self, placement: str | None) -> KeySlot | None:
        """Return where a request that asks for ``placement`` gets the key.

        ``None`` asks for the default placement. A placement the source does not
        declare returns ``None``.
        """
        if not isinstance(self.placement, KeyPlacement) or self.name is None:
            return None
        default = KeySlot(self.placement, self.name, self.scheme)
        if placement is None or placement == default.placement.value:
            return default
        candidates: tuple[object, ...] = tuple(self.alternates)
        return next(
            (
                slot
                for slot in candidates
                if isinstance(slot, KeySlot) and slot.placement == placement
            ),
            None,
        )

    @classmethod
    def contact(cls) -> Authentication:
        """Describe a source that requires the user's contact in the User-Agent."""
        return cls(kind=AuthKind.CONTACT)

    def __post_init__(self) -> None:
        """Turn enum values into members; leave anything else for the auth rule."""
        object.__setattr__(self, "kind", _member(AuthKind, self.kind))
        if self.placement is not None:
            object.__setattr__(self, "placement", _member(KeyPlacement, self.placement))
        object.__setattr__(self, "alternates", _tuple(self.alternates))


@dataclass(frozen=True, slots=True, kw_only=True)
class RateLimit:
    """A published limit: this many requests per second, minute or day.

    ``without_key`` marks a limit that holds only for the requests sent without
    a key, such as BLS's 25 keyless queries a day.
    """

    requests: int
    per: Literal["second", "minute", "day"]
    without_key: bool = False

    @property
    def window_seconds(self) -> int:
        """The length of the window in seconds."""
        return _SECONDS[self.per]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderInfo:
    """What a provider is, on what terms, and how to reach it.

    A provider declares one, as the class attribute ``info``. Construction
    accepts what it is given; ``pyeconomics.data.registry.validate()`` checks
    every rule of the contract and reports each problem as
    ``<id>: [<rule>] <detail>``, so a toy with one flaw shows exactly that one.
    """

    id: str
    """The permanent snake_case id (ADR-0003)."""
    name: str
    """The source's name as people know it."""
    homepage: str
    """The source's public home page (``https``)."""
    terms: Terms
    """The licence class, terms page and date, attribution, notice, ``llm_use``
    and cache policy."""
    capabilities: tuple[Capability, ...] = (Capability.FETCH,)
    """What the provider implements; each needs its ``build_*`` and ``parse_*``."""
    auth: Authentication = field(default_factory=Authentication)
    """None, a key, or the user's contact."""
    access: Access = Access.HTTPS
    """HTTPS requests through a transport, or a local session."""
    hosts: tuple[str, ...] = ()
    """The exact host names the provider may contact, HTTPS only. Never a
    wildcard, a scheme or a port."""
    rate_limits: tuple[RateLimit, ...] = ()
    """The source's published limits, which the transport holds the provider to."""
    extra: str | None = None
    """The extra of the ``pyeconomics`` distribution that installs the provider's
    client library, a string literal; ``None`` for a provider with no extra."""
    platforms: tuple[Platform, ...] = tuple(Platform)
    """Where the provider runs; ``fetch`` refuses any other platform."""
    automated_collection: bool = True
    """Whether the source's terms allow automated collection. The scheduled live
    run skips a source whose terms bar it (ADR-0011 decision 18)."""
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    """The largest response body the transport reads, in bytes."""
    follow_redirects: bool = True
    """Whether the transport follows a redirect (to an allowlisted HTTPS host).
    ``False`` returns the redirect itself, for a source that answers a bad key
    with one (Census), so ``classify_error`` sees it and nothing follows a page
    that echoes the request."""
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    """How long the cache serves an open entry (``latest``, ``first_release``,
    ``all`` or a recent ``as_of``) before fetching again, in seconds; a user's
    ``PYECONOMICS_TTL_<PROVIDER>`` overrides it, and ``0`` turns the provider's
    caching off. A closed past vintage never expires. Ignored for a source whose
    terms forbid storage."""

    def __post_init__(self) -> None:
        """Turn sequences into tuples and enum values into members."""
        for name, kind in (
            ("capabilities", Capability),
            ("platforms", Platform),
        ):
            object.__setattr__(self, name, _members(kind, getattr(self, name)))
        object.__setattr__(self, "access", _member(Access, self.access))
        object.__setattr__(self, "hosts", _tuple(self.hosts))
        object.__setattr__(self, "rate_limits", _tuple(self.rate_limits))

    @property
    def key_variable(self) -> str | None:
        """The environment variable that holds the key, or ``None`` without one."""
        if self.auth.kind is AuthKind.KEY:
            return key_variable(self.id)
        return None

    def supports(self, platform: Platform) -> bool:
        """Return whether the provider runs on ``platform``."""
        return platform in self.platforms


def _member[E: StrEnum](kind: type[E], value: object) -> object:
    """Return the enum member for a value; anything else is left for the rules."""
    if isinstance(value, kind):
        return value
    if isinstance(value, str):
        try:
            return kind(value)
        except ValueError:
            return value
    return value


def _tuple(values: object) -> object:
    if isinstance(values, list | tuple | set | frozenset):
        return tuple(values)
    return values


def _members[E: StrEnum](kind: type[E], values: object) -> object:
    items = _tuple(values)
    if isinstance(items, tuple):
        return tuple(_member(kind, item) for item in items)
    return items


def current_platform() -> Platform | None:
    """Return the platform this process runs on, or ``None`` if it is unknown."""
    name = sys.platform
    if name == "emscripten":
        return Platform.PYODIDE
    if name.startswith("win"):
        return Platform.WINDOWS
    if name == "darwin":
        return Platform.MACOS
    if name.startswith("linux"):
        return Platform.LINUX
    return None


_SeriesId = Annotated[str, StringConstraints(pattern=_ANCHORED_SERIES_ID)]


class Query(BaseModel):
    """What to fetch: series ids, a date range, a size bound and a vintage.

    Bounded on every field: at most :data:`MAX_QUERY_SERIES` ids of at most 128
    characters, at most 100,000 observations, and dates inside the data layer's
    bounds, 1700-01-01 to 2200-12-31 (ADR-0011 decision 3). A provider with more
    options subclasses it and sets :attr:`DataProvider.query_type`.

    Examples
    --------
    >>> query = Query(series=("GDPC1",), max_observations=24, vintage="first_release")
    >>> query.series, query.max_observations, query.vintage_selector.label
    (('GDPC1',), 24, 'first_release')
    >>> Query(series=("GDPC1", "UNRATE")).start is None
    True

    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )

    series: tuple[_SeriesId, ...] = Field(min_length=1, max_length=MAX_QUERY_SERIES)
    start: dt.date | None = None
    """The first observation date wanted, if bounded."""
    end: dt.date | None = None
    """The last observation date wanted, if bounded."""
    max_observations: int = Field(default=MAX_OBSERVATIONS, ge=1, le=MAX_OBSERVATIONS)
    """At most this many observations per fetch, the most recent ones."""
    vintage: str = Field(default="latest", pattern=_ANCHORED_VINTAGE)
    """Which published version: ``latest``, ``first_release``, ``all`` or
    ``as_of:YYYY-MM-DD`` (ADR-0011 decision 6)."""

    @field_validator("start", "end")
    @classmethod
    def _in_bounds(cls, value: dt.date | None) -> dt.date | None:
        if value is not None and not DATA_DATE_BOUNDS.contains(value):
            msg = (
                f"{value} lies outside {DATA_DATE_BOUNDS.lower} to "
                f"{DATA_DATE_BOUNDS.upper}"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _ordered(self) -> Query:
        if len(set(self.series)) != len(self.series):
            msg = "series must not repeat an id"
            raise ValueError(msg)
        if self.start is not None and self.end is not None and self.start > self.end:
            msg = f"start {self.start} is after end {self.end}"
            raise ValueError(msg)
        Vintage.parse(self.vintage)  # the label's date must be a real date in bounds
        return self

    @property
    def vintage_selector(self) -> Vintage:
        """The :class:`~pyeconomics.data.vintage.Vintage` the label names."""
        return Vintage.parse(self.vintage)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchHit:
    """One result of :meth:`DataProvider.search`."""

    series_id: str
    title: str
    dataset: str | None = None
    frequency: ObservationFrequency | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        """Check the text fields and the frequency."""
        if not _SERIES_ID.fullmatch(f.text(self.series_id, "series_id")):
            msg = f"series_id is not a series id: {self.series_id!r}"
            raise f.fail(msg)
        f.text(self.title, "title")
        f.optional_text(self.dataset, "dataset")
        f.optional_text(self.unit, "unit")
        if self.frequency is not None:
            object.__setattr__(
                self,
                "frequency",
                f.choice(ObservationFrequency, self.frequency, "frequency"),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class Case:
    """One recorded interaction of a provider, for the recorder and the contract suite.

    A provider lists its cases in :attr:`DataProvider.cases`. The recorder
    (``scripts/record_cassettes.py``) runs each live and writes
    ``tests/providers/cassettes/<provider>/<name>.json``; the contract suite
    replays the same case offline. A case that expects an error is an *error
    cassette*: the recording holds the source's real failure response, which the
    provider maps to the taxonomy.
    """

    name: str
    """The cassette's file stem (snake_case)."""
    operation: Capability
    """Which public operation the case runs."""
    argument: Query | str
    """A :class:`Query` for ``fetch``; the text to find for ``search``; a series
    id for ``describe`` and ``vintages``."""
    expect: type[DataError] | None = None
    """The error the operation raises, for an error cassette."""
    invalid_key: bool = False
    """Whether the recorder sends a made-up key, to record a 401 or a 403."""
    keyless: bool = False
    """Whether the case runs with no key, for a source whose key is optional:
    the chain's key is withheld (:func:`~pyeconomics.data.credentials.withheld`)."""
    simulate: int | None = None
    """A failure status the recorder records in place of the source's answer, for
    an error no well-behaved client provokes on purpose: a 429 or a 5xx. The
    request is built but never sent, and the cassette is marked synthetic."""

    def __post_init__(self) -> None:
        """Check that the argument fits the operation."""
        f.identifier(self.name, "case name")
        f.flag(self.keyless, "keyless")
        f.flag(self.invalid_key, "invalid_key")
        if self.keyless and self.invalid_key:
            msg = "a keyless case sends no key, so it cannot send an invalid one"
            raise f.fail(msg)
        if self.simulate is not None and (
            self.simulate not in SIMULATED_STATUSES or self.expect is None
        ):
            msg = (
                "a simulated case stands in for a 429 or a 5xx and names the "
                "error it expects"
            )
            raise f.fail(msg)
        operation = f.choice(Capability, self.operation, "operation")
        object.__setattr__(self, "operation", operation)
        if operation is Capability.BULK:
            msg = "bulk is a capability, not an operation: record it as a fetch"
            raise f.fail(msg)
        wants = Query if operation in {Capability.FETCH, Capability.RECORDS} else str
        if not isinstance(self.argument, wants):
            msg = f"a {operation.value} case takes a {wants.__name__}"
            raise f.fail(msg)


def sends_key(info: ProviderInfo, key: str | Secret | None = None) -> bool:
    """Return whether the transport attaches a key to a provider's requests.

    It does for a source with a key that is required, given as an argument, or
    found by the key chain (an optional key is sent only when there is one).
    The transport and :attr:`DataProvider.sends_key` both ask this, so a
    provider's keyed or keyless requests always match what is sent.
    """
    auth = info.auth
    if auth.kind is not AuthKind.KEY:
        return False
    return key is not None or auth.required or has_key(info.id)


def tail[F: (Series, Table)](frame: F, count: int) -> F:
    """Keep the last ``count`` rows of a frame (the most recent observations).

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.data import (
    ...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
    ...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
    ... )
    >>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://example.org",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: Example.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> meta = SeriesMeta(provider="demo", series_id="X", title="X",
    ...     unit=UnitRecord(text="Index"), frequency=ObservationFrequency.ANNUAL,
    ...     seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
    ...     source_dating=DateConvention.PERIOD_END, terms=terms)
    >>> series = Series(
    ...     (dt.date(2023, 12, 31), dt.date(2024, 12, 31)), (1.0, 2.0), meta
    ... )
    >>> tail(series, 1).values
    (2.0,)

    """
    if len(frame.index) <= count:
        return frame
    keep = slice(len(frame.index) - count, None)
    realtime = None if frame.realtime is None else frame.realtime[keep]
    if isinstance(frame, Series):
        return replace(
            frame, index=frame.index[keep], values=frame.values[keep], realtime=realtime
        )
    return replace(
        frame,
        index=frame.index[keep],
        data=tuple(column[keep] for column in frame.data),
        realtime=realtime,
    )


class DataProvider:
    """The base class of every data provider.

    Subclass it, set :attr:`info`, and override the hooks of the capabilities
    :attr:`~ProviderInfo.capabilities` declares. Register the class in the
    ``pyeconomics.providers`` entry-point group.

    The public operations are final. Each one checks the capability and the
    platform, refuses a source hosted mode may not serve before any request,
    builds the requests, exchanges them, maps each response's status to the
    error taxonomy and checks what the ``parse_*`` hook returned.
    """

    info: ClassVar[ProviderInfo]
    """The provider's metadata; every concrete subclass sets it."""
    query_type: ClassVar[type[Query]] = Query
    """The query model :meth:`fetch` validates its argument with."""
    cases: ClassVar[tuple[Case, ...]] = ()
    """The interactions the recorder records and the contract suite replays."""

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401 - cooperative
        """Refuse a subclass that overrides a final public operation."""
        super().__init_subclass__(**kwargs)
        overridden = [name for name in _FINAL_METHODS if name in cls.__dict__]
        if overridden:
            msg = (
                f"{cls.__name__} overrides {', '.join(overridden)}: these hold the "
                "hosted-mode and status checks every request passes through; "
                "override the build_* and parse_* hooks instead"
            )
            raise TypeError(msg)

    # --- hooks a provider overrides -------------------------------------------

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Say what to ask for to answer ``query`` (capability ``fetch``)."""
        self._unimplemented("build_requests")

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Turn the answers to :meth:`build_requests` into a series or a table."""
        self._unimplemented("parse")

    def build_records(self, query: Query) -> Sequence[Request]:
        """Build requests for typed records (capability ``records``)."""
        self._unimplemented("build_records")

    def parse_records(self, responses: Sequence[Response], query: Query) -> Records:
        """Read identifier mappings or filings, never binding inputs."""
        self._unimplemented("parse_records")

    def build_search(self, text: str, limit: int) -> Sequence[Request]:
        """Say what to ask for to find series by ``text`` (capability ``search``)."""
        self._unimplemented("build_search")

    def parse_search(
        self, responses: Sequence[Response], text: str, limit: int
    ) -> Sequence[SearchHit]:
        """Turn the answers to :meth:`build_search` into hits."""
        self._unimplemented("parse_search")

    def build_describe(self, series_id: str) -> Sequence[Request]:
        """Say what to ask for to describe a series (capability ``describe``)."""
        self._unimplemented("build_describe")

    def parse_describe(
        self, responses: Sequence[Response], series_id: str
    ) -> SeriesMeta:
        """Turn the answers to :meth:`build_describe` into the series' metadata."""
        self._unimplemented("parse_describe")

    def build_vintages(self, series_id: str) -> Sequence[Request]:
        """Say what to ask for to list a series' vintages (capability ``vintages``)."""
        self._unimplemented("build_vintages")

    def parse_vintages(
        self, responses: Sequence[Response], series_id: str
    ) -> Sequence[dt.date]:
        """Turn the answers to :meth:`build_vintages` into the dates it changed."""
        self._unimplemented("parse_vintages")

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """Map a source's own error body to the taxonomy, or return ``None``.

        Called for any status outside 2xx before the default mapping (a redirect
        reaches it only from a source that does not follow them). A source
        that answers a missing series with HTTP 400 and a JSON message, say,
        returns a :class:`~pyeconomics.data.errors.SeriesNotFoundError` here.
        """
        return None

    def next_page(self, request: Request, response: Response) -> Request | None:
        """Return the request for the page after ``response``, or ``None``.

        A source that pages its answers (FRED v2's cursor, FiscalData's page
        numbers) overrides this; the default :meth:`exchange` follows it, and
        ``parse`` then receives every page, in order, after its first request's.
        """
        return None

    @property
    def sends_key(self) -> bool:
        """Whether the transport attaches a key in the operation now running.

        A build or parse hook of a source whose key is optional reads it to
        choose the keyed or the keyless API. Outside an operation it answers
        for a call with no explicit key.
        """
        current = _SENDS_KEY.get()
        return sends_key(self.info) if current is None else current

    def exchange(
        self,
        requests: Sequence[Request],
        *,
        key: str | Secret | None,
        transport: Transport | None,
    ) -> Sequence[Response]:
        """Send the requests and return their answers, in order.

        The default sends each through ``transport`` (the process's HTTPS
        transport when ``None``), follows :meth:`next_page` after each answer,
        and stops at the first failure status. A source that is not HTTPS, a
        terminal's desktop session say, overrides this and declares
        ``access=Access.SESSION`` and no hosts.
        """
        active = transport if transport is not None else default_transport()
        responses: list[Response] = []
        for first in requests:
            request: Request | None = first
            while request is not None:
                if len(responses) >= MAX_REQUESTS_PER_OPERATION:
                    msg = (
                        f"{self.info.id} needs more than "
                        f"{MAX_REQUESTS_PER_OPERATION} requests for one operation"
                    )
                    raise self._contract(msg)
                response = active.send(self.info, request, key=key)
                self._check_status(request, response)
                responses.append(response)
                request = self.next_page(request, response)
        return responses

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Trim a live recorder response without inventing observations.

        Called by the deliberate local recorder only, after the full answer
        parsed successfully. Third-party sources may keep the default when
        their requests already bound responses to the cassette size cap.
        """
        return response

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Replace every observed value in a response with a synthetic one.

        The recorder calls this for a source that is not hosted-safe or that
        forbids storage, so the cassette keeps the response's real structure and
        none of its values. Use
        :func:`~pyeconomics.data.transport.cassette.synthetic_value` for the
        numbers; keep titles, units and identifiers.
        """
        self._unimplemented("synthesize")

    # --- the public operations (final) -----------------------------------------

    @final
    def fetch(
        self,
        query: Query | Mapping[str, object],
        *,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> Series | Table:
        """Fetch the data a query names.

        Parameters
        ----------
        query
            A :attr:`query_type` or a mapping of its fields.
        key
            An explicit API key; otherwise the key chain finds one.
        transport
            The transport to send through; the process's HTTPS transport by default.

        Raises
        ------
        InputError
            If the query is invalid.
        LicenceError
            In hosted mode, for a source or series hosted mode may not serve.
        DataError
            The taxonomy's subclass the source's answer maps to: a
            ``CredentialError``, ``SeriesNotFoundError``, ``RateLimitError``,
            ``TransportError`` or ``ResponseError``.
        """
        return self.fetch_with_origin(query, key=key, transport=transport).frame

    @final
    def fetch_with_origin(
        self,
        query: Query | Mapping[str, object],
        *,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> Fetched:
        """Fetch the data a query names and say where it came from.

        This is :meth:`fetch` with the :class:`~pyeconomics.data.cache.policy.Origin`
        kept: whether the cache or offline mode served the frame, and the warning
        codes about it. ``Fetched.source()`` turns the pair into the
        :class:`~pyeconomics.core.provenance.DataSource` record a manifest carries.

        The cache is asked first (ADR-0011 decision 14). A source, or a series,
        whose terms forbid storage is never read from or written to it; a fresh
        entry of any other is returned without a request; and in offline mode only
        a cached entry answers, whatever its age.

        Raises
        ------
        OfflineError
            In offline mode, when nothing cached answers (and for a source whose
            terms forbid storage, which can never be served offline).
        """
        checked = self._query(query)
        self._gate(Capability.FETCH)
        if checked.vintage not in {"latest", "all"} and (
            Capability.VINTAGES not in self.info.capabilities
        ):
            msg = (
                f"{self.info.id} keeps no vintages, so {checked.vintage} cannot "
                "be read; ask for the latest data"
            )
            raise DataError(msg, provider=self.info.id)
        found = cache.lookup(self.info, checked)
        if found.fetched is not None:
            return found.fetched
        with self._keyed(key):
            responses = self._run(self.build_requests(checked), key, transport)
            frame = redaction.call_scrubbed(
                lambda: self.parse(responses, checked),
                lambda message: ResponseError(message, provider=self.info.id),
                catch=(
                    ValueError,
                    TypeError,
                    KeyError,
                    IndexError,
                    StopIteration,
                    OverflowError,
                ),
            )
        fetched = Fetched(
            self._finish(frame, checked, responses),
            Origin(warnings=found.warnings),
            checked.vintage,
        )
        cache.save(self.info, found, fetched)
        return fetched

    @final
    def records(
        self,
        query: Query | Mapping[str, object],
        *,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> Records:
        """Fetch typed records through the same gates as every other operation.

        Records have no frame-cache or vintage-selection semantics and cannot
        be used by a binding. Offline mode refuses them before a request.
        """
        checked = self._query(query)
        self._gate(Capability.RECORDS)
        if checked.vintage != "latest":
            msg = "records do not support vintage selection"
            raise self._contract(msg)
        with self._keyed(key):
            responses = self._run(self.build_records(checked), key, transport)
            result = redaction.call_scrubbed(
                lambda: self.parse_records(responses, checked),
                lambda message: ResponseError(message, provider=self.info.id),
                catch=(
                    ValueError,
                    TypeError,
                    KeyError,
                    IndexError,
                    StopIteration,
                    OverflowError,
                ),
            )
        candidate: object = result
        if not isinstance(candidate, Records) or candidate.provider != self.info.id:
            msg = "parse_records must return its own Records"
            raise self._contract(msg)
        modes.require_allowed(result.terms, provider=self.info.id)
        if len(result.rows) > checked.max_observations:
            msg = "records exceed the query's size bound"
            raise self._contract(msg)
        return result

    @final
    def search(
        self,
        text: str,
        *,
        limit: int = 25,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> tuple[SearchHit, ...]:
        """Find series by text (capability ``search``)."""
        f.text(text, "search text", max_length=256)
        if isinstance(limit, bool) or not 1 <= limit <= MAX_SEARCH_RESULTS:
            msg = f"limit must be between 1 and {MAX_SEARCH_RESULTS}"
            raise f.fail(msg)
        self._gate(Capability.SEARCH)
        with self._keyed(key):
            responses = self._run(self.build_search(text, limit), key, transport)
            hits = tuple(self.parse_search(responses, text, limit))
        if len(hits) > limit or not all(isinstance(hit, SearchHit) for hit in hits):
            msg = f"{self.info.id}.parse_search must return at most {limit} SearchHit"
            raise self._contract(msg)
        return hits

    @final
    def describe(
        self,
        series_id: str,
        *,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> SeriesMeta:
        """Describe a series without its observations (capability ``describe``)."""
        series = self._series_id(series_id)
        self._gate(Capability.DESCRIBE)
        with self._keyed(key):
            responses = self._run(self.build_describe(series), key, transport)
            candidate: object = self.parse_describe(responses, series)
        if not isinstance(candidate, SeriesMeta) or candidate.provider != self.info.id:
            msg = f"{self.info.id}.parse_describe must return its own SeriesMeta"
            raise self._contract(msg)
        meta = candidate
        modes.require_allowed(meta.terms, provider=self.info.id)
        if meta.retrieved_at is None:
            meta = replace(meta, retrieved_at=_latest(responses))
        return meta

    @final
    def vintages(
        self,
        series_id: str,
        *,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> tuple[dt.date, ...]:
        """List the dates a series changed, oldest first (capability ``vintages``)."""
        series = self._series_id(series_id)
        self._gate(Capability.VINTAGES)
        with self._keyed(key):
            responses = self._run(self.build_vintages(series), key, transport)
            days = tuple(self.parse_vintages(responses, series))
        checked = tuple(f.day(day, "a vintage date", DATA_DATE_BOUNDS) for day in days)
        if len(checked) > MAX_OBSERVATIONS or checked != tuple(sorted(set(checked))):
            msg = f"{self.info.id}.parse_vintages must return sorted, distinct dates"
            raise self._contract(msg)
        return checked

    @final
    def run_case(
        self,
        case: Case,
        *,
        key: str | Secret | None = None,
        transport: Transport | None = None,
    ) -> (
        Series
        | Table
        | Records
        | tuple[SearchHit, ...]
        | SeriesMeta
        | tuple[dt.date, ...]
    ):
        """Run a :class:`Case` through the public operation it names.

        A keyless case runs with the key chain's key withheld, and refuses an
        explicit key.
        """
        if not case.keyless:
            return self._run_case(case, key, transport)
        if key is not None:
            msg = f"{case.name} runs keyless, so it takes no key"
            raise self._contract(msg)
        with withheld(self.info.id):
            return self._run_case(case, None, transport)

    # --- internals ---------------------------------------------------------------

    def _run_case(
        self, case: Case, key: str | Secret | None, transport: Transport | None
    ) -> (
        Series
        | Table
        | Records
        | tuple[SearchHit, ...]
        | SeriesMeta
        | tuple[dt.date, ...]
    ):
        argument = case.argument
        if isinstance(argument, Query):
            if case.operation is Capability.RECORDS:
                return self.records(argument, key=key, transport=transport)
            return self.fetch(argument, key=key, transport=transport)
        text = argument
        if case.operation is Capability.SEARCH:
            return self.search(text, key=key, transport=transport)
        if case.operation is Capability.DESCRIBE:
            return self.describe(text, key=key, transport=transport)
        return self.vintages(text, key=key, transport=transport)

    @contextlib.contextmanager
    def _keyed(self, key: str | Secret | None) -> Generator[None]:
        """Say, for the hooks of one operation, whether a key is sent."""
        token = _SENDS_KEY.set(sends_key(self.info, key))
        try:
            yield
        finally:
            _SENDS_KEY.reset(token)

    def _unimplemented(self, hook: str) -> NoReturn:
        msg = f"{type(self).__name__} does not implement {hook}"
        raise NotImplementedError(msg)

    def _contract(self, message: str) -> DataError:
        return DataError(message, provider=self.info.id)

    def _query(self, query: Query | Mapping[str, object]) -> Query:
        if isinstance(query, self.query_type):
            return query
        try:
            return self.query_type.model_validate(
                query.model_dump() if isinstance(query, Query) else dict(query)
            )
        except ValidationError as error:
            raise InputError.from_validation_error(error) from None
        except (TypeError, ValueError):
            msg = f"a query is a {self.query_type.__name__} or a mapping of its fields"
            raise f.fail(msg) from None

    def _series_id(self, series_id: str) -> str:
        candidate: object = series_id
        if not isinstance(candidate, str) or not _SERIES_ID.fullmatch(candidate):
            msg = f"not a series id: {candidate!r}"
            raise f.fail(msg)
        return candidate

    def _gate(self, operation: Capability) -> None:
        """Refuse what the provider cannot do here, before anything is requested.

        That is an operation it lacks, a platform it does not run on, a source
        hosted mode may not serve and, for any operation but a fetch (which the
        cache answers or refuses), offline mode, which sends no request.
        """
        info = self.info
        if operation not in info.capabilities:
            msg = f"{info.id} does not support {operation.value}"
            raise DataError(msg, provider=info.id)
        platform = current_platform()
        if platform is None or not info.supports(platform):
            where = platform.value if platform else sys.platform
            msg = f"{info.id} does not run on {where}"
            raise DataError(msg, provider=info.id)
        modes.require_allowed(info.terms, provider=info.id)
        if operation is not Capability.FETCH:
            modes.require_online(provider=info.id)

    def _run(
        self,
        built: Sequence[Request],
        key: str | Secret | None,
        transport: Transport | None,
    ) -> Sequence[Response]:
        """Check the requests, exchange them and check every answer."""
        requests = tuple(built)
        if not 1 <= len(requests) <= MAX_REQUESTS_PER_OPERATION or not all(
            isinstance(request, Request) for request in requests
        ):
            msg = (
                f"{self.info.id} must build between 1 and "
                f"{MAX_REQUESTS_PER_OPERATION} Request values"
            )
            raise self._contract(msg)
        responses = tuple(self.exchange(requests, key=key, transport=transport))
        if not len(requests) <= len(responses) <= MAX_REQUESTS_PER_OPERATION or not all(
            isinstance(response, Response) for response in responses
        ):
            msg = (
                f"{self.info.id}.exchange must return a Response per request "
                "(and per further page)"
            )
            raise self._contract(msg)
        if len(responses) == len(requests):
            for request, response in zip(requests, responses, strict=True):
                self._check_status(request, response)
        elif not all(response.ok for response in responses):
            # Pages follow their requests, so a failure is no longer matched to
            # the request that met it; the default exchange already mapped it.
            msg = f"{self.info.id}.exchange returned a failed page"
            raise ResponseError(msg, provider=self.info.id)
        return responses

    def _check_status(self, request: Request, response: Response) -> None:
        """Map a response's final status to the error taxonomy."""
        status, info = response.status, self.info
        if not response.ok:
            custom = self.classify_error(request, response)
            if custom is not None:
                raise custom
        if 200 <= status < 300:  # noqa: PLR2004 - HTTP success statuses
            return
        if status in {401, 403}:
            where = f"set {info.key_variable}" if info.key_variable else "check access"
            msg = (
                f"{info.id} refused the request (HTTP {status}); {where}; "
                f"see {GUIDE_URL}"
            )
            raise CredentialError(msg, provider=info.id)
        if status == 404:  # noqa: PLR2004 - HTTP not found
            raise SeriesNotFoundError(info.id, request.series or request.path)
        if status == 429:  # noqa: PLR2004 - HTTP too many requests
            wait = retry_after_seconds(
                response.header("retry-after"), response.retrieved_at
            )
            msg = f"{info.id} is rate limiting requests (HTTP 429)"
            raise RateLimitError(msg, provider=info.id, retry_after=wait)
        if status >= 500:  # noqa: PLR2004 - HTTP server errors
            msg = f"{info.id} failed with HTTP {status}"
            raise TransportError(msg, provider=info.id)
        msg = f"{info.id} answered HTTP {status}, which the request does not expect"
        raise ResponseError(msg, provider=info.id)

    def _finish(
        self, frame: Series | Table, query: Query, responses: Sequence[Response]
    ) -> Series | Table:
        """Check what ``parse`` returned, stamp the retrieval time and trim it."""
        info = self.info
        candidate: object = frame
        if (
            not isinstance(candidate, Series | Table)
            or candidate.meta.provider != info.id
        ):
            msg = f"{info.id}.parse must return its own Series or Table"
            raise self._contract(msg)
        modes.require_allowed(candidate.meta.terms, provider=info.id)
        when, select = _latest(responses), query.vintage_selector
        if isinstance(candidate, Series):
            if candidate.meta.retrieved_at is None:
                meta = replace(candidate.meta, retrieved_at=when)
                candidate = replace(candidate, meta=meta)
            return tail(select.select(candidate), query.max_observations)
        if candidate.meta.retrieved_at is None:
            table_meta = replace(candidate.meta, retrieved_at=when)
            candidate = replace(candidate, meta=table_meta)
        return tail(select.select(candidate), query.max_observations)


def _latest(responses: Iterable[Response]) -> dt.datetime:
    return max(response.retrieved_at for response in responses)
