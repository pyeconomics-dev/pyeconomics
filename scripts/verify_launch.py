# scripts/verify_launch.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Check the public 1.0.0 launch, with no token (Phase 5 Step 21).

Every check reads what anyone can read: the public site and API at
https://pyeconomics.dev, its redirect hosts, PyPI, Read the Docs, the MCP
Registry and the MDN HTTP Observatory. It prints one ``PASS`` or ``FAIL`` line
per check and exits 1 when any fails. Step 21's Deployed & verified bullet is
the list; Step 22's ``verify-phase05.sh --live`` reruns it.

A ``FAIL`` in ``headers`` or ``observatory`` means the public site's security
headers are wrong: restore the Access application while it is fixed
(``docs/operations/production.md`` section 5, "Rollback").

Some checks need the maintainer's machine:

- ``install``, ``app`` and ``mcp-local`` make clean environments with ``uv``
  (Python 3.12 and 3.15 must be installable) and install from PyPI;
- ``mcp-local`` and ``mcp-hosted`` drive the pinned MCP Inspector in
  ``tools/node`` (``npm ci --ignore-scripts`` first), and compare its answers
  with this checkout's Python API, so run the script with ``uv run`` at the
  tag;
- ``zap``, ``release`` and ``repository`` read GitHub through ``gh``;
- ``origin`` finds the Cloud Run origin with ``gcloud``, unless ``--origin``
  names it.

No check sends a credential: an Access header, a key or a token never leaves
this machine, and nothing this script prints holds one.

    uv run --no-sync python -I scripts/verify_launch.py --tag v1.0.0
    uv run --no-sync python -I scripts/verify_launch.py --only headers,indexing
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import socket
import subprocess  # nosec B404 # runs uv, git, gh, gcloud and the Inspector with fixed arguments
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET  # nosec B405 # parses the site's own sitemap, never untrusted XML
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

ROOT: Final = Path(__file__).resolve().parents[1]
SITE: Final = "https://pyeconomics.dev"
USER_AGENT: Final = "pyeconomics-verify-launch/1.0"
TIMEOUT: Final = 60
#: The hosts the cutover redirects to the canonical site (production.md section 10).
REDIRECT_HOSTS: Final = (
    "www.pyeconomics.dev",
    "pyeconomics.com",
    "www.pyeconomics.com",
    "pyeconomics.org",
    "www.pyeconomics.org",
    "pyeconomics.io",
    "www.pyeconomics.io",
)
#: A concept the hosted site serves from its snapshot, and a library-only one.
HOSTED_CONCEPT: Final = "us.unemployment.rate"
LIBRARY_ONLY_CONCEPT: Final = "factors.ff3.us.monthly"
#: The snapshot job runs daily at 23:30 UTC; a read older than this missed a run.
SNAPSHOT_HOURS: Final = 26
#: A model page's address, https://pyeconomics.dev/models/<domain>/<slug>/.
MODEL_PAGE_SLASHES: Final = 6
OBSERVATORY: Final = "https://observatory-api.mdn.mozilla.net/api/v2/scan"
REGISTRY: Final = (
    "https://registry.modelcontextprotocol.io/v0.1/servers/"
    "io.github.pyeconomics-dev%2Fpyeconomics/versions/"
)
RTD_PROJECT: Final = "https://app.readthedocs.org/api/v3/projects/pyeconomics/"
REPOSITORY: Final = "pyeconomics-dev/pyeconomics"
#: A data-free run whose GET form the edge may cache (production.md section 5).
CACHED_RUN: Final = (
    "/v1/models/foundations.time_value/run?inputs="
    "eyJjYWxjdWxhdGlvbiI6ImZ1dHVyZV92YWx1ZSIsInByZXNlbnRfdmFsdWUiOjEwMDAuMCwicmF0ZSI6"
    "MC4wNSwicGVyaW9kcyI6MTB9"
)


