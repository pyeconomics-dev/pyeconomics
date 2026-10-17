# src/pyeconomics/data/transport/sdmx.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""SDMX's requests session, confined to the normal transport and safe XML reader.

There is no second network stack or response cache. The adapter hands each
prepared request to the caller's transport, including cassette transports.
That transport owns TLS (the OS trust store), timeouts, limits and redirects.
"""

from __future__ import annotations

import gzip
import io
import logging
from contextvars import ContextVar
from itertools import chain
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qsl, urlsplit

from pyeconomics.core._optional import import_optional
from pyeconomics.data import redaction
from pyeconomics.data.errors import ResponseError, TransportError
from pyeconomics.data.transport.base import Request, Response, check_host
from pyeconomics.data.transport.cassette import synthetic_value

if TYPE_CHECKING:
    from pyeconomics.data.providers.base import ProviderInfo
    from pyeconomics.data.transport.base import Transport

_PARSING: ContextVar[bool] = ContextVar("sdmx_parsing", default=False)


class _Diagnostics(logging.Filter):
    """Suppress third-party parser diagnostics in this parsing context only."""

    def filter(self, record: logging.LogRecord) -> bool:
        del record
        return not _PARSING.get()


_DIAGNOSTICS = _Diagnostics()
_MAX_XML_BYTES = 64_000_000
_FRAME_ATTRIBUTES = frozenset(
    {
        "UNIT",
        "UNIT_MEASURE",
        "UNIT_MULT",
        "TITLE",
        "TITLE_COMPL",
        "OBS_STATUS",
        "OBS_CONF",
        "COPYRIGHT",
        "LICENSE",
        "LICENCE",
        "RESTRICTIONS",
    }
)


def send(info: ProviderInfo, request: Request, transport: Transport) -> Response:
    """Send through an uncached sdmx1 Client session with a confined adapter."""
    requests = import_optional("requests", extra="sdmx")
    sdmx = import_optional("sdmx", extra="sdmx")

    class Adapter(requests.adapters.BaseAdapter):  # type: ignore[name-defined, misc]  # lazy optional requests base
        def send(self, prepared: Any, **kwargs: Any) -> Any:  # noqa: ANN401, ARG002 - lazy optional sdmx1 and lxml APIs are untyped; provider or adapter protocol parameter
            parts = urlsplit(prepared.url)
            if (
                parts.scheme != "https"
                or parts.username
                or parts.password
                or parts.port
                or parts.fragment
            ):
                msg = "SDMX refused a non-provider address"
                raise TransportError(msg, provider=info.id)
            built = Request(
                host=parts.hostname or "",
                path=parts.path,
                params=tuple(parse_qsl(parts.query, keep_blank_values=True)),
                headers=request.headers,
                series=request.series,
            )
            check_host(info, built)
            response = transport.send(info, built)
            result = requests.Response()
            result.status_code = response.status
            result._content = response.body  # noqa: SLF001 - requests adapter must populate the Response content buffer
            result.headers.update(dict(response.headers))
            result.request = prepared
            result.provider_response = response
            return result

        def close(self) -> None:
            pass

    # Plain requests.Session cannot acquire requests-cache behaviour, even
    # if the caller installed sdmx1[cache]. No default adapter remains.
    with requests.Session() as session:
        session.trust_env = False
        session.adapters.clear()
        adapter = Adapter()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        client = sdmx.Client(session=session)
        prepared = client.session.prepare_request(
            requests.Request(
                "GET",
                f"https://{request.host}{request.path}",
                params=request.params,
                headers=dict(request.headers),
            )
        )
        result = redaction.call_scrubbed(
            lambda: client.session.send(prepared, allow_redirects=False),
            lambda message: TransportError(message, provider=info.id),
        )
        return cast("Response", result.provider_response)


def xml_body(body: bytes, provider: str) -> bytes:
    """Bound decompression of Eurostat's gzip bodies, even without an HTTP header."""
    if body.startswith(b"\x1f\x8b"):
        body = redaction.call_scrubbed(
            lambda: _read_gzip(body),
            lambda _: ResponseError("source sent invalid gzip", provider=provider),
        )
    if len(body) > _MAX_XML_BYTES:
        msg = "SDMX XML exceeds its decompressed size limit"
        raise ResponseError(msg, provider=provider)
    return body


def _read_gzip(body: bytes) -> bytes:
    """Read at most one byte beyond the decompressed response cap."""
    with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
        return stream.read(_MAX_XML_BYTES + 1)


