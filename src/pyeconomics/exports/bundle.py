# src/pyeconomics/exports/bundle.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Reproducibility bundles: one zip that reruns a result (ADR-0012 decision 7).

:func:`write_bundle` writes a result as a zip of eight members:

- ``result.json``: the result's canonical bytes;
- ``inputs.json``: its validated inputs, as canonical JSON;
- ``request.json``: the bind request (``as_of``, ``vintage``, ``profile``,
  ``concepts``, ``parameters``) of a run that bound data, else ``null``;
- ``manifest.json``: the manifest, as canonical JSON;
- ``ATTRIBUTION.txt``: the attribution, required notice and terms page of every
  source of its data;
- ``requirements.txt``: ``pyeconomics==<version>``, with the extras the model and
  its data's providers need;
- ``reproduce.py``: reruns the model and compares ``result_sha256``
  (:mod:`~pyeconomics.exports.reproduction`);
- ``README.txt``: what the members are and how to check and rerun them.

The zip is deterministic: every member stored (not deflated, so no zlib build
changes a byte), in sorted order, dated 1980-01-01 00:00 with Unix permissions
0644, so equal results give equal bytes on every operating system.

:func:`check_bundle` verifies a bundle while executing nothing from it. Before
reading any member it refuses an archive above :data:`MAX_BUNDLE_BYTES`, more
than :data:`MAX_BUNDLE_MEMBERS` members, a member name with a path separator or
``..``, a member this format does not have or lacks one it has, a compressed or
encrypted member, and members larger in all than :data:`MAX_BUNDLE_BYTES`. It
then reads the JSON members only, strictly, and checks that each is canonical,
that the result's hashes are those of its body and inputs, and that the inputs
and the manifest members are the result's own. ``reproduce.py`` is never read:
it is code to read before running a bundle someone else made.

Examples
--------
>>> BUNDLE_MEMBERS[:2]
('ATTRIBUTION.txt', 'README.txt')
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.core.manifest import inputs_sha256, result_sha256
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.exports.reproduction import REPRODUCE_SCRIPT
from pyeconomics.surfaces.documents import jsonable

if TYPE_CHECKING:
    from os import PathLike

    from pyeconomics.core.results import Result
    from pyeconomics.surfaces.invoke import BindRequest

__all__ = [
    "BUNDLE_MEMBERS",
    "FIXED_TIMESTAMP",
    "JSON_MEMBERS",
    "MAX_BUNDLE_BYTES",
    "MAX_BUNDLE_MEMBERS",
    "MEMBER_MODE",
    "BundleReport",
    "bundle_bytes",
    "bundle_members",
    "check_bundle",
    "write_bundle",
]

#: Every member of a bundle, in the order they are stored.
BUNDLE_MEMBERS: Final = (
    "ATTRIBUTION.txt",
    "README.txt",
    "inputs.json",
    "manifest.json",
    "reproduce.py",
    "request.json",
    "requirements.txt",
    "result.json",
)
#: The members ``check_bundle`` reads; it never reads the others.
JSON_MEMBERS: Final = ("inputs.json", "manifest.json", "request.json", "result.json")
#: Every member's date and time: the earliest a zip can record.
FIXED_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)
#: Every member's Unix mode: a regular file, readable by all, writable by its owner.
MEMBER_MODE: Final = 0o100644
#: The most members ``check_bundle`` looks at.
MAX_BUNDLE_MEMBERS: Final = 64
#: The largest archive, and the largest total of its members, ``check_bundle``
#: reads: 64 MiB, four times the largest input a surface decodes.
MAX_BUNDLE_BYTES: Final = 64 * 1024 * 1024

_UNIX: Final = 3  # the zip "made by" system: Unix, whatever the host
_ENCRYPTED: Final = 0x1
_REQUEST_KEYS: Final = frozenset(
    {"as_of", "vintage", "profile", "concepts", "parameters"}
)
_BODY_KEYS: Final = ("inputs", "model_id", "model_version", "outputs", "warnings")


