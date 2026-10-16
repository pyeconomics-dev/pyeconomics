# docs/_ext/provider_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Generate one reference page per registered data provider, offline, at build time.

Each page comes from the provider's :class:`~pyeconomics.data.ProviderInfo`: its
class, the terms page and the date it was read, the attribution and required
notice, ``llm_use``, the cache policy, how to set its key, its capabilities, its
rate limits, the extra it needs and the hosts it may contact. The build blocks the
network, so nothing here fetches anything; the pages are written to a git-ignored
directory and a stale page is removed. A provider id becomes ``<id>.md`` under
``reference/providers``, and ``index.md`` lists them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pyeconomics.data import ProviderInfo

_ID = re.compile(r"[a-z][a-z0-9_]{0,63}")
_ESCAPED = re.compile(r"([\\`*_{}\[\]<>#|~$])")
_KEYS_GUIDE = "../../data/keys.md"


class Catalog(Protocol):
    """The registry operations used to generate pages."""

    def infos(self) -> tuple[ProviderInfo, ...]:
        """Return every provider's info, sorted by id."""
        ...


def _text(value: str) -> str:
    """Escape Markdown and MyST syntax in text taken from a provider."""
    return _ESCAPED.sub(r"\\\1", " ".join(value.split()))


def _rate_limits(info: ProviderInfo) -> str:
    if not info.rate_limits:
        return "None declared."
    lines = [
        f"- {limit.requests} requests per {limit.per}"
        + (" without a key" if limit.without_key else "")
        for limit in info.rate_limits
    ]
    return "\n".join(lines)


def _key_setup(info: ProviderInfo) -> str:
    kind = info.auth.kind.value
    if kind == "key":
        variable = info.key_variable
        optional = (
            "" if info.auth.required else " It is optional and raises the limits."
        )
        return (
            f"A key is read from the `{variable}` environment variable, the `.env` "
            f"file in the configuration directory or the OS keyring; see the "
            f"[keys guide]({_KEYS_GUIDE}).{optional}"
        )
    if kind == "contact":
        return (
            "No key, but the source requires your contact (a name and an email "
            "address) in the User-Agent: set `PYECONOMICS_SEC_CONTACT` or "
            f"`sec_contact` in `pyeconomics.toml`; see the [keys guide]({_KEYS_GUIDE})."
        )
    return "No key is needed."


def render(info: ProviderInfo) -> str:
    """Return the Markdown page for one provider."""
    terms = info.terms
    extra = (
        f'`pip install "pyeconomics[{info.extra}]"`'
        if info.extra
        else "None (the default install)."
    )
    notice = f"> {_text(terms.notice)}" if terms.notice else "None required."
    capabilities = ", ".join(f"`{c.value}`" for c in info.capabilities)
    platforms = ", ".join(f"`{p.value}`" for p in info.platforms)
    hosts = "\n".join(f"- `{host}`" for host in info.hosts) or "None (a local session)."
    return (
        f"# {_text(info.name)}\n\n"
        f"Provider id: `{info.id}`. "
        f"[{_text(info.name)} home page]({info.homepage}).\n\n"
        "```{list-table}\n"
        ":widths: 30 70\n\n"
        f"* - Licence class\n  - `{terms.licence.value}`\n"
        f"* - Terms\n  - [terms page]({terms.terms_url}), "
        f"read on {terms.checked.isoformat()}\n"
        f"* - Language-model use\n  - `{terms.llm_use.value}`\n"
        f"* - Caching\n  - `{terms.cache.value}`\n"
        f"* - Capabilities\n  - {capabilities}\n"
        f"* - Platforms\n  - {platforms}\n"
        f"* - Extra\n  - {extra}\n"
        "```\n\n"
        "## Attribution\n\n"
        f"> {_text(terms.attribution)}\n\n"
        "## Required notice\n\n"
        f"{notice}\n\n"
        "## Key and contact\n\n"
        f"{_key_setup(info)}\n\n"
        "## Rate limits\n\n"
        f"{_rate_limits(info)}\n\n"
        "## Hosts\n\n"
        f"{hosts}\n"
    )


def _index(infos: tuple[ProviderInfo, ...]) -> str:
    if not infos:
        return (
            "# Data provider reference\n\n"
            "No data provider is registered in this build. The free sources arrive "
            "during the 1.0 alpha; see "
            "[Writing a provider](../../data/writing-a-provider.md) to add one.\n"
        )
    rows = "\n".join(
        f"| [{_text(info.name)}]({info.id}.md) | `{info.id}` | "
        f"`{info.terms.licence.value}` | `{info.auth.kind.value}` |"
        for info in infos
    )
    names = "\n".join(info.id for info in infos)
    return (
        "# Data provider reference\n\n"
        "Each page comes from the registered provider's metadata: its licence class, "
        "terms, attribution, key setup and limits.\n\n"
        "| Source | Id | Licence class | Authentication |\n"
        "|--------|----|---------------|----------------|\n"
        f"{rows}\n\n"
        f"```{{toctree}}\n:hidden:\n:maxdepth: 1\n\n{names}\n```\n"
    )


def check_pages(root: Path, provider_ids: tuple[str, ...]) -> None:
    """Fail on missing, extra or misplaced pages, excluding the index."""
    expected = {Path(f"{provider_id}.md") for provider_id in provider_ids}
    actual = {
        path.relative_to(root) for path in root.rglob("*.md") if path.name != "index.md"
    }
    if actual != expected or len(actual) != len(provider_ids):
        message = (
            f"Provider page count mismatch: expected {len(provider_ids)}, "
            f"got {len(actual)}"
        )
        raise ValueError(message)


def write_pages(root: Path, catalog: Catalog) -> tuple[Path, ...]:
    """Write provider pages and the index; remove stale generated Markdown only.

    ``root`` is the dedicated, ignored generation directory. Ids are validated
    before any filesystem change, so a malformed registry cannot escape it.
    """
    infos = catalog.infos()
    provider_ids = tuple(info.id for info in infos)
    if (
        len(set(provider_ids)) != len(provider_ids)
        or any(not _ID.fullmatch(provider_id) for provider_id in provider_ids)
        or "index" in provider_ids
    ):
        message = "Invalid or duplicate provider ids"
        raise ValueError(message)
    pages = {Path(f"{info.id}.md"): render(info) for info in infos}
    pages[Path("index.md")] = _index(infos)
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.rglob("*.md"):
        if stale.relative_to(root) not in pages:
            stale.unlink()
    for relative, markdown in pages.items():
        (root / relative).write_bytes(markdown.encode("utf-8"))
    check_pages(root, provider_ids)
    return tuple(root / path for path in pages if path.name != "index.md")


def setup(app: Any) -> dict[str, object]:  # noqa: ANN401
    """Install the builder hook; pure functions do not require Sphinx."""
    from sphinx.errors import ExtensionError  # noqa: PLC0415

    from pyeconomics.data import registry  # noqa: PLC0415

    def generate(application: Any) -> None:  # noqa: ANN401
        try:
            registry.validate()
            write_pages(
                Path(application.srcdir) / "reference" / "providers",
                registry.installed(),
            )
        except ValueError as error:
            raise ExtensionError(str(error)) from error

    app.connect("builder-inited", generate)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
