# tests/server/server_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the REST API's tests share (Phase 4 Step 6).

- :data:`LOOPBACK_ONLY`: every module here is marked with it. The app's event
  loop needs a socket pair, which ``--disable-socket`` refuses; allowing loopback
  hosts only lets sockets be made while any connection beyond this machine is
  still refused.
- :func:`client`: a ``TestClient`` over :func:`~pyeconomics.server.create_app`,
  addressed to 127.0.0.1 as a local server requires, with its lifespan run. It
  uses an inline pool (``workers=0``) unless told otherwise, so the registry a
  test installs is the one that runs.
- :func:`encode`: the GET form's ``?inputs=`` text for some inputs.
- :func:`problem`: a response's problem body, after checking its media type.
- Toy models for the pool and the error table: ``foundations.toy_nap`` sleeps
  for its input, ``foundations.toy_crash`` ends its own process, and
  ``foundations.toy_fail`` raises the error its input names (:data:`ERRORS`),
  with its ``message``. :func:`toy_registry` holds them and the registry tests'
  toys; :func:`use_toys` installs it for one test, and :func:`install_toys`, a
  pool's ``worker_setup``, in a spawned worker, where it also swaps the OS
  keyring for one that holds nothing.
- Hosted mode (Phase 4 Step 7): :func:`use_providers` makes some providers the
  installed ones for a test; :class:`RecordingPool` stands for urllib3 behind
  the real HTTPS transport, answering every request 404 and recording its URL,
  and :func:`use_recording_transport` installs it as the process's transport,
  :func:`install_recording_transport` in a spawned worker, and
  :func:`install_fuzz_world` there with a random key for every keyed source and
  a random SEC contact (the API fuzz);
  :class:`Plant` is a secret to look for with ``LeakCheck``.