def _texts(result: Result[Any, Any]) -> list[str]:
    """Return ATTRIBUTION.txt's lines: each source's attribution, notice and terms."""
    records = [
        record
        for record in result.manifest.data_sources
        if record.licence is not LicenceClass.USER_SUPPLIED
    ]
    if not records:
        return ["This result read no data, so it carries no attribution."]
    lines = [
        "This result read the data below. Show each source's attribution and",
        "notice wherever the data appears.",
    ]
    seen: set[tuple[str, str | None, str | None]] = set()
    for record in records:
        key = (record.attribution, record.notice, record.terms_url)
        if key in seen:
            continue
        seen.add(key)
        lines += ["", f"{record.provider}: {record.series_id}", record.attribution]
        if record.notice:
            lines.append(record.notice)
        if record.terms_url:
            lines.append(f"Terms: {record.terms_url}")
    return lines


def _extras(result: Result[Any, Any]) -> list[str]:
    """Return the extras the model and the providers of its data need, sorted."""
    extras = {result.model.spec.extra} - {None}
    providers = {
        record.provider
        for record in result.manifest.data_sources
        if record.licence is not LicenceClass.USER_SUPPLIED
    }
    if providers:
        from pyeconomics.data import registry  # noqa: PLC0415 - only bound runs

        for provider in sorted(providers):
            if provider in registry.ids():
                extras.add(registry.get(provider).info.extra)
    return sorted(extra for extra in extras if extra)


def _requirements(result: Result[Any, Any]) -> list[str]:
    extras = _extras(result)
    suffix = f"[{','.join(extras)}]" if extras else ""
    return [
        "# Install with: pip install -r requirements.txt",
        f"pyeconomics{suffix}=={result.manifest.package_version}",
    ]


def _readme(result: Result[Any, Any], *, bound: bool) -> list[str]:
    manifest = result.manifest
    lines = [
        (
            f"A pyeconomics reproducibility bundle: {result.model_id}, version "
            f"{result.model_version}."
        ),
        f"result_sha256 {manifest.result_sha256}",
        f"Made with pyeconomics {manifest.package_version}.",
        "",
        "result.json       the result: inputs, outputs, warnings and manifest",
        "inputs.json       the validated inputs the model ran on",
        "request.json      the bind request of a run that read data, else null",
        "manifest.json     the provenance: versions, data records and hashes",
        "ATTRIBUTION.txt   the attributions and notices of the data",
        "requirements.txt  the pyeconomics version (and extras) to install",
        "reproduce.py      reruns the model and compares result_sha256",
        "",
        "Check it without running anything from it:",
        "    pyeconomics bundle check BUNDLE.zip",
        "",
        "Rerun it (reproduce.py is a program: read it before you run a bundle",
        "someone else made):",
        "    pip install -r requirements.txt",
        "    python reproduce.py",
    ]
    if bound:
        lines += [
            "",
            "Bind the data again at the recorded date and vintages, and compare:",
            "    python reproduce.py --refetch",
        ]
    return lines


def _text(lines: list[str]) -> bytes:
    return "".join(f"{line}\n" for line in lines).encode("utf-8")


def bundle_members(
    result: Result[Any, Any], request: BindRequest | None = None
) -> dict[str, bytes]:
    """Return a bundle's members by name, as the bytes :func:`write_bundle` stores.

    Parameters
    ----------
    result
        The result to bundle.
    request
        The bind request the run was made with, if it bound data.
    """
    recorded = None if request is None else jsonable(request.to_dict())
    return {
        "ATTRIBUTION.txt": _text(_texts(result)),
        "README.txt": _text(_readme(result, bound=request is not None)),
        "inputs.json": canonical_json(result.inputs.model_dump(mode="json")),
        "manifest.json": canonical_json(result.manifest.to_dict()),
        "reproduce.py": REPRODUCE_SCRIPT.encode("utf-8"),
        "request.json": canonical_json(recorded),
        "requirements.txt": _text(_requirements(result)),
        "result.json": result.to_json().encode("utf-8"),
    }


