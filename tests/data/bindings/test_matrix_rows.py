# tests/data/bindings/test_matrix_rows.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A matrix field reads a window of a table's rows (Phase 3 Step 16).

A field that is a tuple of rows, bound to a table concept with the ``window``
rule, receives one row per period of the window and, in each, one value per
column: every column of the table, or the ones the binding's ``columns`` names,
in that order. Its window ends with the other windows of its frequency, so its
rows pair with a series' values by position. A scripted Ken French provider
answers the industry portfolios and the three-factor file.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any, Literal

import pytest
from catalog_support import HOSTED_TERMS, month_end
from pydantic import Field
from scripted import registry_of, scripted

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    InputError,
    Invariant,
    ModelCard,
    ModelInputs,
    ModelOutputs,
    Reference,
    Registry,
    RegistryError,
    Return,
    UnitKind,
    model,
    run_model,
)
from pyeconomics.data import (
    ColumnMeta,
    DataError,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Table,
    TableMeta,
    UnitRecord,
)
from pyeconomics.data.bindings import bind_model, validate_bindings

AS_OF = dt.date(2026, 1, 15)
INDUSTRIES = ("NoDur", "Durbl", "Manuf")
FACTORS = ("Mkt-RF", "SMB", "HML", "RF")

_Value = Annotated[Return, Field(ge=-10.0, le=10.0)]


_Row = Annotated[tuple[_Value, ...], Field(min_length=1, max_length=4), ARRAY_INPUT]
_NarrowRow = Annotated[
    tuple[_Value, ...], Field(min_length=1, max_length=2), ARRAY_INPUT
]


class PanelInputs(ModelInputs):
    returns: tuple[_Row, ...] = Field(
        min_length=1, max_length=24, description="Rows of asset returns"
    )
    factors: tuple[_Row, ...] = Field(
        min_length=1, max_length=24, description="Rows of factor returns"
    )
    market: Annotated[tuple[_Value, ...], ARRAY_INPUT] = Field(
        min_length=1, max_length=24, description="The market's excess return"
    )


class NarrowInputs(PanelInputs):
    factors: tuple[_NarrowRow, ...] = Field(
        min_length=1, max_length=24, description="Rows of two factor returns"
    )


def _inputs(width: int) -> type[PanelInputs]:
    return PanelInputs if width == 4 else NarrowInputs


class PanelOutputs(ModelOutputs):
    first: Return = Field(ge=-10, le=10, description="The first asset's last return")


def _table(
    table_id: str, names: tuple[str, ...], months: int, gap: tuple[int, int] | None
) -> Table:
    meta = TableMeta(
        provider="ken_french",
        table_id=table_id,
        title=table_id,
        frequency=ObservationFrequency.MONTHLY,
        source_dating=DateConvention.PERIOD_END,
        terms=HOSTED_TERMS,
    )
    columns = tuple(
        ColumnMeta(
            name=name,
            unit=UnitRecord(text="Return", kind=UnitKind.RETURN),
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        )
        for name in names
    )
    index = tuple(month_end(2025, m) for m in range(1, months + 1))
    data = tuple(
        tuple(
            None if gap == (row, column) else 0.01 * (column + 1) + 0.001 * row
            for row in range(months)
        )
        for column in range(len(names))
    )
    return Table(index, columns, data, meta)


def _french(gap: tuple[int, int] | None = None) -> Any:  # noqa: ANN401 - a provider
    """Industries through December 2025, factors only through November."""
    return scripted(
        "ken_french",
        {
            "industry12:monthly": _table("industry12", INDUSTRIES, 12, gap),
            "ff3:monthly": _table("ff3", FACTORS, 11, None),
        },
    )


def _panel(
    *,
    columns: tuple[str, ...] = ("Mkt-RF", "SMB"),
    width: int = 4,
    returns: str = "portfolios.industry12.us.monthly",
    bindings: tuple[Binding, ...] | None = None,
) -> Any:  # noqa: ANN401 - a model
    declared = bindings or (
        Binding("returns", returns, as_of=AsOf.WINDOW, window=6),
        Binding(
            "factors",
            "factors.ff3.us.monthly",
            as_of=AsOf.WINDOW,
            window=6,
            columns=columns,
        ),
        Binding(
            "market",
            "factors.ff3_market.us.monthly",
            as_of=AsOf.WINDOW,
            window=6,
        ),
    )

    def panel(inputs: PanelInputs) -> PanelOutputs:
        return PanelOutputs(first=inputs.returns[-1][0])

    # The inputs class depends on the width: set it before the decorator reads it.
    panel.__annotations__ = {"inputs": _inputs(width), "return": PanelOutputs}
    return model(
        id="asset_pricing.toy_panel",
        version=1,
        title="Toy panel",
        summary="Reads a panel of returns and factors bound to the catalog.",
        formula=(r"r = r",),
        assumptions=("A toy.",),
        limitations=("It models nothing.",),
        references=(
            Reference(
                key="toy2026",
                citation="A toy source for the matrix tests (2026).",
                url="https://www.example.org/toy",
                locator="Table 1",
            ),
        ),
        evidence=Evidence.PRACTITIONER,
        cost=CostClass.INSTANT,
        changelog=(ChangelogEntry(version=1, note="First version."),),
        invariants=(Invariant(id="reads", statement="It reads the panel."),),
        examples=(
            Example(
                name="one",
                inputs={"returns": [[0.1]], "factors": [[0.1]], "market": [0.1]},
            ),
        ),
        bindings=declared,
    )(panel)