class CheckFailedError(Exception):
    """A check found what it must not: its message says what."""


@dataclass(frozen=True)
class Reply:
    """An HTTP answer: status, headers (lower-case names) and body."""

    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:  # noqa: ANN401 - a parsed JSON document
        """Parse the body as JSON."""
        return json.loads(self.body)

    def text(self) -> str:
        """Decode the body as UTF-8."""
        return self.body.decode("utf-8", "replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def request(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    follow: bool = True,
) -> Reply:
    """Send one HTTPS request and return its answer, whatever its status."""
    if not url.startswith(("https://", "http://127.0.0.1:")):
        message = f"refusing a URL that is not https: {url}"
        raise CheckFailedError(message)
    sent = urllib.request.Request(url, data=body, method=method)  # noqa: S310 - https or loopback, checked above
    sent.add_header("User-Agent", USER_AGENT)
    for name, value in (headers or {}).items():
        sent.add_header(name, value)
    opener = (
        urllib.request.build_opener()
        if follow
        else urllib.request.build_opener(_NoRedirect)
    )
    try:
        with opener.open(sent, timeout=TIMEOUT) as answer:
            return Reply(
                answer.status,
                {k.lower(): v for k, v in answer.headers.items()},
                answer.read(),
            )
    except urllib.error.HTTPError as error:
        return Reply(
            error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()
        )


def need(condition: object, message: str) -> None:
    """Fail the check with ``message`` unless ``condition`` holds."""
    if not condition:
        raise CheckFailedError(message)


def run(*command: str, cwd: Path | None = None, timeout: int = 1800) -> str:
    """Run a command and return its standard output; fail on a non-zero exit."""
    done = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments, no shell
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if done.returncode != 0:
        tail = (done.stderr or done.stdout).strip().splitlines()[-5:]
        message = f"{command[0]} exited {done.returncode}: " + " | ".join(tail)
        raise CheckFailedError(message)
    return done.stdout


def tool(name: str) -> str:
    """Return the full path of a program on PATH, or fail."""
    path = shutil.which(name)
    need(path, f"{name} is not on PATH")
    return str(path)


# --- the checks -------------------------------------------------------------


@dataclass(frozen=True)
class Context:
    """What every check may read."""

    tag: str
    version: str
    sha: str
    origin: str | None
    zap_run: str | None


def check_version(context: Context) -> str:
    """Check that /version and /version.json name the tag's commit, with no token."""
    api = request(f"{SITE}/version", follow=False)
    need(api.status == HTTPStatus.OK, f"/version answered {api.status}")
    payload = api.json()
    need(
        payload.get("git_sha") == context.sha,
        f"/version names {payload.get('git_sha')}",
    )
    need(
        payload.get("pyeconomics") == context.version,
        f"/version is {payload.get('pyeconomics')}",
    )
    need(payload.get("mode") == "hosted", "the API is not in hosted mode")
    site = request(f"{SITE}/version.json", follow=False)
    need(site.status == HTTPStatus.OK, f"/version.json answered {site.status}")
    need(
        site.json() == {"pyeconomics": context.version, "git_sha": context.sha},
        f"/version.json is {site.text()[:200]}",
    )
    home = request(f"{SITE}/", follow=False)
    need(
        home.status == HTTPStatus.OK,
        f"/ answered {home.status} with no token: is Access still on?",
    )
    need(
        "cf_authorization" not in home.headers.get("set-cookie", "").lower(),
        "Access set its cookie",
    )
    return f"{context.version} at {context.sha[:12]}, served to anyone"