"""

from __future__ import annotations

import base64
import os
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import pytest
import toy_models as toys
from fastapi.testclient import TestClient
from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    ConvergenceError,
    CostClass,
    DomainError,
    Evidence,
    Example,
    InputError,
    MissingOptionalDependencyError,
    ModelInputs,
    ModelNotFoundError,
    ModelOutputs,
    PyeconomicsError,
    Registry,
    RegistryError,
    Years,
    model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.server import ServerSettings, create_app

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping

    import httpx2
    from fastapi import FastAPI

    from pyeconomics.server.settings import ServerMode

__all__ = [
    "ERRORS",
    "LOCAL",
    "LOOPBACK_ONLY",
    "Plant",
    "RecordingPool",
    "broken_setup",
    "client",
    "crash",
    "encode",
    "fail",
    "install_fuzz_world",
    "install_recording_transport",
    "install_toys",
    "nap",
    "openapi_of",
    "problem",
    "service_of",
    "toy_registry",
    "use_providers",
    "use_recording_transport",
    "use_toys",
]

#: Where a local server's tests address it.
LOCAL = "http://127.0.0.1"
#: Sockets for the event loop, connections to loopback hosts only.
LOOPBACK_ONLY = pytest.mark.allow_hosts(["127.0.0.1", "::1"])


def _errors() -> dict[str, Callable[[str], BaseException]]:
    from pyeconomics.ai.errors import (  # noqa: PLC0415 - the AI narrative's errors
        NarrativeDisabledError,
        NarrativeHostedError,
    )
    from pyeconomics.data import (  # noqa: PLC0415 - the data layer's errors
        ConceptNotFoundError,
        ConfigError,
        CredentialError,
        DataError,
        LicenceError,
        LlmUse,
        LlmUseError,
        OfflineError,
        ProviderNotFoundError,
        RateLimitError,
        ResponseError,
        SeriesNotFoundError,
        SourceDisabledError,
        TransportError,
    )
    from pyeconomics.surfaces.budgets import BudgetExceededError  # noqa: PLC0415
    from pyeconomics.surfaces.codec import InputTooLargeError  # noqa: PLC0415
    from pyeconomics.surfaces.service import (  # noqa: PLC0415
        EdgeRefusedError,
        HostNotAllowedError,
        LimitsUnavailableError,
        MethodNotAllowedError,
        RouteNotFoundError,
        ServerBusyError,
        TooManyRequestsError,
    )

    library_only = LicenceClass.LIBRARY_ONLY
    return {
        "InputError": InputError,
        "InputTooLargeError": lambda text: InputTooLargeError(len(text), 1),
        "DomainError": DomainError,
        "ConvergenceError": ConvergenceError,
        "ModelNotFoundError": ModelNotFoundError,
        "ProviderNotFoundError": ProviderNotFoundError,
        "ConceptNotFoundError": ConceptNotFoundError,
        "SeriesNotFoundError": lambda text: SeriesNotFoundError("toy", text),
        "LicenceError": lambda text: LicenceError(
            text,
            provider="toy",
            licence=library_only,
            terms_url="https://www.example.org/terms",
        ),
        "LlmUseError": lambda text: LlmUseError(
            text,
            provider="toy",
            licence=library_only,
            llm_use=LlmUse.FORBIDDEN,
            terms_url="https://www.example.org/terms",
        ),
        "NarrativeDisabledError": lambda _text: NarrativeDisabledError(),
        "NarrativeHostedError": lambda _text: NarrativeHostedError(),
        "CredentialError": lambda text: CredentialError(text, provider="toy"),
        "TransportError": lambda text: TransportError(text, provider="toy"),
        "ResponseError": lambda text: ResponseError(text, provider="toy"),
        "RateLimitError": lambda text: RateLimitError(
            text, provider="toy", retry_after=2.5
        ),
        "OfflineError": lambda text: OfflineError(text, provider="toy"),
        "SourceDisabledError": lambda _text: SourceDisabledError("toy"),
        "DataError": DataError,
        "MissingOptionalDependencyError": lambda text: MissingOptionalDependencyError(
            "toy_library", note=text
        ),
        "BudgetExceededError": lambda text: BudgetExceededError(text, 2.0),
        "RouteNotFoundError": lambda _text: RouteNotFoundError(),
        "MethodNotAllowedError": lambda _text: MethodNotAllowedError(["GET"]),
        "HostNotAllowedError": lambda _text: HostNotAllowedError(),
        "ServerBusyError": lambda _text: ServerBusyError(1),
        "EdgeRefusedError": lambda _text: EdgeRefusedError(),
        "TooManyRequestsError": lambda _text: TooManyRequestsError(
            "2 per 1 second", 0.4
        ),
        "LimitsUnavailableError": lambda _text: LimitsUnavailableError(),
        "RegistryError": lambda text: RegistryError(text, problems=(text,)),
        "ConfigError": ConfigError,
        "PyeconomicsError": PyeconomicsError,
        "Exception": RuntimeError,
    }


#: Each error the table maps, by its class's name, made from a message.
ERRORS: Mapping[str, Callable[[str], BaseException]] = _errors()

_COMMON: dict[str, Any] = {
    "formula": (r"y = x",),
    "assumptions": ("A toy.",),
    "limitations": ("It models nothing.",),
    "references": (toys.FISHER,),
    "evidence": Evidence.PRACTITIONER,
    "no_invariants_reason": "A toy for the server tests.",
    "changelog": (ChangelogEntry(version=1, note="First version."),),
}


class NapInputs(ModelInputs):
    seconds: Years = Field(ge=0, le=60, description="How long to sleep")


class NapOutputs(ModelOutputs):
    slept: Years = Field(ge=0, le=60, description="How long it slept")


@model(
    id="foundations.toy_nap",
    version=1,
    title="Toy nap",
    summary="Sleeps for as long as it is asked.",
    cost=CostClass.INSTANT,
    examples=(Example(name="short", inputs={"seconds": 0.01}),),
    **_COMMON,
)
def nap(inputs: NapInputs) -> NapOutputs:
    time.sleep(inputs.seconds)
    return NapOutputs(slept=inputs.seconds)


@model(
    id="foundations.toy_crash",
    version=1,
    title="Toy crash",
    summary="Ends the process it runs in.",
    cost=CostClass.INSTANT,
    examples=(Example(name="now", inputs={"seconds": 0}),),
    **_COMMON,
)
def crash(inputs: NapInputs) -> NapOutputs:
    del inputs
    os._exit(3)  # the worker dies mid-task


class FailInputs(ModelInputs):
    error: str = Field(max_length=64, description="The error class to raise")
    message: str = Field("a toy failure", max_length=10_000, description="Its text")


@model(
    id="foundations.toy_fail",
    version=1,
    title="Toy failure",
    summary="Raises the error it is asked to.",
    cost=CostClass.INSTANT,
    examples=(Example(name="domain", inputs={"error": "DomainError"}),),
    **_COMMON,
)
def fail(inputs: FailInputs) -> NapOutputs:
    raise ERRORS[inputs.error](inputs.message)


def toy_registry() -> Registry:
    """The server's toys with the registry tests' toys (an alias among them)."""
    return Registry.from_models(
        crash,
        fail,
        nap,
        *toys.ALL_MODELS,
        distribution="toy-dist",
        extras=toys.EXTRAS,
    )


def install_toys() -> None:
    """Make the toy registry the installed one; a worker's setup, too."""
    core_registry._CACHE.registry = toy_registry()  # noqa: SLF001
    try:
        import keyring  # noqa: PLC0415 - the keyring extra
        from keyring.backends import fail as failing  # noqa: PLC0415
    except ImportError:  # pragma: no cover - the test group installs keyring
        return
    keyring.set_keyring(failing.Keyring())  # type: ignore[no-untyped-call]


def broken_setup() -> None:
    """A worker setup that fails, so the worker never starts."""
    msg = "this worker cannot start"
    raise RuntimeError(msg)