def _value(column: int, row: int) -> float:
    return 0.01 * (column + 1) + 0.001 * row


def test_a_matrix_reads_rows_of_the_table_ending_with_the_series_windows() -> None:
    bound = bind_model(_panel(), as_of=AS_OF, registry=registry_of(_french()))
    # The factors end in November, so every monthly window does: rows 5 to 10.
    assert bound.values["returns"] == tuple(
        tuple(_value(c, r) for c in range(len(INDUSTRIES))) for r in range(5, 11)
    )
    assert bound.values["factors"] == tuple(
        (_value(0, r), _value(1, r)) for r in range(5, 11)
    )
    assert bound.values["market"] == tuple(_value(0, r) for r in range(5, 11))
    records = {record.field: record for record in bound.sources}
    assert set(records) == {"returns", "factors", "market"}
    for record in records.values():
        assert record.observation_start == month_end(2025, 6)
        assert record.observation_end == month_end(2025, 11)
        assert record.transforms[-1] == "window(count=6,date=2025-11-30)"
    assert records["returns"].concept == "portfolios.industry12.us.monthly"
    assert records["factors"].provider == "ken_french"
    result = run_model(_panel(), bound)
    assert result.outputs.first == _value(0, 10)


def test_no_columns_keeps_every_column_in_the_tables_order() -> None:
    bound = bind_model(_panel(columns=()), as_of=AS_OF, registry=registry_of(_french()))
    factors = bound.values["factors"]
    assert isinstance(factors, tuple)
    assert all(len(row) == len(FACTORS) for row in factors)


def test_the_columns_are_kept_in_the_order_the_binding_names() -> None:
    bound = bind_model(
        _panel(columns=("RF", "Mkt-RF")), as_of=AS_OF, registry=registry_of(_french())
    )
    assert bound.values["factors"] == tuple(
        (_value(3, r), _value(0, r)) for r in range(5, 11)
    )


def test_a_column_the_table_lacks_is_refused() -> None:
    with pytest.raises(InputError, match="has no column 'UMD'; its columns: Mkt-RF"):
        bind_model(
            _panel(columns=("Mkt-RF", "UMD")),
            as_of=AS_OF,
            registry=registry_of(_french()),
        )


def test_more_columns_than_a_row_takes_are_refused() -> None:
    with pytest.raises(InputError, match="exceed the 2 a row of the field takes"):
        bind_model(
            _panel(columns=(), width=2), as_of=AS_OF, registry=registry_of(_french())
        )


def test_a_missing_value_in_the_window_raises() -> None:
    with pytest.raises(DataError, match="missing a value in the last 6"):
        bind_model(_panel(), as_of=AS_OF, registry=registry_of(_french(gap=(7, 1))))


def test_the_shared_end_keeps_a_later_gap_out_of_the_window() -> None:
    # December's Manuf return is missing, but the factors end in November, so
    # every monthly window does, and December is never read.
    bound = bind_model(
        _panel(), as_of=AS_OF, registry=registry_of(_french(gap=(11, 2)))
    )
    (record,) = [r for r in bound.sources if r.field == "returns"]
    assert record.observation_end == month_end(2025, 11)


def test_a_gap_in_the_last_rows_on_the_date_raises_as_a_series_does() -> None:
    with pytest.raises(DataError, match="missing a value"):
        bind_model(
            _panel(),
            as_of=AS_OF,
            overrides={"factors": ((0.0, 0.0),) * 6, "market": (0.0,) * 6},
            registry=registry_of(_french(gap=(11, 2))),
        )


def test_the_caller_can_supply_the_matrix() -> None:
    given = ((0.01, 0.02, 0.03),) * 6
    bound = bind_model(
        _panel(),
        as_of=AS_OF,
        overrides={"returns": given},
        registry=registry_of(_french()),
    )
    by_field = {record.field: record for record in bound.sources}
    assert by_field["returns"].provider == "user"
    assert bound.values["returns"] == given


def test_a_series_concept_cannot_fill_a_matrix() -> None:
    toy = _panel(returns="factors.ff3_smb.us.monthly")
    registry = Registry.from_models(toy, distribution="toy-dist")
    with pytest.raises(
        RegistryError, match="is a series; a matrix field reads a table"
    ):
        validate_bindings(registry)
    with pytest.raises(InputError, match="a matrix field reads a table's rows"):
        bind_model(toy, as_of=AS_OF, registry=registry_of(_french()))


