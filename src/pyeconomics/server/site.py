# src/pyeconomics/server/site.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The local web app: the built site that ``pyeconomics serve`` serves at ``/``.

ADR-0013 decision 16. The ``pyeconomics-app`` distribution (``pip install
"pyeconomics[app]"``) holds the static site Cloudflare serves in production;
:func:`packaged_site` finds it, and :func:`mount` adds it to a local app after
every API route, so ``/v1``, ``/mcp``, ``/docs``, ``/redoc``, ``/openapi.json``,
``/healthz`` and ``/version`` keep their answers, and every other ``GET`` or
``HEAD`` reads the site:

- a directory answers its ``index.html``, a directory without its trailing slash
  redirects to it, and a path the site lacks answers its ``404.html``;
- a path under ``/v1/``, or one an API route matches for another method, never
  reaches the site, so the API's own problems answer it as before;
- files are read with Starlette's ``StaticFiles`` without following a symbolic
  link out of the directory, and no path escapes it (``..`` included);
- the site's ``_headers`` file, the one source of the production policy, is
  parsed as Cloudflare reads it (:class:`HeaderRules`) and applied to every site
  response, with ``X-Robots-Tag: noindex`` beside it; ``_redirects`` answers its
  redirects as Cloudflare does (:func:`parse_redirects`), and neither file is
  served itself.

A site whose ``_headers`` cannot be read, or sets no Content-Security-Policy for
``/``, is refused (``ConfigError``) rather than served without it. The loopback
guard is the app's own and wraps the site too.

Examples
--------
>>> rules = HeaderRules.parse("/*\n  X-Frame: deny\n/_astro/*\n  Max: 60\n")
>>> rules.for_path("/_astro/a.js")
{'X-Frame': 'deny', 'Max': '60'}
>>> parse_redirects("/old/ /new/ 301\n")
{'/old/': ('/new/', 301)}
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.routing import BaseRoute, Match, Mount, Route
from starlette.staticfiles import StaticFiles

from pyeconomics.data.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fastapi import FastAPI
    from starlette.types import Message, Receive, Scope, Send

__all__ = [
    "APP_MODULE",
    "BUILD_HINT",
    "INSTALL_HINT",
    "NOINDEX",
    "HeaderRules",
    "missing_hint",
    "mount",
    "packaged_site",
    "parse_redirects",
]

#: The module of the ``pyeconomics-app`` distribution.
APP_MODULE: Final = "pyeconomics_app"
#: What ``serve`` logs when the web app is not installed.
INSTALL_HINT: Final = (
    'the web app is not installed: pip install "pyeconomics[app]" to serve it at /'
)
#: What ``serve`` logs when the web app is installed with no built site in it.
BUILD_HINT: Final = (
    "pyeconomics-app holds no built site: in a checkout, run npm run build in web/ "
    "and then python scripts/web/package_site.py"
)
#: The header every site response carries: the local site is never indexed.
NOINDEX: Final = ("X-Robots-Tag", "noindex")
#: The files that configure the site and are never served as pages.
CONFIG_FILES: Final = frozenset({"_headers", "_redirects"})
#: The redirect statuses a ``_redirects`` line may give (Cloudflare's).
REDIRECT_STATUSES: Final = frozenset({301, 302, 303, 307, 308})

# A site's media types by suffix, so a module script is never served as
# text/plain where the platform's own table says so (Windows reads its registry).
_MEDIA_TYPES: Final = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".mjs": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".wasm": "application/wasm",
    ".webmanifest": "application/manifest+json",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".xml": "application/xml",
}
_OCTETS: Final = "application/octet-stream"
_PLACEHOLDER: Final = re.compile(r"(\*|:[A-Za-z]\w*)")
_API_PREFIX: Final = "/v1"


def packaged_site() -> Path | None:
    """Return the installed web app's built site; ``None`` when there is none.

    ``None`` means ``pyeconomics-app`` is not installed, or holds no
    ``index.html`` (a checkout before ``scripts/web/package_site.py``), or is not
    on the file system: :func:`missing_hint` says which to tell the user.
    """
    if importlib.util.find_spec(APP_MODULE) is None:
        return None
    site = importlib.import_module(APP_MODULE).site_path()
    if not isinstance(site, Path) or not (site / "index.html").is_file():
        return None
    return site