def bundle_bytes(members: dict[str, bytes]) -> bytes:
    """Return members as a deterministic zip: stored, sorted, fixed dates and modes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = _UNIX
            info.external_attr = MEMBER_MODE << 16
            archive.writestr(info, members[name])
    return buffer.getvalue()


def write_bundle(
    result: Result[Any, Any],
    target: str | PathLike[str] | IO[bytes],
    request: BindRequest | None = None,
) -> None:
    """Write a result's reproducibility bundle to a path or a binary stream.

    Parameters
    ----------
    result
        The result to bundle.
    target
        A file path, or a binary stream to write to.
    request
        The :class:`~pyeconomics.surfaces.invoke.BindRequest` the run bound its
        data with; ``reproduce.py --refetch`` binds again from it. ``None`` for
        a run that read no data.
    """
    data = bundle_bytes(bundle_members(result, request))
    if isinstance(target, str | os.PathLike):
        Path(target).write_bytes(data)
    else:
        target.write(data)


@dataclass(frozen=True, slots=True)
class BundleReport:
    """What :func:`check_bundle` verified."""

    model_id: str
    model_version: int
    package_version: str
    result_sha256: str
    inputs_sha256: str
    bound: bool
    """Whether the bundle records a bind request."""
    sources: int
    """The number of data records in its manifest."""
    members: tuple[tuple[str, int], ...]
    """Each member's name and size in bytes."""

    def to_dict(self) -> dict[str, object]:
        """Return the report as JSON-ready values."""
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "package_version": self.package_version,
            "result_sha256": self.result_sha256,
            "inputs_sha256": self.inputs_sha256,
            "bound": self.bound,
            "sources": self.sources,
            "members": [{"name": name, "size": size} for name, size in self.members],
        }


def _refuse(message: str) -> InputError:
    return InputError(f"the bundle is not valid: {message}")


def _refuse_constant(name: str) -> object:
    msg = f"a JSON member holds {name}"
    raise _refuse(msg)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    found: dict[str, object] = {}
    for key, value in pairs:
        if key in found:
            msg = f"a JSON member repeats the key {key!r}"
            raise _refuse(msg)
        found[key] = value
    return found


def _open(source: str | PathLike[str] | bytes) -> zipfile.ZipFile:
    """Open an archive after checking its size; a failure names no path."""
    target: Path | IO[bytes]
    size, failure = 0, ""
    if isinstance(source, bytes):
        size, target = len(source), io.BytesIO(source)
    else:
        target = Path(source)
        try:
            size = target.stat().st_size
        except OSError as error:
            failure = type(error).__name__
    if failure:
        msg = f"the bundle file cannot be read ({failure})"
        raise InputError(msg)
    if size > MAX_BUNDLE_BYTES:
        msg = f"it is larger than {MAX_BUNDLE_BYTES} bytes"
        raise _refuse(msg)
    try:
        return zipfile.ZipFile(target)
    except (zipfile.BadZipFile, OSError) as error:
        msg = f"it is not a zip archive ({type(error).__name__})"
        raise _refuse(msg) from None


def _check_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Refuse the archive's layout before any member is read."""
    infos = archive.infolist()
    if len(infos) > MAX_BUNDLE_MEMBERS:
        msg = f"it has more than {MAX_BUNDLE_MEMBERS} members"
        raise _refuse(msg)
    seen: set[str] = set()
    for info in infos:
        name = info.filename
        if "/" in name or "\\" in name or ".." in name:
            msg = f"the member name {name!r} holds a path separator or '..'"
            raise _refuse(msg)
        if name in seen:
            msg = f"it holds {name!r} twice"
            raise _refuse(msg)
        seen.add(name)
        if name not in BUNDLE_MEMBERS:
            msg = f"it holds an unexpected member {name!r}"
            raise _refuse(msg)
        if info.compress_type != zipfile.ZIP_STORED or info.flag_bits & _ENCRYPTED:
            msg = f"{name} is compressed or encrypted; bundle members are stored"
            raise _refuse(msg)
    missing = sorted(set(BUNDLE_MEMBERS) - seen)
    if missing:
        msg = f"it lacks {', '.join(missing)}"
        raise _refuse(msg)
    if sum(info.file_size for info in infos) > MAX_BUNDLE_BYTES:
        msg = f"its members hold more than {MAX_BUNDLE_BYTES} bytes"
        raise _refuse(msg)
    return infos