def read_xml(body: bytes, provider: str, *, structure: Any = None) -> Any:  # noqa: ANN401 - lazy optional sdmx1 and lxml APIs are untyped
    """Read SDMX-ML with entities, DTD loading and network access disabled.

    sdmx1's default XML dispatcher constructs its own parser. Select its
    versioned reader and supply our hardened event iterator instead.
    """
    body = xml_body(body, provider)
    import_optional("sdmx", extra="sdmx")
    etree = import_optional("lxml.etree", extra="sdmx")
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        msg = "SDMX refuses DTDs and entities"
        raise ResponseError(msg, provider=provider)

    def convert() -> Any:  # noqa: ANN401 - lazy optional sdmx1 and lxml APIs are untyped
        events = etree.iterparse(
            io.BytesIO(body),
            events=("start", "end"),
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
        )
        first = next(events)
        namespaces = tuple(first[1].nsmap.values())
        if any("v3_0" in value for value in namespaces if value):
            reader = import_optional("sdmx.reader.xml.v30", extra="sdmx")
        else:
            reader = import_optional("sdmx.reader.xml.v21", extra="sdmx")

        class QuietReader(reader.Reader):  # type: ignore[name-defined, misc]  # lazy optional parser
            def _dump(self) -> None:
                # sdmx1's error handler calls _dump before printing source XML.
                # Abort there so neither its stack nor its body reaches stdout.
                msg = "source sent invalid SDMX-ML"
                raise ResponseError(msg, provider=provider)

        # XMLEventReader.__init_subclass__ resets the parser dispatch table.
        QuietReader.parser = reader.Reader.parser
        logging.getLogger(reader.__name__).addFilter(_DIAGNOSTICS)
        token = _PARSING.set(True)
        try:
            return QuietReader().convert(
                None,
                structure=structure,
                _events=chain((first,), events),
            )
        finally:
            _PARSING.reset(token)

    return redaction.call_scrubbed(
        convert,
        lambda _: ResponseError("source sent invalid SDMX-ML", provider=provider),
    )


def xml_tree(body: bytes, provider: str) -> Any:  # noqa: ANN401 - lazy optional sdmx1 and lxml APIs are untyped
    """Parse an XML tree for bounded recording transformations, without entities."""
    body = xml_body(body, provider)
    etree = import_optional("lxml.etree", extra="sdmx")
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        msg = "SDMX refuses DTDs and entities"
        raise ResponseError(msg, provider=provider)
    return redaction.call_scrubbed(
        lambda: etree.fromstring(
            body,
            parser=etree.XMLParser(
                resolve_entities=False, no_network=True, load_dtd=False
            ),
        ),
        lambda _: ResponseError("source sent invalid XML", provider=provider),
    )


def synthetic_xml(body: bytes, seed: str, provider: str) -> bytes:
    """Replace every generic or structure-specific SDMX observation value."""
    if not body.strip():
        return body
    etree = import_optional("lxml.etree", extra="sdmx")
    root = xml_tree(body, provider)
    for index, node in enumerate(root.iter()):
        local = etree.QName(node).localname
        field = "value" if local == "ObsValue" else "OBS_VALUE"
        if node.get(field) is not None and node.get(field) not in {"NaN", "nan", ""}:
            node.set(field, str(synthetic_value(seed, index)))
    return cast("bytes", etree.tostring(root, encoding="UTF-8", xml_declaration=True))


def flows(body: bytes, provider: str) -> tuple[tuple[str, str, str], ...]:
    """Read dataflow identities without resolving external structure references."""
    etree = import_optional("lxml.etree", extra="sdmx")
    root = xml_tree(body, provider)
    return tuple(
        (
            node.get("agencyID"),
            node.get("id"),
            next(
                (
                    str(child.text)
                    for child in node
                    if etree.QName(child).localname == "Name"
                    and child.get("{http://www.w3.org/XML/1998/namespace}lang", "en")
                    == "en"
                ),
                node.get("id"),
            ),
        )
        for node in root.iter()
        if etree.QName(node).localname == "Dataflow"
        and node.get("id")
        and node.get("agencyID")
    )