def missing_hint() -> str:
    """Return the line ``serve`` logs when :func:`packaged_site` found nothing."""
    return INSTALL_HINT if importlib.util.find_spec(APP_MODULE) is None else BUILD_HINT


# --- _headers and _redirects -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Rule:
    pattern: re.Pattern[str]
    headers: tuple[tuple[str, str], ...]
    detach: tuple[str, ...]


def _pattern(path: str) -> re.Pattern[str]:
    """Compile a rule's path: ``*`` matches anything, ``:name`` one segment."""
    parts = _PLACEHOLDER.split(path)
    return re.compile(
        "".join(
            ".*"
            if part == "*"
            else "[^/]+"
            if part.startswith(":")
            else re.escape(part)
            for part in parts
        )
    )


def _site_path(text: str) -> bool:
    """Return whether text is a path on the site's own origin."""
    return text.startswith("/") and not text.startswith("//") and "\\" not in text


class HeaderRules:
    """A ``_headers`` file as Cloudflare reads it: path rules and their headers.

    A line that starts at the margin is a path (``*`` matches anything, ``:name``
    one segment); each indented ``Name: value`` line below it adds a header and
    ``! Name`` removes one an earlier rule added. Every rule whose path matches
    applies, in order, and a header two rules set holds both values, joined by
    a comma. Blank lines and ``#`` comments are skipped.
    """

    def __init__(self, rules: Sequence[_Rule]) -> None:
        self._rules = tuple(rules)

    @classmethod
    def parse(cls, text: str) -> HeaderRules:
        """Read a ``_headers`` file's text.

        Raises
        ------
        ConfigError
            For a rule that is not a path on the site, or a header line that is
            not ``Name: value`` or ``! Name``, or one before any rule.
        """
        rules: list[_Rule] = []
        path: str | None = None
        headers: list[tuple[str, str]] = []
        detach: list[str] = []

        def close() -> None:
            if path is not None:
                rules.append(_Rule(_pattern(path), tuple(headers), tuple(detach)))

        for number, line in enumerate(text.splitlines(), start=1):
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            if not line[0].isspace():
                close()
                if not _site_path(entry):
                    msg = f"_headers line {number}: a rule is a path from /: {entry!r}"
                    raise ConfigError(msg)
                path, headers, detach = entry, [], []
                continue
            name, separator, value = entry.removeprefix("!").partition(":")
            if path is None or not name.strip():
                msg = f"_headers line {number}: a header outside a rule"
                raise ConfigError(msg)
            if entry.startswith("!"):
                detach.append(name.strip())
            elif separator:
                headers.append((name.strip(), value.strip()))
            else:
                msg = f"_headers line {number}: a header is Name: value"
                raise ConfigError(msg)
        close()
        return cls(rules)

    def for_path(self, path: str) -> dict[str, str]:
        """Return the headers every matching rule gives a path, in order."""
        found: dict[str, tuple[str, str]] = {}
        for rule in self._rules:
            if not rule.pattern.fullmatch(path):
                continue
            for name, value in rule.headers:
                key = name.lower()
                if key in found:
                    first, values = found[key]
                    found[key] = (first, f"{values}, {value}")
                else:
                    found[key] = (name, value)
            for name in rule.detach:
                found.pop(name.lower(), None)
        return dict(found.values())


def parse_redirects(text: str) -> dict[str, tuple[str, int]]:
    """Read a ``_redirects`` file: ``from to [status]`` per line, 302 by default.

    Only exact paths on the site's own origin are read, which is what the build
    writes (``web/scripts/indexing.ts``).

    Raises
    ------
    ConfigError
        For a line that is not two paths and an optional redirect status, a path
        that is not on the site, or a splat or placeholder.
    """
    redirects: dict[str, tuple[str, int]] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        fields = entry.split()
        status = fields[2] if len(fields) == 3 else "302"  # noqa: PLR2004 - from to status
        if (
            len(fields) not in {2, 3}
            or not all(_site_path(field) for field in fields[:2])
            or _PLACEHOLDER.search(fields[0])
            or not status.isdigit()
            or int(status) not in REDIRECT_STATUSES
        ):
            msg = f"_redirects line {number}: not an exact redirect between site paths"
            raise ConfigError(msg)
        redirects[fields[0]] = (fields[1], int(status))
    return redirects