def test_the_card_names_the_columns() -> None:
    card = ModelCard.from_model(_panel()).to_markdown()
    assert "`factors`, columns `Mkt-RF`, `SMB`" in card


@pytest.mark.parametrize(
    ("binding", "problem"),
    [
        (
            Binding(
                "market",
                "factors.ff3_market.us.monthly",
                as_of=AsOf.WINDOW,
                window=6,
                columns=("Mkt-RF",),
            ),
            "columns go with a matrix field",
        ),
        (
            Binding(
                "factors",
                "factors.ff3.us.monthly",
                as_of=AsOf.WINDOW,
                window=6,
                columns=("SMB", "SMB"),
            ),
            "names a column twice",
        ),
        (
            Binding(
                "factors",
                "factors.ff3.us.monthly",
                as_of=AsOf.WINDOW,
                window=6,
                columns=("Mkt-RF", "SMB", "HML", "RF", "X"),
            ),
            "5 columns exceed the 4",
        ),
        (
            Binding(
                "factors",
                "factors.ff3.us.monthly",
                transform="lag",
                as_of=AsOf.WINDOW,
                window=6,
            ),
            "a matrix binding takes no transform",
        ),
        (
            Binding(
                "factors",
                "factors.ff3.us.monthly",
                as_of=AsOf.WINDOW,
                window=6,
                columns=("",),
            ),
            "columns is a tuple of column names",
        ),
        (
            Binding("factors", "factors.ff3.us.monthly"),
            "an array field needs the 'window' rule",
        ),
    ],
)
def test_the_registry_holds_a_matrix_binding_to_its_rules(
    binding: Binding, problem: str
) -> None:
    toy = _panel(
        bindings=(
            binding,
            Binding(
                "market",
                "factors.ff3_market.us.monthly",
                as_of=AsOf.WINDOW,
                window=6,
                profile="other",
            ),
        )
        if binding.field != "market"
        else (binding,)
    )
    registry = Registry.from_models(toy, distribution="toy-dist")
    details = [p.detail for p in registry.problems(released={}) if p.rule == "bindings"]
    assert any(problem in detail for detail in details), details


def test_a_columns_list_and_a_curve_with_columns_are_refused() -> None:
    listed = Binding(
        "factors",
        "factors.ff3.us.monthly",
        as_of=AsOf.WINDOW,
        window=6,
        columns=["Mkt-RF"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )
    curve = Binding(
        "returns", "us.treasury.par_curve", tenors="market", columns=("1m",)
    )
    registry = Registry.from_models(
        _panel(bindings=(listed, curve)), distribution="toy-dist"
    )
    details = [p.detail for p in registry.problems(released={}) if p.rule == "bindings"]
    assert any("columns is a tuple of column names" in d for d in details), details
    assert any("a curve's binding takes no columns" in d for d in details), details
    assert any("a curve's values go to an array field" in d for d in details), details


class _MatrixMember(ModelInputs):
    calculation: Literal["rows"] = Field("rows", description="Rows")
    returns: tuple[_Row, ...] = Field(
        min_length=1, max_length=24, description="Rows of returns"
    )


class _VectorMember(ModelInputs):
    calculation: Literal["values"] = Field("values", description="Values")
    returns: Annotated[tuple[_Value, ...], ARRAY_INPUT] = Field(
        min_length=1, max_length=24, description="A list of returns"
    )


def test_a_field_that_is_a_matrix_in_one_calculation_only_is_refused() -> None:
    def mixed(inputs: Any) -> PanelOutputs:  # noqa: ANN401 - a union
        return PanelOutputs(first=0.0 * len(inputs.returns))

    mixed.__annotations__ = {
        "inputs": Annotated[
            _MatrixMember | _VectorMember, Field(discriminator="calculation")
        ],
        "return": PanelOutputs,
    }
    toy = model(
        id="asset_pricing.toy_mixed",
        version=1,
        title="Toy mixed",
        summary="A field that is a matrix in one calculation and a list in another.",
        formula=(r"r = r",),
        assumptions=("A toy.",),
        limitations=("It models nothing.",),
        references=(
            Reference(
                key="toy2026",
                citation="A toy source for the matrix tests (2026).",
                url="https://www.example.org/toy",
                locator="Table 1",
            ),
        ),
        evidence=Evidence.PRACTITIONER,
        cost=CostClass.INSTANT,
        changelog=(ChangelogEntry(version=1, note="First version."),),
        invariants=(Invariant(id="reads", statement="It reads."),),
        examples=(
            Example(name="rows", inputs={"calculation": "rows", "returns": [[0.1]]}),
            Example(name="values", inputs={"calculation": "values", "returns": [0.1]}),
        ),
        bindings=(
            Binding(
                "returns",
                "portfolios.industry12.us.monthly",
                as_of=AsOf.WINDOW,
                window=6,
            ),
        ),
    )(mixed)
    registry = Registry.from_models(toy, distribution="toy-dist")
    details = [p.detail for p in registry.problems(released={}) if p.rule == "bindings"]
    assert any("a matrix in one calculation" in d for d in details), details
