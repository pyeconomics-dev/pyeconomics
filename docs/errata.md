# Errata

## 2026-10-14: IRR roots at inclusive bracket endpoints (#85)

Affected: version 1 of `foundations.time_value`,
`corporate.capital_budgeting` and `performance.return_measurement`, including
package `1.0.0a1`. Corrected in package `1.0.0a2.dev1`, version 2 of those
models. Their permanent ids are unchanged.

Version 1 could return null/no_root_in_range for an IRR at the inclusive
bounds -0.99 or 10.0. Version 2 recognizes these roots; permanent model ids
and the smallest-root selection policy are unchanged. The one-period cash
flows `[-100, 1]` and `[-1000000, 11000000]` give -0.99 and 10.0 respectively
from the identity `r = final_receipt / initial_outlay - 1`. Log-scaled NPV
evaluation had rounded the endpoint away from zero. The correction accepts
an endpoint only when local evaluations certify a root within the existing
rate tolerance; roots materially outside the bracket stay refused.

Regression golden cases, rescaling tests and a property test over chosen
rates including both bounds guard the correction. See
[issue #85](https://github.com/pyeconomics-dev/pyeconomics/issues/85).

## 2026-10-12: US 30/360 long first-period accrual (#89)

Affected: package `1.0.0a1.dev1`; version 1 of `fixed_income.bond_pricing`,
`fixed_income.duration`, and `fixed_income.convexity`. Corrected in package
`1.0.0a1.dev2`, version 2 of those models. Their permanent ids are unchanged.

Long first periods were split at a notional coupon date for all day counts.
US 30/360 endpoint adjustments are not always additive across that date, so
this could change the first coupon, accrued interest, discount times, prices,
solved yields and duration/convexity, including calculations off a spot curve.
The correction measures each 30/360 accrual interval as a whole and retains
the reference-period split required by ACT/ACT ICMA.

For a zero-coupon annual bond issued 1993-05-30, settling 1994-05-31 and
maturing 1995-04-15 under US 30/360 at a 5% yield, Macaulay duration was
0.8722222222222222 years and full price was 95.83369261359005. Correct values
are 0.875 years and 95.8207053225834. The whole period is 675/360 years and
the elapsed accrual is 360/360, leaving 315/360 years. These values agree
with QuantLib 1.43's
[US day counter](https://github.com/lballabio/QuantLib/blob/v1.43/ql/time/daycounters/thirty360.cpp)
and [stepwise discount timing](https://github.com/lballabio/QuantLib/blob/v1.43/ql/cashflows/cashflows.cpp).
Deterministic oracle tests and independent golden cases guard the correction;
see [issue #89](https://github.com/pyeconomics-dev/pyeconomics/issues/89).

Report an incorrect model result using the
[bug report form](https://github.com/pyeconomics-dev/pyeconomics/issues/new?template=bug.yml).
Include the model id and version, inputs, expected output with a public source
and locator, actual output, and the package version. Remove private data and
credentials before sharing an example or manifest.

A model error receives the `model-error` label and High severity. The correction
includes a regression golden case and a public erratum describing affected
versions, the incorrect behavior and the corrected result. Permanent model ids
stay unchanged; the model version and changelog record the correction.
