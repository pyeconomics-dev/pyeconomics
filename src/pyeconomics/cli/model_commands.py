# src/pyeconomics/cli/model_commands.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics models`` and ``registry export``: the registry on the command line.

``models list``, ``search`` and ``describe`` read the registry
(:mod:`pyeconomics.surfaces.listing`, :func:`pyeconomics.registry.describe`).
``models run ID`` has no options of its own until :func:`prepare_run` sees the
id on the command line: it then generates one ``--<field>`` option per input
field of the model (underscores written as hyphens), beside the run options
(``--inputs``, ``--format``, ``--out``) and the bind options (``--as-of``,
``--vintage``, ``--profile``, ``--concept``, ``--param``). Each value reaches
the model as ``field=value`` text, which :func:`~pyeconomics.surfaces.codec.
decode_pairs` types by the model's input schema, and the run goes through
:func:`~pyeconomics.surfaces.invoke.invoke`, so ``--format json`` prints the same
bytes as ``Result.to_json()``, followed by one newline.

A run binds the model's data when any bind option is given (``--profile
default`` alone binds the default profile at the latest data); the options then
override the values bound, as ``pyeconomics.bind``'s overrides do.

``--format csv|xlsx|parquet|arrow`` writes an export, ``--bundle PATH`` also
writes the run's reproducibility bundle, and ``--batch FILE`` runs the model once
per row of a CSV or JSON Lines file (:mod:`pyeconomics.cli.exporting`).