def check_headers(_context: Context) -> str:
    """Check every security header on pages and the API, and that none says noindex."""
    for path in ("/", "/models/foundations/time-value/"):
        reply = request(SITE + path)
        need(reply.status == HTTPStatus.OK, f"{path} answered {reply.status}")
        headers = reply.headers
        policy = headers.get("content-security-policy", "")
        need(policy, f"{path} has no Content-Security-Policy")
        need(
            "'unsafe-inline'" not in policy and "'unsafe-eval'" not in policy,
            f"{path}'s policy is unsafe",
        )
        need(
            "frame-ancestors 'none'" in policy,
            f"{path}'s policy lacks frame-ancestors 'none'",
        )
        hsts = headers.get("strict-transport-security", "")
        need(
            "max-age=63072000" in hsts
            and "includesubdomains" in hsts.lower()
            and "preload" in hsts,
            f"{path}'s HSTS is {hsts!r}",
        )
        need(
            headers.get("x-content-type-options") == "nosniff", f"{path} lacks nosniff"
        )
        need(
            headers.get("referrer-policy") == "strict-origin-when-cross-origin",
            f"{path}'s Referrer-Policy",
        )
        need(headers.get("permissions-policy"), f"{path} has no Permissions-Policy")
        need(
            headers.get("cross-origin-opener-policy") == "same-origin", f"{path}'s COOP"
        )
        need(
            "noindex" not in headers.get("x-robots-tag", ""),
            f"{path} still says noindex",
        )
    api = request(f"{SITE}/version")
    need(
        "max-age=63072000" in api.headers.get("strict-transport-security", ""),
        "the API lacks HSTS",
    )
    need(
        api.headers.get("x-content-type-options") == "nosniff", "the API lacks nosniff"
    )
    return "CSP with no unsafe source, frame-ancestors, HSTS preload, nosniff, COOP"


def check_observatory(_context: Context) -> str:
    """Check that the MDN HTTP Observatory grades the site A or better."""
    query = urllib.parse.urlencode({"host": urllib.parse.urlsplit(SITE).hostname})
    reply = request(f"{OBSERVATORY}?{query}", method="POST", body=b"")
    need(reply.status == HTTPStatus.OK, f"the Observatory answered {reply.status}")
    scan = reply.json()
    need(not scan.get("error"), f"the Observatory's scan failed: {scan.get('error')}")
    grade = scan.get("grade")
    need(grade in {"A+", "A"}, f"graded {grade} ({scan.get('score')})")
    passed, total = scan.get("tests_passed"), scan.get("tests_quantity")
    return f"grade {grade}, score {scan.get('score')}, {passed}/{total} tests"


def check_indexing(_context: Context) -> str:
    """Check that robots.txt allows indexing and the sitemap lists every page."""
    robots = request(f"{SITE}/robots.txt")
    need(robots.status == HTTPStatus.OK, f"robots.txt answered {robots.status}")
    lines = [line.strip().lower() for line in robots.text().splitlines()]
    need("disallow: /" not in lines, "robots.txt disallows the site")
    need(
        any(line.startswith("sitemap:") for line in lines),
        "robots.txt names no sitemap",
    )
    found: set[str] = set()
    pending = [
        line.split(":", 1)[1].strip()
        for line in robots.text().splitlines()
        if line.lower().startswith("sitemap:")
    ]
    while pending:
        url = pending.pop()
        need(url.startswith(SITE + "/"), f"a sitemap off the site: {url}")
        tree = ET.fromstring(request(url).body)  # noqa: S314 # nosec B314 - the site's own sitemap
        for loc in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            target = (loc.text or "").strip()
            if target.endswith(".xml"):
                pending.append(target)
            else:
                found.add(target)
    released = json.loads((ROOT / "web" / "released-pages.json").read_bytes())
    pages = released if isinstance(released, list) else released.get("pages", released)
    expected = {SITE + page for page in pages}
    missing = sorted(expected - found)
    need(
        not missing,
        f"{len(missing)} released pages missing from the sitemap, e.g. {missing[:3]}",
    )
    models = sum(
        1
        for page in expected
        if page.startswith(f"{SITE}/models/") and page.count("/") == MODEL_PAGE_SLASHES
    )
    return f"robots allows; the sitemap lists {len(expected)} pages ({models} models)"


