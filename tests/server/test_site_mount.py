# tests/server/test_site_mount.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The web app at ``/`` in a local server (Phase 5 Step 10; ADR-0013 decision 16).

A small built site stands in for ``pyeconomics-app``'s: pages, a 404 page, an
``_astro`` script, ``version.json``, and the ``_headers`` and ``_redirects`` files
the build writes. Mounted through ``ServerSettings.site`` (what ``pyeconomics
serve`` passes), it must leave every API route's answer as it was, carry the
site's own headers and ``noindex`` on each of its responses and on none of the
API's, answer its 404 page for a path it lacks, never serve its configuration
files or a file outside its directory, and sit behind the same loopback guard.
Without the package, or with it but no build in it, ``serve`` logs one hint and
serves the API alone.
"""

from __future__ import annotations

import importlib.machinery
import logging
import os
import sys
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from cli_support import cli
from server_support import LOOPBACK_ONLY, client, problem

from pyeconomics.cli import serve_command
from pyeconomics.core.errors import InputError
from pyeconomics.data.errors import ConfigError
from pyeconomics.server import ServerSettings, create_app, logs, site

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

pytestmark = LOOPBACK_ONLY

POLICY = "default-src 'self'; script-src 'self'; frame-ancestors 'none'"
IMMUTABLE = "public, max-age=31536000, immutable"
HEADERS = f"""/*
  Content-Security-Policy: {POLICY}
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
/_astro/*
  Cache-Control: {IMMUTABLE}
"""
OUTSIDE = "outside the site"


@pytest.fixture
def built(tmp_path: Path) -> Path:
    """A built site, and a secret beside it that it must never serve."""
    root = tmp_path / "site"
    pages = {
        "index.html": "<h1>home</h1>",
        "404.html": "<h1>not here</h1>",
        "models/demo/model/index.html": "<h1>a model</h1>",
        "_astro/app.js": "export const a = 1;",
        "version.json": '{"pyeconomics":"1.0.0","git_sha":"' + "a" * 40 + '"}',
        # Names an API route also answers: the API keeps them.
        "healthz": "the site's healthz",
        "v1/index.html": "<h1>the site's v1</h1>",
        "_headers": HEADERS,
        "_redirects": "/models/old/ /models/demo/model/ 301\n",
    }
    for name, text in pages.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / "secret.txt").write_text(OUTSIDE, encoding="utf-8")
    return root


def _link(target: Path, link: Path) -> bool:
    """Link a directory, as a symbolic link or, on Windows, a junction."""
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            return False
        import _winapi  # noqa: PLC0415 - Windows only

        _winapi.CreateJunction(str(target), str(link))
    return True


def _last_route(app: FastAPI) -> str | None:
    name: str | None = getattr(app.router.routes[-1], "name", None)
    return name


# --- precedence ---------------------------------------------------------------------


API_PATHS = (
    "/healthz",
    "/version",
    "/v1/models",
    "/v1/models/foundations.time_value",
    "/v1/no-such-route",
    "/v1/",
    "/v1",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/mcp",
)


def _answers(api: TestClient) -> dict[str, tuple[int, str | None, bytes]]:
    answers = {}
    for path in API_PATHS:
        response = api.get(path, follow_redirects=False)
        assert "content-security-policy" not in response.headers, path
        assert "x-robots-tag" not in response.headers, path
        answers[path] = (
            response.status_code,
            response.headers.get("content-type"),
            response.content,
        )
    return answers


def test_every_api_route_keeps_its_answer(built: Path) -> None:
    with client() as api:
        before = _answers(api)
    with client(site=built) as api:
        after = _answers(api)
        under_v1 = api.get("/v1/")
    assert after == before
    assert before["/healthz"][0] == 200
    assert before["/mcp"][0] == 405
    assert problem(under_v1)["type"].endswith("/route-not-found")


def test_a_method_the_site_does_not_take_is_the_apis_problem(built: Path) -> None:
    with client(site=built) as api:
        response = api.post("/models/demo/model/")
    assert response.status_code == 404
    assert problem(response)["type"].endswith("/route-not-found")


def test_the_site_is_the_last_route(built: Path) -> None:
    app = create_app(settings=ServerSettings(workers=0, site=built))
    assert _last_route(app) == "site"


# --- pages, headers and the 404 page -------------------------------------------------


def test_pages_answer_with_the_sites_headers_and_noindex(built: Path) -> None:
    with client(site=built) as api:
        home = api.get("/")
        page = api.get("/models/demo/model/")
        script = api.get("/_astro/app.js")
        version = api.get("/version.json")
    assert home.text == "<h1>home</h1>"
    assert page.text == "<h1>a model</h1>"
    assert version.json()["pyeconomics"] == "1.0.0"
    for response in (home, page, script, version):
        assert response.status_code == 200
        assert response.headers["content-security-policy"] == POLICY
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert response.headers["x-robots-tag"] == "noindex"
    assert home.headers["content-type"] == "text/html; charset=utf-8"
    assert script.headers["content-type"] == "text/javascript; charset=utf-8"
    assert script.headers["cache-control"] == IMMUTABLE
    assert "cache-control" not in home.headers
    assert version.headers["content-type"] == "application/json"


def test_a_directory_without_its_slash_redirects_to_it(built: Path) -> None:
    with client(site=built) as api:
        response = api.get("/models/demo/model", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/models/demo/model/")
    assert response.headers["x-robots-tag"] == "noindex"


def test_an_unknown_path_answers_the_404_page(built: Path) -> None:
    with client(site=built) as api:
        response = api.get("/models/no-such/page/")
        head = api.head("/no-such-file.js")
    assert response.status_code == 404
    assert response.text == "<h1>not here</h1>"
    assert response.headers["content-security-policy"] == POLICY
    assert response.headers["x-robots-tag"] == "noindex"
    assert head.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/_headers",
        "/_redirects",
        "/_headers/",
        "/%2f_redirects",
        "/models/../_headers",
        "/%5f%68eaders",
    ],
)
def test_the_configuration_files_are_not_served(built: Path, path: str) -> None:
    with client(site=built) as api:
        responses = [api.get(path)]
        if sys.platform == "win32":  # a case-insensitive file system
            responses += [api.get(path.upper()), api.get(f"{path}.")]
    for response in responses:
        assert response.status_code == 404
        assert response.text == "<h1>not here</h1>"
        assert response.headers["x-robots-tag"] == "noindex"


def test_a_redirect_answers_as_written_with_its_query(built: Path) -> None:
    with client(site=built) as api:
        plain = api.get("/models/old/", follow_redirects=False)
        query = api.get("/models/old/?tab=1", follow_redirects=False)
    assert plain.status_code == 301
    assert plain.headers["location"] == "/models/demo/model/"
    assert query.headers["location"] == "/models/demo/model/?tab=1"
    assert plain.headers["content-security-policy"] == POLICY


def test_the_access_line_names_the_template_never_the_path(
    built: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=logs.ACCESS_LOGGER)
    with client(site=built) as api:
        api.get("/models/demo/model/?secret-ish=1")
    lines = [r.getMessage() for r in caplog.records if r.name == logs.ACCESS_LOGGER]
    assert any(line.startswith("GET /{path} 200") for line in lines), lines
    assert not any("demo" in line or "secret" in line for line in lines)


# --- no escape ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/%2e%2e/secret.txt",
        "/..%2fsecret.txt",
        "/models/%2e%2e/%2e%2e/%2e%2e/secret.txt",
        "/..%5csecret.txt",
        "/%2e%2e%5c%2e%2e%5csecret.txt",
    ],
)
def test_no_path_leaves_the_site(built: Path, path: str) -> None:
    with client(site=built) as api:
        response = api.get(path)
    assert OUTSIDE not in response.text
    assert response.status_code in {400, 404}


def test_an_absolute_path_to_a_file_is_not_served(built: Path, tmp_path: Path) -> None:
    # On Windows this is /<drive>:/..., which os.path.join would let replace the
    # site's own directory; elsewhere a path from the root.
    secret = (tmp_path / "secret.txt").resolve().as_posix().lstrip("/")
    with client(site=built) as api:
        response = api.get(f"/{secret}")
    assert response.status_code in {400, 404}
    assert OUTSIDE not in response.text


def test_a_link_out_of_the_site_is_not_followed(built: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(OUTSIDE, encoding="utf-8")
    if not _link(outside, built / "linked"):
        pytest.skip("this platform cannot link a directory")  # pragma: no cover
    with client(site=built) as api:
        response = api.get("/linked/secret.txt")
    assert response.status_code == 404
    assert OUTSIDE not in response.text


# --- the guard ----------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/models/demo/model/", "/_astro/app.js"])
@pytest.mark.parametrize(
    "base_url", ["http://evil.example", "http://192.168.1.20:8000"]
)
def test_the_loopback_guard_holds_for_the_site(
    built: Path, base_url: str, path: str
) -> None:
    with client(site=built, base_url=base_url) as api:
        response = api.get(path)
    assert response.status_code == 400
    assert problem(response)["type"].endswith("/host-not-allowed")
    assert "<h1>" not in response.text


@pytest.mark.parametrize("base_url", ["http://localhost:8000", "http://[::1]:8000"])
def test_every_loopback_name_reads_the_site(built: Path, base_url: str) -> None:
    with client(site=built, base_url=base_url) as api:
        assert api.get("/").text == "<h1>home</h1>"


# --- what refuses a site ------------------------------------------------------------


def test_hosted_mode_refuses_a_site(built: Path) -> None:
    with pytest.raises(InputError, match="Cloudflare"):
        create_app(mode="hosted", settings=ServerSettings(workers=0, site=built))


def test_the_settings_take_only_a_path() -> None:
    with pytest.raises(InputError, match="site is a Path"):
        ServerSettings(site="web/dist")  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    ("name", "text", "match"),
    [
        ("_headers", None, "no _headers"),
        ("_headers", "/*\n  X-Content-Type-Options: nosniff\n", "no Content-Security"),
        ("_headers", "https://example.org/*\n  X-A: b\n", "a path from /"),
        ("_headers", "  X-A: b\n", "outside a rule"),
        ("_headers", "/*\n  X-A b\n", "Name: value"),
        ("_redirects", "/a/ https://example.org/ 301\n", "_redirects line 1"),
        ("_redirects", "/a/* /b/ 301\n", "_redirects line 1"),
        ("_redirects", "/a/ /b/ 200\n", "_redirects line 1"),
        ("_redirects", "/a/\n", "_redirects line 1"),
        ("index.html", None, "no index.html"),
    ],
)
def test_a_site_that_cannot_carry_its_policy_is_refused(
    built: Path, name: str, text: str | None, match: str
) -> None:
    if text is None:
        (built / name).unlink()
    else:
        (built / name).write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match=match):
        create_app(settings=ServerSettings(workers=0, site=built))


def test_header_rules_join_detach_and_match_placeholders() -> None:
    rules = site.HeaderRules.parse(
        "# a comment\n\n/*\n  X-A: one\n  X-B: kept\n"
        "/models/:id/\n  x-a: two\n  ! X-B\n"
    )
    assert rules.for_path("/models/demo/") == {"X-A": "one, two"}
    assert rules.for_path("/models/demo/deeper/") == {"X-A": "one", "X-B": "kept"}


def test_a_redirect_without_a_status_is_302() -> None:
    assert site.parse_redirects("# old\n/a /b\n") == {"/a": ("/b", 302)}


# --- serve -------------------------------------------------------------------------


@dataclass
class Served:
    app: FastAPI
    host: str
    port: int


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> list[Served]:
    calls: list[Served] = []

    def record(app: FastAPI, host: str, port: int) -> None:
        calls.append(Served(app, host, port))

    monkeypatch.setattr(serve_command, "run_server", record)
    return calls


def _fake_app_package(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    module = types.ModuleType(site.APP_MODULE)
    module.__spec__ = importlib.machinery.ModuleSpec(site.APP_MODULE, None)
    module.site_path = lambda: directory  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, site.APP_MODULE, module)


def test_serve_mounts_the_installed_site(
    built: Path, served: list[Served], monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_app_package(monkeypatch, built)
    assert site.packaged_site() == built
    outcome = cli("serve", "--workers", "0", "--port", "8123")
    assert outcome.code == 0
    (call,) = served
    assert call.app.state.service.settings.site == built
    assert _last_route(call.app) == "site"
    assert "INFO pyeconomics.server: serving the web app at http://127.0.0.1:8123/" in (
        outcome.stderr
    )
    assert "WARNING" not in outcome.stderr


def test_serve_names_an_ipv6_host_in_brackets(
    built: Path, served: list[Served], monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_app_package(monkeypatch, built)
    outcome = cli("serve", "--host", "::1", "--workers", "0")
    assert outcome.code == 0
    assert served
    assert "serving the web app at http://[::1]:8000/" in outcome.stderr


def test_serve_keeps_the_guard_with_the_site_installed(
    built: Path, served: list[Served], monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_app_package(monkeypatch, built)
    outcome = cli("serve", "--host", "0.0.0.0")  # noqa: S104 # nosec B104 - refused, never bound
    assert outcome.code == 2
    assert "--allow-remote" in outcome.stderr
    assert served == []


def test_serve_without_the_package_logs_the_install_hint(
    served: list[Served], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, site.APP_MODULE, None)
    assert site.packaged_site() is None
    outcome = cli("serve", "--workers", "0")
    assert outcome.code == 0
    (call,) = served
    assert call.app.state.service.settings.site is None
    assert _last_route(call.app) != "site"
    assert outcome.stderr.count(site.INSTALL_HINT) == 1
    assert 'pip install "pyeconomics[app]"' in site.INSTALL_HINT


def test_serve_with_an_unbuilt_package_logs_the_build_hint(
    tmp_path: Path, served: list[Served], monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_app_package(monkeypatch, tmp_path / "site")
    assert site.packaged_site() is None
    outcome = cli("serve", "--workers", "0")
    assert outcome.code == 0
    assert served
    assert outcome.stderr.count(site.BUILD_HINT) == 1


def test_a_site_off_the_file_system_is_not_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = types.ModuleType(site.APP_MODULE)
    module.__spec__ = importlib.machinery.ModuleSpec(site.APP_MODULE, None)
    module.site_path = lambda: os.fspath("not-a-path")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, site.APP_MODULE, module)
    assert site.packaged_site() is None