``--narrate`` also asks the optional AI narrative (:func:`pyeconomics.ai.narrate`)
to explain the result, binding any data under the user's ``llm_use`` policy. The
narrative and its cost follow a table on standard output; with any other format,
or ``--out``, they go to standard error, so standard output stays the canonical
bytes. A narrative is never written into an export, a bundle or a cache.
"""

import inspect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Final, Literal

from cyclopts import App, Group, Parameter

from pyeconomics import registry
from pyeconomics.cli.context import Context, ContextParameter, UsageError
from pyeconomics.cli.exporting import (
    batch_blocks,
    read_batch,
    refuse_binary_terminal,
    write_bundle_file,
    write_export,
)
from pyeconomics.cli.output import (
    Block,
    DescribeFormat,
    Format,
    Grid,
    RunFormat,
    cell,
    emit,
    emit_json,
    show,
)
from pyeconomics.core.binding import DEFAULT_PROFILE
from pyeconomics.core.errors import (
    InputError,
    MissingOptionalDependencyError,
    RegistryError,
)
from pyeconomics.core.schema import input_schema, output_schema
from pyeconomics.surfaces import codec, listing
from pyeconomics.surfaces.envelope import canonical_bytes
from pyeconomics.surfaces.invoke import BindRequest, invoke, invoke_batch

__all__ = [
    "RESERVED_OPTIONS",
    "describe_model",
    "export_registry",
    "list_models",
    "model_command",
    "prepare_run",
    "result_blocks",
    "run_app",
    "search_models",
]

#: The options ``models run`` takes besides a model's fields; no field may
#: take one of these names.
RESERVED_OPTIONS: Final = frozenset(
    {
        "--inputs",
        "--batch",
        "--format",
        "--out",
        "--bundle",
        "--narrate",
        "--as-of",
        "--vintage",
        "--profile",
        "--concept",
        "--param",
        "--debug",
        "--help",
        "--version",
    }
)

_INPUTS: Final = Group(
    "Inputs",
    help="The model's input fields; a value is a number, text, true or false, "
    "null, or a JSON literal for an array.",
    sort_key=1,
)
_RUN: Final = Group("Run options", sort_key=2)
_BIND: Final = Group(
    "Data",
    help="Any of these binds the model's data first; the inputs above then "
    "override the values bound.",
    sort_key=3,
)
_METAVARS: Final = {
    "number": "NUMBER",
    "integer": "INTEGER",
    "string": "TEXT",
    "boolean": "true|false",
    "array": "JSON",
    "object": "JSON",
}

FormatOption = Annotated[Format, Parameter(name="--format")]
OutOption = Annotated[
    Path | None,
    Parameter(name="--out", help="Write the output to this file instead."),
]
#: ``--vintage``'s values: :class:`~pyeconomics.core.binding.VintagePolicy`'s.
Vintage = Literal["real_time", "latest"]


# --- list, search and describe -------------------------------------------------


def _entry_grid(title: str, entries: Sequence[Mapping[str, object]]) -> Grid:
    return Grid(
        title,
        ("Id", "Version", "Domain", "Title", "Extra", "Data"),
        tuple(
            (
                str(entry["id"]),
                cell(entry["version"]),
                str(entry["domain"]),
                str(entry["title"]),
                cell(entry["extra"]),
                "bound" if entry["bound"] else "",
            )
            for entry in entries
        ),
    )


def list_models(
    *,
    domain: str | None = None,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """List the registered models, sorted by id.

    Parameters
    ----------
    domain
        Only this domain's models, such as fixed_income.
    output_format
        table, or json for the entries as canonical JSON.
    """
    entries = listing.list_models(domain)
    if output_format == "json":
        emit_json(context.streams, entries, out)
        return
    footer = f"{len(entries)} models. Describe one with: pyeconomics models describe ID"
    show(context.streams, [_entry_grid("Models", entries), footer], out)


def search_models(
    text: str,
    /,
    *,
    limit: int = 20,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """Search the models' ids, titles, tags, domains and summaries.

    Parameters
    ----------
    text
        Words to look for.
    limit
        At most this many models, from 1 to 100.
    output_format
        table, or json for the entries as canonical JSON.
    """
    entries = listing.search_models(text, limit)
    if output_format == "json":
        emit_json(context.streams, entries, out)
        return
    show(context.streams, [_entry_grid("Matches", entries)], out)


def describe_model(
    model_id: str,
    /,
    *,
    output_format: Annotated[DescribeFormat, Parameter(name="--format")] = "markdown",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """Describe a model: its card, or every field of its description as JSON.

    Parameters
    ----------
    model_id
        The model's id.
    output_format
        markdown for the model card, or json for the specification, the input
        and output JSON Schemas, the examples and the card.
    """
    entry = registry.describe(model_id)
    if output_format == "json":
        emit_json(context.streams, entry, out)
        return
    card = str(entry["card"])
    emit(context.streams, (card.rstrip("\n") + "\n").encode("utf-8"), out)


def export_registry(
    *,
    out: Annotated[Path, Parameter(name="--out", help="The directory to write to.")],
    figures: bool = True,
    context: ContextParameter,
) -> None:
    """Write registry.json, the description of every model, into a directory.

    With the server extra installed it also writes openapi.json, the REST API's
    OpenAPI 3.1 document. Each file is canonical JSON with no trailing newline,
    so its SHA-256 identifies it; the directory is created if it does not exist.

    Parameters
    ----------
    figures
        Include each model's example figure (it needs the plot extra);
        --no-figures writes null for every figure.
    """
    from pyeconomics.core._optional import import_optional  # noqa: PLC0415
    from pyeconomics.surfaces.registry_export import (  # noqa: PLC0415 - loads plotting
        write_registry,
    )

    failure = ""
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        failure = type(error).__name__
    if failure:
        msg = f"the --out directory cannot be created ({failure})"
        raise InputError(msg)
    target = out / "registry.json"
    write_registry(target, figures=figures)
    written = [target]
    try:
        import_optional("fastapi", extra="server")
    except MissingOptionalDependencyError as error:
        context.streams.error(f"openapi.json skipped: {error}")
    else:
        from pyeconomics.server.openapi import write_openapi  # noqa: PLC0415

        written.append(out / "openapi.json")
        write_openapi(written[-1])
    context.streams.write("".join(f"{path}\n" for path in written).encode())


# --- run -----------------------------------------------------------------------


def run_unregistered(model_id: str, /) -> None:
    """Run a model: its id, then its inputs as options.

    Each input field of the model becomes an option, its name written with
    hyphens (--present-value 100); see the model's own options with
    pyeconomics models run ID --help, and its ids with pyeconomics models list.

    Parameters
    ----------
    model_id
        The model's id, written first.
    """
    # prepare_run registers a model's command when its id comes straight after
    # "models run"; reaching this means it did not (it followed "--").
    msg = f"name the model straight after models run: pyeconomics models run {model_id}"
    raise UsageError(msg)


def run_app() -> App:
    """Return the ``models run`` application, to which :func:`prepare_run` adds."""
    app = App(name="run", help=run_unregistered.__doc__)
    app.default(run_unregistered)
    return app


@dataclass(slots=True)
class _Field:
    """One input field across a model's calculations."""

    name: str
    schema: Mapping[str, Any]
    calculations: list[str] = field(default_factory=list)