def trim_xml(
    body: bytes, provider: str, *, codes: frozenset[str], search: str = ""
) -> bytes:
    """Keep a source's structure and a small selection of its published codes."""
    etree = import_optional("lxml.etree", extra="sdmx")
    root = xml_tree(body, provider)
    _prune_attributes(root, etree, codes)
    concepts = {
        node.get("id") for node in root.iter() if node.get("class") == "Concept"
    }
    for node in list(root.iter()):
        local = etree.QName(node).localname
        parent = node.getparent()
        if parent is None:
            continue
        node.attrib.pop("urn", None)
        if local == "Concept" and node.get("id") not in concepts:
            parent.remove(node)
            continue
        if (
            local == "Name"
            and node.get("{http://www.w3.org/XML/1998/namespace}lang", "en") != "en"
        ):
            parent.remove(node)
            continue
        if local in {
            "Annotations",
            "Description",
            "Constraints",
            "CategorySchemes",
            "Categorisations",
            "OrganisationSchemes",
        }:
            if local != "Annotations" or not _legal_annotation(node):
                parent.remove(node)
        elif search and local == "Dataflow":
            names = " ".join(
                str(child.text or "")
                for child in node
                if etree.QName(child).localname == "Name"
            )
            if search.casefold() not in f"{node.get('id')} {names}".casefold():
                parent.remove(node)
        elif local == "Codelist":
            _trim_codes(node, codes, etree)
    # A structure response can include many unrelated code lists. Retain
    # only enumerations referenced by the surviving concepts/components.
    referenced = {
        node.get("id") for node in root.iter() if node.get("class") == "Codelist"
    }
    _remove_unused_lists(root, referenced, etree)
    return cast("bytes", etree.tostring(root, encoding="UTF-8", xml_declaration=True))


def _legal_annotation(node: Any) -> bool:  # noqa: ANN401 - lazy lxml element
    """Keep rights metadata when trimming source structures for recording."""
    text = (
        " ".join(node.itertext())
        + " "
        + " ".join(value for child in node.iter() for value in child.attrib.values())
    ).casefold()
    return any(
        word in text
        for word in (
            "copyright",
            "license",
            "licence",
            "restricted",
            "third-party",
            "third party",
            "permission",
            "commercial",
            "storage",
            "caching",
            "llm",
        )
    )


def _trim_codes(node: Any, codes: frozenset[str], etree: Any) -> None:  # noqa: ANN401 - lazy lxml API
    """Retain the selected and first two published codes of one enumeration."""
    entries = [child for child in node if etree.QName(child).localname == "Code"]
    for child in entries:
        if child.get("id") not in codes and child not in entries[:2]:
            node.remove(child)


def data_codes(body: bytes, provider: str) -> frozenset[str]:
    """Collect dimension and attribute codes used by recorded observations."""
    root = xml_tree(body, provider)
    return frozenset(
        value for node in root.iter() for pair in node.attrib.items() for value in pair
    )


def trim_data(body: bytes, provider: str, dimensions: frozenset[str]) -> bytes:
    """Keep observation values, keys and the attributes used by frame metadata."""
    etree = import_optional("lxml.etree", extra="sdmx")
    root = xml_tree(body, provider)
    keep = dimensions | _FRAME_ATTRIBUTES | {"TIME_PERIOD", "OBS_VALUE"}
    for node in list(root.iter()):
        local = etree.QName(node).localname
        parent = node.getparent()
        if (
            local == "Value"
            and parent is not None
            and etree.QName(parent).localname == "Attributes"
            and node.get("id") not in keep
        ):
            parent.remove(node)
        elif local in {"Series", "Obs", "DataSet"}:
            for name in list(node.attrib):
                if not name.startswith("{") and name not in keep:
                    del node.attrib[name]
    return cast("bytes", etree.tostring(root, encoding="UTF-8", xml_declaration=True))


def _remove_unused_lists(root: Any, referenced: set[str | None], etree: Any) -> None:  # noqa: ANN401 - lazy lxml API
    """Drop enumerations unreferenced by the retained structure."""
    for node in list(root.iter()):
        if (
            etree.QName(node).localname == "Codelist"
            and node.get("id") not in referenced
        ):
            node.getparent().remove(node)


def _prune_attributes(root: Any, etree: Any, used: frozenset[str]) -> None:  # noqa: ANN401 - lazy lxml API
    """Keep attribute definitions used by the small recorded selections."""
    kept_attributes = _FRAME_ATTRIBUTES
    for node in list(root.iter()):
        if (
            etree.QName(node).localname == "Attribute"
            and node.get("id") not in kept_attributes | used
        ):
            node.getparent().remove(node)
