---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
---

# Your first model

This lesson follows {doc}`install`. It is a notebook that runs during every
documentation build, and it uses only local inputs. We will calculate a
holding-period return, inspect its evidence and make a table.

```{code-cell} ipython3
:tags: [remove-cell]

# Keep model and notebook execution offline after the local kernel starts.
from pytest_socket import disable_socket

disable_socket()
```

An investment starts at 100, ends at 108 and pays 2 in income. Its total return
is `(108 - 100 + 2) / 100`, or ten percent.

```{code-cell} ipython3
import pyeconomics

result = pyeconomics.run(
    "foundations.returns",
    calculation="holding_period",
    beginning_value=100,
    ending_value=108,
    income=2,
)
assert result.outputs.holding_period_return == 0.1
result.outputs
```

The card states the formula, variables, assumptions, limitations and sources.

```{code-cell} ipython3
from IPython.display import Markdown, display

display(Markdown(result.card().to_markdown()))
```

A table keeps inputs and outputs in separate columns and includes the result's
hash. The manifest has no timestamp, user, host or environment values.

```{code-cell} ipython3
table = result.to_pandas()
assert table.loc[0, "outputs.holding_period_return"] == 0.1
table
```

This example is educational, not investment advice. It describes a hypothetical
investment and makes no claim about future performance.

## Next

Every model has a page like that card in the
{doc}`model reference </reference/models/index>`, and a page on
[pyeconomics.dev](https://pyeconomics.dev/models/) with a calculator.
{doc}`data-and-keys` replaces the typed numbers with data from a real source.