def _resolve(schema: Mapping[str, Any], root: Mapping[str, Any]) -> Mapping[str, Any]:
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        resolved: Mapping[str, Any] = root["$defs"][reference.removeprefix("#/$defs/")]
        return resolved
    return schema


def _members(root: Mapping[str, Any]) -> list[tuple[str | None, Mapping[str, Any]]]:
    """Each calculation's name and field schemas; one unnamed member otherwise."""
    discriminator = root.get("discriminator")
    if not isinstance(discriminator, Mapping):
        return [(None, root.get("properties", {}))]
    return [
        (name, _resolve({"$ref": reference}, root)["properties"])
        for name, reference in sorted(discriminator["mapping"].items())
    ]


def _fields(root: Mapping[str, Any]) -> dict[str, _Field]:
    fields: dict[str, _Field] = {}
    for calculation, properties in _members(root):
        for name, schema in properties.items():
            entry = fields.setdefault(name, _Field(name, schema))
            if calculation is not None:
                entry.calculations.append(calculation)
    return fields


def _options(
    schema: Mapping[str, Any], root: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    return [_resolve(option, root) for option in schema.get("anyOf", [schema])]


def _kinds(schema: Mapping[str, Any], root: Mapping[str, Any]) -> list[str]:
    kinds: list[str] = []
    for option in _options(schema, root):
        kind = option.get("type")
        found = kind if isinstance(kind, list) else [kind] if kind else ["string"]
        kinds.extend(k for k in found if k not in kinds)
    return kinds


def _unit(schema: Mapping[str, Any], root: Mapping[str, Any]) -> str:
    for option in [schema, *_options(schema, root)]:
        unit = option.get("x-unit")
        if isinstance(unit, str):
            return unit
    return ""


def _help(entry: _Field, root: Mapping[str, Any], *, discriminator: str | None) -> str:
    schema = entry.schema
    if entry.name == discriminator:
        names = sorted(set(entry.calculations))
        return f"Which calculation to run: {', '.join(names)}."
    parts = [str(schema.get("description") or entry.name.replace("_", " ")).rstrip(".")]
    unit = _unit(schema, root)
    if unit:
        parts.append(f"Unit: {unit}")
    choices = [
        str(value)
        for option in _options(schema, root)
        for value in option.get("enum", ())
    ]
    if choices:
        parts.append(f"One of: {', '.join(choices)}")
    if "default" in schema:
        parts.append(f"Default: {cell(schema['default']) or 'null'}")
    if entry.calculations:
        parts.append(f"For: {', '.join(entry.calculations)}")
    return ". ".join(parts) + "."


def _option_name(name: str) -> str:
    return f"--{name.replace('_', '-')}"


def _keyword(name: str, annotation: object, default: object) -> inspect.Parameter:
    return inspect.Parameter(
        name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=annotation
    )


def _signature(model_id: str, root: Mapping[str, Any]) -> list[inspect.Parameter]:
    discriminator = root.get("discriminator")
    tag = discriminator["propertyName"] if isinstance(discriminator, Mapping) else None
    parameters: list[inspect.Parameter] = []
    for entry in _fields(root).values():
        option = _option_name(entry.name)
        if option in RESERVED_OPTIONS:
            msg = (
                f"{model_id}: its input {entry.name} takes the command line's "
                f"option {option}"
            )
            raise RegistryError(msg)
        kinds = [k for k in _kinds(entry.schema, root) if k != "null"]
        parameter = Parameter(
            name=option,
            help=_help(entry, root, discriminator=tag),
            metavar=_METAVARS.get(kinds[0], "VALUE") if len(kinds) == 1 else "VALUE",
            group=_INPUTS,
            allow_leading_hyphen=True,
            negative="",
            show_default=False,
        )
        parameters.append(
            _keyword(f"field_{entry.name}", Annotated[str | None, parameter], None)
        )
    return parameters


def _fixed_parameters() -> list[inspect.Parameter]:
    return [
        _keyword(
            "inputs",
            Annotated[
                str | None,
                Parameter(
                    name="--inputs",
                    metavar="FILE",
                    group=_RUN,
                    allow_leading_hyphen=True,
                    help="A JSON object of inputs in a file, or - for standard "
                    "input; the field options override its values.",
                ),
            ],
            None,
        ),
        _keyword(
            "batch",
            Annotated[
                str | None,
                Parameter(
                    name="--batch",
                    metavar="FILE",
                    group=_RUN,
                    allow_leading_hyphen=True,
                    help="Run once per row of a CSV file (a header of field "
                    "names) or a JSON Lines file, or - for standard input.",
                ),
            ],
            None,
        ),
        _keyword(
            "output_format",
            Annotated[
                RunFormat,
                Parameter(
                    name="--format",
                    group=_RUN,
                    help="json for the canonical result, table, or an export: "
                    "csv, xlsx, parquet or arrow.",
                ),
            ],
            "json",
        ),
        _keyword(
            "out",
            Annotated[
                Path | None,
                Parameter(
                    name="--out", group=_RUN, help="Write the output to this file."
                ),
            ],
            None,
        ),
        _keyword(
            "bundle",
            Annotated[
                Path | None,
                Parameter(
                    name="--bundle",
                    metavar="PATH",
                    group=_RUN,
                    help="Also write the run's reproducibility bundle, a zip, "
                    "to this file.",
                ),
            ],
            None,
        ),
        _keyword(
            "narrate",
            Annotated[
                bool,
                Parameter(
                    name="--narrate",
                    negative="",
                    group=_RUN,
                    help="Also explain the result with the optional AI narrative "
                    "(ai_enabled must be on); it prints after a table, or to "
                    "standard error.",
                ),
            ],
            False,  # noqa: FBT003 - a flag's default
        ),
        _keyword(
            "as_of",
            Annotated[
                str | None,
                Parameter(
                    name="--as-of",
                    metavar="DATE",
                    group=_BIND,
                    help="Read the data as published on this date (YYYY-MM-DD).",
                ),
            ],
            None,
        ),
        _keyword(
            "vintage",
            Annotated[
                Vintage | None,
                Parameter(
                    name="--vintage",
                    group=_BIND,
                    help="real_time or latest, for every binding in place of "
                    "its own policy.",
                ),
            ],
            None,
        ),
        _keyword(
            "profile",
            Annotated[
                str | None,
                Parameter(
                    name="--profile",
                    metavar="NAME",
                    group=_BIND,
                    help=f"The set of bindings to read ({DEFAULT_PROFILE} by default).",
                ),
            ],
            None,
        ),
        _keyword(
            "concept",
            Annotated[
                tuple[str, ...],
                Parameter(
                    name="--concept",
                    metavar="FIELD=ID",
                    group=_BIND,
                    negative="",
                    show_default=False,
                    help="Bind a field to another catalog concept; repeat for "
                    "more fields.",
                ),
            ],
            (),
        ),
        _keyword(
            "param",
            Annotated[
                tuple[str, ...],
                Parameter(
                    name="--param",
                    metavar="NAME=VALUE",
                    group=_BIND,
                    negative="",
                    show_default=False,
                    help="A concept parameter, such as an SEP meeting; repeat "
                    "for more.",
                ),
            ],
            (),
        ),
        _keyword("context", ContextParameter, inspect.Parameter.empty),
    ]


def _assignments(items: Sequence[str], option: str, what: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for item in items:
        name, separator, value = item.partition("=")
        if not separator or not name:
            msg = f"{option} takes {what}, not text without '='"
            raise InputError(msg)
        if name in found:
            msg = f"{option} names {name} twice"
            raise InputError(msg)
        found[name] = value
    return found


def _bind_request(
    *,
    as_of: str | None,
    vintage: str | None,
    profile: str | None,
    concept: Sequence[str],
    param: Sequence[str],
) -> BindRequest | None:
    if (
        as_of is None
        and vintage is None
        and profile is None
        and not concept
        and not param
    ):
        return None
    return BindRequest(
        as_of=as_of,
        vintage=vintage,
        profile=profile or DEFAULT_PROFILE,
        concepts=_assignments(concept, "--concept", "FIELD=ID"),
        parameters=_assignments(param, "--param", "NAME=VALUE"),
    )


def _read_inputs(context: Context, source: str) -> dict[str, object]:
    """Read a JSON object of inputs from a file or standard input, within limits."""
    limit = codec.MAX_INPUT_BYTES
    if source == "-":
        return codec.decode_json(context.streams.stdin.read(limit + 1), limit=limit)
    failure = ""
    data = b""
    try:
        with Path(source).open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError as error:
        failure = type(error).__name__
    if failure:
        msg = f"the --inputs file cannot be read ({failure})"
        raise InputError(msg)
    return codec.decode_json(data, limit=limit)


def _decode_options(
    model: Any,  # noqa: ANN401 - a registered model
    root: Mapping[str, Any],
    pairs: list[str],
    document: Mapping[str, object],
) -> dict[str, object]:
    if not pairs:
        return {}
    discriminator = root.get("discriminator")
    if isinstance(discriminator, Mapping):
        tag = discriminator["propertyName"]
        named = any(pair.startswith(f"{tag}=") for pair in pairs)
        if not named and isinstance(document.get(tag), str):
            pairs = [f"{tag}={document[tag]}", *pairs]
    return codec.decode_pairs(model, pairs)


def _write_batch(
    context: Context,
    batch: Any,  # noqa: ANN401 - a BatchResult
    output_format: str,
    out: Path | None,
) -> None:
    if output_format == "table":
        show(context.streams, batch_blocks(batch), out)
    elif output_format == "json":
        from pyeconomics.exports import export_bytes  # noqa: PLC0415 - loads exports

        emit(context.streams, export_bytes(batch, "json") + b"\n", out)
    else:
        write_export(context, batch, output_format, out)


def _narrative_policy() -> Any:  # noqa: ANN401 - an LlmUsePolicy
    """Return the user's ``llm_use`` policy, which a narrated run binds under."""
    from pyeconomics.data.config import settings  # noqa: PLC0415 - the data layer

    return settings().llm_use_policy


def _narrate(result: Any) -> str:  # noqa: ANN401 - a model's result
    """Return a result's narrative, its notice and its cost, as text."""
    from pyeconomics.ai import narrate  # noqa: PLC0415 - loads the AI narrative

    return narrate(result).render()


def model_command(model: Any, typed_id: str) -> Callable[..., None]:  # noqa: ANN401
    """Return the ``models run`` command of one model, its options generated.

    Parameters
    ----------
    model
        The registered model.
    typed_id
        The id as written: an alias still warns when the model runs.

    Raises
    ------
    RegistryError
        If an input field's option takes the name of a run option.
    """
    root = input_schema(model)
    fields = _signature(model.id, root)

    # Cyclopts reads a function's own annotations over its __signature__'s, so
    # both are set to the generated signature below.
    def command(  # noqa: PLR0913 - the run and bind options
        *,
        context: Context,
        inputs: str | None = None,
        batch: str | None = None,
        output_format: str = "json",
        out: Path | None = None,
        bundle: Path | None = None,
        narrate: bool = False,
        as_of: str | None = None,
        vintage: str | None = None,
        profile: str | None = None,
        concept: Sequence[str] = (),
        param: Sequence[str] = (),
        **values: str | None,
    ) -> None:
        refuse_binary_terminal(context, output_format, out)
        pairs = [
            f"{name.removeprefix('field_')}={text}"
            for name, text in values.items()
            if text is not None
        ]
        request = _bind_request(
            as_of=as_of, vintage=vintage, profile=profile, concept=concept, param=param
        )
        if batch is not None:
            if pairs or inputs is not None or bundle is not None or request or narrate:
                msg = (
                    "--batch takes every row's inputs from its file; it cannot be "
                    "combined with field options, --inputs, --bundle, --narrate or "
                    "the data options"
                )
                raise UsageError(msg)
            outcome = invoke_batch(typed_id, read_batch(context, batch))
            _write_batch(context, outcome, output_format, out)
            return
        document = {} if inputs is None else _read_inputs(context, inputs)
        merged = {**document, **_decode_options(model, root, pairs, document)}
        policy = _narrative_policy() if narrate else None
        result = invoke(typed_id, merged, bind=request, llm_use=policy)
        narrative = _narrate(result) if narrate else None
        if bundle is not None:
            write_bundle_file(result, bundle, request)
        if output_format == "json":
            emit(context.streams, canonical_bytes(result) + b"\n", out)
        elif output_format == "table":
            blocks = result_blocks(result)
            if narrative is not None and out is None:
                blocks.append(f"Narrative\n\n{narrative}")
                narrative = None
            show(context.streams, blocks, out)
        else:
            write_export(context, result, output_format, out)
        if narrative is not None:
            context.streams.error(narrative)

    spec = model.spec
    signature = inspect.Signature([*fields, *_fixed_parameters()])
    command.__signature__ = signature  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
    command.__annotations__ = {
        name: parameter.annotation for name, parameter in signature.parameters.items()
    }
    command.__doc__ = (
        f"{spec.title} ({model.id}, version {spec.version}).\n\n{spec.summary}\n\n"
        f"Its card: pyeconomics models describe {model.id}"
    )
    return command


def prepare_run(app: App, tokens: Sequence[str]) -> None:
    """Add ``models run ID``'s command when the command line names a model.

    ``tokens`` are the command line without its global flags; the id must come
    straight after ``models run``. An alias is registered as written, so the
    run warns that it is deprecated. An application that already has the
    command, from an earlier command line it ran, keeps it.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id.
    """
    if len(tokens) < 3 or tokens[:2] != ["models", "run"] or tokens[2].startswith("-"):  # noqa: PLR2004 - "models run ID"
        return
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - discovers models

    typed = tokens[2]
    run = app["models"]["run"]
    if typed in run:
        return
    found = installed()
    model = found.get(found.aliases().get(typed, typed))
    run.command(model_command(model, typed), name=typed)


# --- the result as a table ------------------------------------------------------


def _schema_for(
    root: Mapping[str, Any], values: Mapping[str, object]
) -> Mapping[str, Any]:
    discriminator = root.get("discriminator")
    if not isinstance(discriminator, Mapping):
        properties: Mapping[str, Any] = root.get("properties", {})
        return properties
    chosen = values.get(discriminator["propertyName"])
    reference = discriminator["mapping"].get(chosen)
    if reference is None:  # pragma: no cover - a result names its calculation
        return {}
    member_properties: Mapping[str, Any] = _resolve({"$ref": reference}, root)[
        "properties"
    ]
    return member_properties


def _value_rows(
    root: Mapping[str, Any], values: Mapping[str, object]
) -> tuple[tuple[str, ...], ...]:
    properties = _schema_for(root, values)
    return tuple(
        (name, cell(value), _unit(properties.get(name, {}), root))
        for name, value in values.items()
    )


def result_blocks(result: Any) -> list[Block]:  # noqa: ANN401 - a model's result
    """Return a result as tables: its inputs, outputs, warnings and data.

    The attributions and notices of the data it read follow the tables, then the
    result's SHA-256.
    """
    model = result.model
    inputs = result.inputs.model_dump(mode="json")
    outputs = result.outputs.model_dump(mode="json")
    blocks: list[Block] = [
        f"{model.spec.title} ({result.model_id}, version {result.model_version})",
        Grid(
            "Inputs",
            ("Input", "Value", "Unit"),
            _value_rows(input_schema(model), inputs),
        ),
        Grid(
            "Outputs",
            ("Output", "Value", "Unit"),
            _value_rows(output_schema(model), outputs),
        ),
    ]
    if result.warnings:
        blocks.append(
            Grid(
                "Warnings",
                ("Code", "Message"),
                tuple((w.code, w.message) for w in result.warnings),
            )
        )
    records = result.manifest.data_sources
    if records:
        blocks.append(
            Grid(
                "Data",
                ("Field", "Provider", "Series", "Vintage", "Observations"),
                tuple(
                    (
                        cell(record.field),
                        record.provider,
                        record.series_id,
                        cell(record.vintage),
                        ""
                        if record.observation_start is None
                        else f"{record.observation_start} to {record.observation_end}",
                    )
                    for record in records
                ),
            )
        )
    attributions = result.attributions()
    if attributions:
        blocks.append("\n".join(attributions))
    blocks.append(f"result_sha256 {result.manifest.result_sha256}")
    return blocks