def check_redirects(_context: Context) -> str:
    """Check that every other domain answers 301 to the canonical page."""
    for host in REDIRECT_HOSTS:
        reply = request(f"https://{host}/models/", follow=False)
        need(
            reply.status == HTTPStatus.MOVED_PERMANENTLY,
            f"{host} answered {reply.status}",
        )
        location = reply.headers.get("location")
        need(location == f"{SITE}/models/", f"{host} redirects to {location}")
    return f"{len(REDIRECT_HOSTS)} hosts answer 301 to {SITE}/models/"


def _first_model_per_domain() -> Iterator[tuple[str, dict[str, Any]]]:
    import pyeconomics  # noqa: PLC0415 - only the checks that run a model need it

    seen: set[str] = set()
    for model_id in sorted(pyeconomics.registry.ids()):
        domain = model_id.split(".", 1)[0]
        model = pyeconomics.registry.get(model_id)
        if domain in seen or not model.spec.examples:
            continue
        seen.add(domain)
        yield model_id, dict(model.spec.examples[0].inputs)


def check_models(_context: Context) -> str:
    """Run one model per domain, and download a series as CSV with its attribution."""
    count = 0
    for model_id, inputs in _first_model_per_domain():
        reply = request(
            f"{SITE}/v1/models/{model_id}/run",
            method="POST",
            body=json.dumps(inputs).encode(),
            headers={"Content-Type": "application/json"},
        )
        need(
            reply.status == HTTPStatus.OK,
            f"{model_id} answered {reply.status}: {reply.text()[:200]}",
        )
        need(
            reply.json().get("model_id") == model_id,
            f"{model_id} answered another model",
        )
        count += 1
    need(count >= 13, f"only {count} domains ran")  # noqa: PLR2004 - the thirteen domains
    csv = request(f"{SITE}/v1/series/{HOSTED_CONCEPT}?start=2024-01-01&format=csv")
    need(csv.status == HTTPStatus.OK, f"the CSV download answered {csv.status}")
    attributions = [
        line for line in csv.text().splitlines() if line.startswith("# attribution:")
    ]
    need(attributions, "the CSV carries no attribution")
    first = attributions[0].removeprefix("# attribution:").strip()[:60]
    return f"{count} domains ran; {HOSTED_CONCEPT}.csv carries '{first}'"


def retrieved_times(document: object) -> Iterator[str]:
    """Yield every `retrieved_at` time a JSON document holds, wherever it sits."""
    if isinstance(document, dict):
        for key, value in document.items():
            if key == "retrieved_at" and isinstance(value, str):
                yield value
            else:
                yield from retrieved_times(value)
    elif isinstance(document, list):
        for item in document:
            yield from retrieved_times(item)