# --- serving ------------------------------------------------------------------------


class _StaticSite(StaticFiles):
    """StaticFiles with the site's own media types, hiding its configuration files.

    A configuration file is refused by the file it resolves to, so no spelling
    of its path (a trailing slash, another case on a case-insensitive file
    system) reaches it; the site's 404 page answers instead.
    """

    def __init__(self, directory: Path) -> None:
        super().__init__(directory=directory, html=True, follow_symlink=False)
        self.hidden = frozenset(
            os.path.normcase(os.path.realpath(directory / name))
            for name in CONFIG_FILES
        )

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        """Find a file as StaticFiles does, never a configuration file."""
        full_path, stat_result = super().lookup_path(path)
        if stat_result is not None and os.path.normcase(full_path) in self.hidden:
            return "", None
        return full_path, stat_result

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Answer a file, as StaticFiles does, with its media type from the table."""
        response = super().file_response(full_path, stat_result, scope, status_code)
        if isinstance(response, FileResponse):
            media = _MEDIA_TYPES.get(Path(full_path).suffix.lower(), _OCTETS)
            response.media_type = media
            response.headers["content-type"] = media
        return response


class _Site:
    """The site's ASGI app: its files, its redirects and its headers."""

    def __init__(
        self,
        directory: Path,
        rules: HeaderRules,
        redirects: Mapping[str, tuple[str, int]],
    ) -> None:
        self.rules = rules
        self.redirects = dict(redirects)
        self.files = _StaticSite(directory)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path: str = scope["path"]
        headers = {**self.rules.for_path(path), NOINDEX[0]: NOINDEX[1]}

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                given = MutableHeaders(scope=message)
                for name, value in headers.items():
                    given[name] = value
            await send(message)

        redirect = self.redirects.get(path)
        if redirect is None:
            await self.files(scope, receive, with_headers)
            return
        query = scope.get("query_string", b"").decode("latin-1")
        target = f"{redirect[0]}?{query}" if query else redirect[0]
        response = RedirectResponse(target, status_code=redirect[1])
        await response(scope, receive, with_headers)


class _SiteMount(Mount):
    """The site at ``/``: only ``GET`` and ``HEAD``, never an API path.

    It names itself in the scope, so the access line names its template
    (``/{path}``), never the path a caller sent.
    """

    def __init__(self, app: _Site, api: Sequence[BaseRoute]) -> None:
        super().__init__("", app=app, name="site")
        self.api = tuple(route for route in api if isinstance(route, Route))

    def _is_api(self, path: str) -> bool:
        if path == _API_PREFIX or path.startswith(f"{_API_PREFIX}/"):
            return True
        return any(route.path_regex.match(path) for route in self.api)

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """Match a site request; leave the API's paths and methods to the API."""
        if (
            scope["type"] != "http"
            or scope.get("method") not in {"GET", "HEAD"}
            or self._is_api(scope["path"])
        ):
            return Match.NONE, {}
        match, child = super().matches(scope)
        if match is not Match.NONE:
            child["route"] = self
        return match, child


def _read(directory: Path, name: str) -> str | None:
    path = directory / name
    return path.read_text(encoding="utf-8") if path.is_file() else None


def mount(app: FastAPI, directory: Path) -> None:
    """Serve a built site at ``/`` behind every route the app has now.

    Raises
    ------
    ConfigError
        If the directory holds no ``index.html`` or no ``_headers``, its
        ``_headers`` or ``_redirects`` cannot be read, or its rules give ``/`` no
        Content-Security-Policy.
    """
    if not (directory / "index.html").is_file():
        msg = f"the web app's site holds no index.html; {BUILD_HINT}"
        raise ConfigError(msg)
    text = _read(directory, "_headers")
    if text is None:
        msg = "the web app's site holds no _headers: it would be served without them"
        raise ConfigError(msg)
    rules = HeaderRules.parse(text)
    policy = Headers(headers=rules.for_path("/")).get("content-security-policy")
    if not policy:
        msg = "the web app's _headers sets no Content-Security-Policy for /"
        raise ConfigError(msg)
    redirects = parse_redirects(_read(directory, "_redirects") or "")
    site = _Site(directory.resolve(), rules, redirects)
    app.router.routes.append(_SiteMount(site, app.router.routes))