def _read_json(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> object:
    """Read one JSON member strictly; it must be canonical JSON."""
    try:
        with archive.open(info) as member:
            data = member.read(info.file_size + 1)
    except (zipfile.BadZipFile, OSError) as error:
        msg = f"{info.filename} cannot be read ({type(error).__name__})"
        raise _refuse(msg) from None
    if len(data) != info.file_size:
        msg = f"{info.filename} is not the size its entry records"
        raise _refuse(msg)
    try:
        value = json.loads(
            data.decode("utf-8"),
            parse_constant=_refuse_constant,
            object_pairs_hook=_unique,
        )
        canonical = canonical_json(value)
    except InputError:
        raise
    except (ValueError, TypeError, RecursionError) as error:
        msg = f"{info.filename} is not JSON ({type(error).__name__})"
        raise _refuse(msg) from None
    if canonical != data:
        msg = f"{info.filename} is not canonical JSON"
        raise _refuse(msg)
    return value


def _mapping(value: object, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"{what} is not a JSON object"
        raise _refuse(msg)
    return value


def check_bundle(source: str | PathLike[str] | bytes) -> BundleReport:
    """Verify a bundle without executing anything from it.

    Parameters
    ----------
    source
        The bundle's path, or its bytes.

    Returns
    -------
    BundleReport
        The model, the versions and hashes, and the members verified.

    Raises
    ------
    InputError
        If the file cannot be read, or the bundle is not valid: the message says
        what is wrong, never naming a path.
    """
    with _open(source) as archive:
        infos = _check_members(archive)
        documents = {
            info.filename: _read_json(archive, info)
            for info in infos
            if info.filename in JSON_MEMBERS
        }
    result = _mapping(documents["result.json"], "result.json")
    missing = sorted({*_BODY_KEYS, "manifest"} - set(result))
    if missing:
        msg = f"result.json lacks {', '.join(missing)}"
        raise _refuse(msg)
    manifest = _mapping(result["manifest"], "result.json's manifest")
    model_id, version = result["model_id"], result["model_version"]
    if not isinstance(model_id, str) or type(version) is not int:
        msg = "result.json's model_id is not text or its model_version not an integer"
        raise _refuse(msg)
    body = {key: result[key] for key in _BODY_KEYS}
    recorded = (manifest.get("result_sha256"), manifest.get("inputs_sha256"))
    computed = (
        result_sha256(body),
        inputs_sha256(model_id, version, result["inputs"]),
    )
    if recorded[0] != computed[0]:
        msg = "result_sha256 is not the hash of the result's body"
        raise _refuse(msg)
    if recorded[1] != computed[1]:
        msg = "inputs_sha256 is not the hash of the result's inputs"
        raise _refuse(msg)
    if documents["manifest.json"] != manifest:
        msg = "manifest.json is not the result's manifest"
        raise _refuse(msg)
    if documents["inputs.json"] != result["inputs"]:
        msg = "inputs.json is not the result's inputs"
        raise _refuse(msg)
    request = documents["request.json"]
    if request is not None and set(_mapping(request, "request.json")) != set(
        _REQUEST_KEYS
    ):
        msg = "request.json is not a bind request"
        raise _refuse(msg)
    sources = manifest.get("data_sources")
    return BundleReport(
        model_id=model_id,
        model_version=version,
        package_version=str(manifest.get("package_version")),
        result_sha256=computed[0],
        inputs_sha256=computed[1],
        bound=request is not None,
        sources=len(sources) if isinstance(sources, list) else 0,
        members=tuple((info.filename, info.file_size) for info in infos),
    )