def check_snapshot(_context: Context) -> str:
    """Check the snapshot is fresh (the heartbeat's proof); library-only is refused."""
    reply = request(f"{SITE}/v1/series/{HOSTED_CONCEPT}?start=2025-01-01")
    need(reply.status == HTTPStatus.OK, f"{HOSTED_CONCEPT} answered {reply.status}")
    stamps = sorted(retrieved_times(reply.json()))
    need(stamps, "the series records no retrieval time")
    newest = stamps[-1]
    read = time.mktime(time.strptime(newest[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    age = (time.time() - read) / 3600
    need(
        age < SNAPSHOT_HOURS,
        f"the snapshot was read {age:.1f} hours ago ({newest}): a run was missed",
    )
    refused = request(f"{SITE}/v1/series/{LIBRARY_ONLY_CONCEPT}?start=2024-01-01")
    need(
        refused.status == HTTPStatus.FORBIDDEN,
        f"library-only {LIBRARY_ONLY_CONCEPT} answered {refused.status}",
    )
    return f"read {age:.1f} h ago ({newest}); library-only data answers 403"


def check_edge_cache(_context: Context) -> str:
    """Check the edge answers a repeated GET run, and never a POST or a problem."""
    request(SITE + CACHED_RUN)
    second = request(SITE + CACHED_RUN)
    need(second.status == HTTPStatus.OK, f"the GET run answered {second.status}")
    hit = second.headers.get("cf-cache-status") == "HIT" or "age" in second.headers
    need(
        hit,
        f"the second GET run was not cached ({second.headers.get('cf-cache-status')})",
    )
    post = request(
        f"{SITE}/v1/models/foundations.time_value/run",
        method="POST",
        body=b'{"calculation":"future_value","present_value":1000.0,"rate":0.05,"periods":10}',
        headers={"Content-Type": "application/json"},
    )
    problem = request(f"{SITE}/v1/models/foundations.time_value/run?inputs=e30")
    for name, reply in (("the POST run", post), ("a problem", problem)):
        need(
            reply.headers.get("cf-cache-status") != "HIT"
            and "age" not in reply.headers,
            f"{name} was cached",
        )
        need(
            "no-store" in reply.headers.get("cache-control", ""),
            f"{name} is not no-store",
        )
    status, age = second.headers.get("cf-cache-status"), second.headers.get("age")
    return f"second GET {status}, age {age}; POST and problem no-store"


def check_origin(context: Context) -> str:
    """Check the Cloud Run origin still refuses a request with no edge credential."""
    origin = context.origin
    if origin is None:
        origin = run(
            tool("gcloud"),
            "run",
            "services",
            "describe",
            "pyeconomics-api",
            "--project=pyeconomics-production",
            "--region=us-central1",
            "--format=value(status.url)",
        ).strip()
    need(
        origin.startswith("https://") and origin.endswith(".run.app"),
        "no Cloud Run origin",
    )
    reply = request(f"{origin}/v1/models")
    need(
        reply.status == HTTPStatus.FORBIDDEN,
        f"the origin answered {reply.status} without the credential",
    )
    return "the origin answers 403 without the edge credential"


def check_docs(context: Context) -> str:
    """Check Read the Docs: stable is the release, 0.2.6 stays, defaults are set."""
    options = request(
        "https://docs.pyeconomics.dev/en/stable/_static/documentation_options.js"
    )
    need(
        f"VERSION: '{context.version}'" in options.text(),
        "stable does not serve the release",
    )
    legacy = request(
        "https://docs.pyeconomics.dev/en/v0.2.6/_static/documentation_options.js"
    )
    need("VERSION: '0.2.6'" in legacy.text(), "the 0.2.6 documentation is gone")
    project = request(RTD_PROJECT, headers={"User-Agent": "Mozilla/5.0"}).json()
    need(
        project.get("default_version") == "stable",
        f"default version {project.get('default_version')}",
    )
    need(
        project.get("default_branch") == "main",
        f"default branch {project.get('default_branch')}",
    )
    home = request("https://docs.pyeconomics.dev/")
    need(
        home.status == HTTPStatus.OK and "1.0 preview" not in home.text(),
        "the default page is not 1.0",
    )
    return f"stable is {context.version}, v0.2.6 kept, defaults stable and main"


def check_pypi(context: Context) -> str:
    """Check both distributions are newest on PyPI, each file with a provenance."""
    for project in ("pyeconomics", "pyeconomics-app"):
        data = request(f"https://pypi.org/pypi/{project}/json").json()
        need(
            data["info"]["version"] == context.version,
            f"{project}'s newest is {data['info']['version']}",
        )
        files = request(
            f"https://pypi.org/pypi/{project}/{context.version}/json"
        ).json()["urls"]
        need(files, f"{project} {context.version} has no files")
        for item in files:
            name = urllib.parse.quote(item["filename"], safe="")
            provenance = request(
                f"https://pypi.org/integrity/{project}/{context.version}/{name}/provenance"
            )
            need(
                provenance.status == HTTPStatus.OK
                and provenance.json().get("attestation_bundles"),
                f"{item['filename']} has no provenance",
            )
    return f"both distributions' newest is {context.version}, every file attested"


@contextlib.contextmanager
def scratch() -> Iterator[Path]:
    """Yield a temporary directory, removed afterwards."""
    with tempfile.TemporaryDirectory(prefix="pyeconomics-launch-") as path:
        yield Path(path)


def _venv(where: Path, python: str) -> Path:
    run(tool("uv"), "venv", "--no-config", "--seed", "--python", python, str(where))
    scripts = where / ("Scripts" if os.name == "nt" else "bin")
    return scripts / ("python.exe" if os.name == "nt" else "python")


def check_install(context: Context) -> str:
    """Install plainly on Python 3.12 and 3.15: the release, passing the smoke test."""
    with scratch() as temp:
        smoke = temp / "smoke.py"
        smoke.write_bytes(
            run(
                tool("git"), "show", f"{context.tag}:scripts/smoke.py", cwd=ROOT
            ).encode()
        )
        for python in ("3.12", "3.15"):
            interpreter = _venv(temp / f"venv{python}", python)
            run(
                str(interpreter),
                "-m",
                "pip",
                "--isolated",
                "install",
                "--index-url",
                "https://pypi.org/simple/",
                "pyeconomics",
            )
            installed = run(
                str(interpreter),
                "-c",
                "import pyeconomics; print(pyeconomics.__version__)",
                cwd=temp,
            ).strip()
            need(installed == context.version, f"Python {python} installed {installed}")
            run(str(interpreter), str(smoke), "--all", "--min-domains", "13", cwd=temp)
    return f"Python 3.12 and 3.15 install {context.version} and pass smoke.py"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def check_app(context: Context) -> str:
    """Check pyeconomics[app] serves the pages locally, a library-only source live."""
    with scratch() as temp:
        interpreter = _venv(temp / "venv", "3.14")
        run(
            str(interpreter),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--index-url",
            "https://pypi.org/simple/",
            f"pyeconomics[app]=={context.version}",
        )
        port = _free_port()
        base = f"http://127.0.0.1:{port}"
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.endswith("_API_KEY") and not k.startswith("PYECONOMICS_")
        }
        env.update(
            PYECONOMICS_CONFIG_DIR=str(temp / "config"),
            PYECONOMICS_CACHE_DIR=str(temp / "cache"),
        )
        server = subprocess.Popen(  # noqa: S603 # nosec B603 - the installed command
            [
                str(
                    interpreter.parent
                    / ("pyeconomics.exe" if os.name == "nt" else "pyeconomics")
                ),
                "serve",
                "--port",
                str(port),
            ],
            cwd=temp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(120):
                with contextlib.suppress(OSError, CheckFailedError):
                    if request(f"{base}/version").status == HTTPStatus.OK:
                        break
                time.sleep(1)
            home = request(f"{base}/")
            need(
                home.status == HTTPStatus.OK
                and home.headers.get("content-security-policy"),
                "/ is not the app",
            )
            need(
                "noindex" in home.headers.get("x-robots-tag", ""),
                "the local app is not noindex",
            )
            page = request(f"{base}/models/foundations/time-value/")
            need(page.status == HTTPStatus.OK, f"a model page answered {page.status}")
            series = request(
                f"{base}/v1/series/{LIBRARY_ONLY_CONCEPT}?start=2024-01-01"
            )
            need(
                series.status == HTTPStatus.OK,
                f"library-only {LIBRARY_ONLY_CONCEPT} answered {series.status} locally",
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=30)
    return f"/ and a model page served; library-only {LIBRARY_ONLY_CONCEPT} live"


def _inspector(*target: str) -> None:
    node = ROOT / "tools" / "node"
    need(
        (node / "node_modules").is_dir(),
        "tools/node has no node_modules: run npm ci --ignore-scripts there",
    )
    run(
        sys.executable,
        "-I",
        str(ROOT / "scripts" / "mcp" / "inspector_checks.py"),
        str(node),
        *target,
        cwd=ROOT,
    )


def check_mcp_local(context: Context) -> str:
    """Check the released MCP server, run by uvx, passes the Inspector."""
    with scratch() as temp:
        # A wrapper without flags: the Inspector's CLI would read uvx's own as its.
        package = f"pyeconomics[mcp]=={context.version}"
        command = f'uvx --no-config --python 3.14 --from "{package}" pyeconomics mcp'
        if os.name == "nt":
            wrapper = temp / "uvx-mcp.cmd"
            wrapper.write_bytes(f"@echo off\r\n{command}\r\n".encode())
        else:
            wrapper = temp / "uvx-mcp.sh"
            wrapper.write_bytes(f"#!/bin/sh\nexec {command}\n".encode())
            wrapper.chmod(0o700)
        # Warm uvx's cache first: the Inspector waits 15 s for a server (#393).
        run(
            tool("uvx"),
            "--no-config",
            "--python",
            "3.14",
            "--from",
            f"pyeconomics[mcp]=={context.version}",
            "pyeconomics",
            "--version",
        )
        _inspector(str(wrapper))
    return f"uvx pyeconomics[mcp]=={context.version} passes the Inspector"


def check_mcp_hosted(_context: Context) -> str:
    """Check the hosted MCP endpoint passes the Inspector, with no token."""
    _inspector(f"{SITE}/mcp")
    return f"{SITE}/mcp passes the Inspector"


def check_registry(context: Context) -> str:
    """Check the MCP Registry lists the release with the package and the remote."""
    entry = request(REGISTRY + context.version).json()
    server = entry.get("server", entry)
    need(
        server.get("version") == context.version,
        f"the registry lists {server.get('version')}",
    )
    remotes = server.get("remotes") or []
    need(
        remotes == [{"type": "streamable-http", "url": f"{SITE}/mcp"}],
        f"remotes {remotes}",
    )
    meta = entry.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
    need(meta.get("isLatest", True), "the release is not the registry's latest")
    return f"{context.version}, latest, with the remote {SITE}/mcp"


def check_parity(_context: Context) -> str:
    """Check the deployed API answers each domain's golden case as this API does."""
    run(
        sys.executable,
        "-I",
        str(ROOT / "scripts" / "parity" / "check_deployed.py"),
        str(ROOT / "tests" / "golden"),
        SITE,
        cwd=ROOT,
    )
    return "one golden case per domain matches through the public site"


def check_zap(context: Context) -> str:
    """Check the ZAP baseline scan of public production found no High alert."""
    gh = tool("gh")
    run_id = context.zap_run
    if run_id is None:
        listed = json.loads(
            run(
                gh,
                "run",
                "list",
                "-R",
                REPOSITORY,
                "--workflow",
                "zap-baseline.yml",
                "--limit",
                "20",
                "--json",
                "databaseId",
            )
        )
        for item in listed:
            jobs = json.loads(
                run(
                    gh,
                    "run",
                    "view",
                    str(item["databaseId"]),
                    "-R",
                    REPOSITORY,
                    "--json",
                    "jobs",
                )
            )["jobs"]
            if any(
                "production" in job["name"] and job["conclusion"] != "skipped"
                for job in jobs
            ):
                run_id = str(item["databaseId"])
                break
    need(run_id, "no zap-baseline run scanned production")
    jobs = json.loads(
        run(
            gh, "run", "view", str(run_id), "-R", REPOSITORY, "--json", "jobs,createdAt"
        )
    )
    production = [job for job in jobs["jobs"] if "production" in job["name"]]
    need(
        production and all(job["conclusion"] == "success" for job in production),
        f"run {run_id} did not pass",
    )
    return f"run {run_id} ({jobs['createdAt']}) passed with no High alert"


def check_release(context: Context) -> str:
    """Check the GitHub release is published, final and the latest."""
    gh = tool("gh")
    release = json.loads(
        run(
            gh,
            "release",
            "view",
            context.tag,
            "-R",
            REPOSITORY,
            "--json",
            "isDraft,isPrerelease,tagName",
        )
    )
    need(
        not release["isDraft"] and not release["isPrerelease"],
        "the release is a draft or a pre-release",
    )
    latest = json.loads(run(gh, "api", f"repos/{REPOSITORY}/releases/latest"))
    need(
        latest.get("tag_name") == context.tag,
        f"the latest release is {latest.get('tag_name')}",
    )
    return f"{context.tag} is published and the latest"


def check_repository(_context: Context) -> str:
    """Check the homepage is the site, and legacy/0.2.x is locked."""
    gh = tool("gh")
    homepage = run(
        gh, "repo", "view", REPOSITORY, "--json", "homepageUrl", "--jq", ".homepageUrl"
    ).strip()
    need(homepage.rstrip("/") == SITE, f"the homepage is {homepage!r}")
    locked = run(
        gh,
        "api",
        f"repos/{REPOSITORY}/branches/legacy%2F0.2.x/protection",
        "--jq",
        ".lock_branch.enabled",
    ).strip()
    need(locked == "true", "legacy/0.2.x is not locked")
    return f"homepage {SITE}; legacy/0.2.x locked"


CHECKS: Final[dict[str, Callable[[Context], str]]] = {
    "version": check_version,
    "headers": check_headers,
    "observatory": check_observatory,
    "indexing": check_indexing,
    "redirects": check_redirects,
    "models": check_models,
    "snapshot": check_snapshot,
    "edge-cache": check_edge_cache,
    "origin": check_origin,
    "docs": check_docs,
    "pypi": check_pypi,
    "install": check_install,
    "app": check_app,
    "mcp-local": check_mcp_local,
    "mcp-hosted": check_mcp_hosted,
    "registry": check_registry,
    "parity": check_parity,
    "zap": check_zap,
    "release": check_release,
    "repository": check_repository,
}


def main(argv: list[str] | None = None) -> int:
    """Run the checks and print one line each; exit 1 if any fails."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tag", default="v1.0.0", help="the release tag (default v1.0.0)"
    )
    parser.add_argument("--only", help="comma-separated checks to run")
    parser.add_argument("--skip", help="comma-separated checks to leave out")
    parser.add_argument(
        "--origin", help="the Cloud Run origin URL (default: ask gcloud)"
    )
    parser.add_argument(
        "--zap-run",
        help="the zap-baseline.yml run to read (default: the newest of production)",
    )
    args = parser.parse_args(argv)
    chosen = list(CHECKS)
    if args.only:
        chosen = [name for name in args.only.split(",") if name]
    if args.skip:
        chosen = [name for name in chosen if name not in set(args.skip.split(","))]
    unknown = [name for name in chosen if name not in CHECKS]
    if unknown:
        parser.error(f"unknown checks: {', '.join(unknown)}")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag):
        parser.error(f"{args.tag} is not a final release tag")
    try:
        sha = run(tool("git"), "rev-parse", f"{args.tag}^{{commit}}", cwd=ROOT).strip()
    except CheckFailedError:
        parser.error(f"{args.tag} is not a tag in this clone: git fetch --tags first")
    context = Context(args.tag, args.tag[1:], sha, args.origin, args.zap_run)
    failed = 0
    for name in chosen:
        try:
            detail = CHECKS[name](context)
        except (
            CheckFailedError,
            OSError,
            KeyError,
            ValueError,
            subprocess.TimeoutExpired,
        ) as error:
            failed += 1
            sys.stdout.write(f"FAIL  {name}: {error}\n")
        else:
            sys.stdout.write(f"PASS  {name}: {detail}\n")
        sys.stdout.flush()
    sys.stdout.write(f"{len(chosen) - failed} passed, {failed} failed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