def use_toys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the toy registry the installed one for one test."""
    monkeypatch.setattr(core_registry._CACHE, "registry", toy_registry())  # noqa: SLF001


@contextmanager
def client(
    *,
    mode: ServerMode = "local",
    base_url: str = LOCAL,
    **settings: Any,  # noqa: ANN401 - ServerSettings' fields
) -> Generator[TestClient]:
    """Serve an app in this process, its lifespan run, until the block ends."""
    settings.setdefault("workers", 0)
    app = create_app(mode=mode, settings=ServerSettings(**settings))
    with TestClient(app, base_url=base_url) as test_client:
        yield test_client


def service_of(api: TestClient) -> Any:  # noqa: ANN401 - the app's private service
    """Return the service a test client's app keeps its pool and documents in."""
    app = cast("FastAPI", api.app)
    return app.state.service


def openapi_of(api: TestClient) -> dict[str, Any]:
    """Return a test client's app's OpenAPI document."""
    return cast("FastAPI", api.app).openapi()


def encode(inputs: Mapping[str, object]) -> str:
    """Return the GET form's ``?inputs=``: canonical JSON, base64url, no padding."""
    return base64.urlsafe_b64encode(canonical_json(inputs)).rstrip(b"=").decode()


def problem(response: httpx2.Response) -> dict[str, Any]:
    """Return a response's problem, after checking it is one."""
    assert response.headers["content-type"] == "application/problem+json"
    body: dict[str, Any] = response.json()
    assert body["status"] == response.status_code
    return body


# --- hosted mode (Phase 4 Step 7) ----------------------------------------------------


@dataclass(frozen=True)
class Plant:
    """A secret planted in a test, for ``LeakCheck``: never printed."""

    value: str = field(repr=False)

    def needles(self) -> tuple[str, ...]:
        """The secret itself."""
        return (self.value,)


def use_providers(monkeypatch: pytest.MonkeyPatch, *providers: type[Any]) -> None:
    """Make these data providers the installed ones for one test."""
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415
    from pyeconomics.data.registry import ProviderRegistry  # noqa: PLC0415

    monkeypatch.setattr(
        provider_registry._CACHE,  # noqa: SLF001
        "registry",
        ProviderRegistry.from_providers(*providers),
    )


class RecordingPool:
    """A urllib3 pool that records each URL and answers every request 404.

    It stands behind the real :class:`~pyeconomics.data.transport.http.
    HttpTransport`, so a URL it records is one the transport built and would have
    sent, after the transport's own host allowlist.
    """

    def __init__(self) -> None:
        self.urls: list[str] = []
        self._lock = threading.Lock()

    def request(self, method: str, url: str, **_kwargs: Any) -> Any:  # noqa: ANN401
        """Record the URL; answer 404 with an empty body."""
        from fakes import FakeRaw  # noqa: PLC0415 - tests/providers' urllib3 fakes

        with self._lock:
            self.urls.append(url)
        del method
        return FakeRaw(status=404, body=b"")

    def clear(self) -> None:
        """Mirror ``PoolManager.clear``."""


def _recording_transport(pool: RecordingPool) -> Any:  # noqa: ANN401 - the transport
    from fakes import FakeClock  # noqa: PLC0415

    from pyeconomics.data.transport.http import HttpTransport  # noqa: PLC0415

    clock = FakeClock()  # a provider's rate limit waits on it, not on the wall
    return HttpTransport(pool=pool, clock=clock.monotonic, sleep=clock.sleep)


def use_recording_transport(monkeypatch: pytest.MonkeyPatch) -> RecordingPool:
    """Send every data request of this test to a recording pool, and return it."""
    from pyeconomics.data import transport  # noqa: PLC0415

    pool = RecordingPool()
    monkeypatch.setitem(
        transport._DEFAULT,  # noqa: SLF001
        "http",
        _recording_transport(pool),
    )
    return pool


def install_recording_transport() -> None:
    """A spawned worker's setup: no request leaves, no key is found."""
    from pyeconomics.data import transport  # noqa: PLC0415

    transport._DEFAULT["http"] = _recording_transport(RecordingPool())  # noqa: SLF001
    try:
        import keyring  # noqa: PLC0415 - the keyring extra
        from keyring.backends import fail as failing  # noqa: PLC0415
    except ImportError:  # pragma: no cover - the test group installs keyring
        return
    keyring.set_keyring(failing.Keyring())  # type: ignore[no-untyped-call]


def install_fuzz_world() -> None:
    """A fuzzed worker's setup: the recording pool, and every credential present.

    Each keyed source gets a random key and SEC EDGAR a random contact, in this
    worker process only, so no source is passed over for a missing credential:
    every data answer is the recording pool's 404, never a 503 a missing key
    would rightly give.
    """
    from pyeconomics.data import config, registry  # noqa: PLC0415

    install_recording_transport()
    current = config.settings()
    for info in registry.installed().infos():
        if info.key_variable is not None:
            os.environ[info.key_variable] = secrets.token_hex(16)
    contact = f"pyeconomics fuzz {secrets.token_hex(4)}@example.org"
    os.environ["PYECONOMICS_SEC_CONTACT"] = contact
    config.reset()
    config.configure(mode=current.mode, offline=current.offline)
