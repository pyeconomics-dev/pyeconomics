#!/usr/bin/env bash
# scripts/verify-phase02.sh
#
# Phase 2 verification: 66 independent static checks and the V1-V15 matrix.
# --fast (default): static checks; --python: tests, docs, artifacts and smoke;
# --security: whole-tree gate; --live: authenticated/public service reads;
# --all: fast + python + security; --post: all + live + published installs,
# alarm evidence, Phase 1 post verification and current PR checks.
# Run from the repository. No credential or environment value is printed.

set -uo pipefail
# Associative arrays need bash 4; under macOS's /bin/bash 3.2 the script would
# stop at its first check and exit 0 (#217), so refuse to run instead.
[ "${BASH_VERSINFO[0]:-0}" -ge 4 ] || {
  echo "verify needs bash >= 4 (brew install bash)" >&2
  exit 2
}
REPO="${VERIFY_REPO:-pyeconomics-dev/pyeconomics}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 2
cd "$ROOT" || exit 2
export MSYS_NO_PATHCONV=1
ROADMAP=docs/roadmap/phase02-roadmap.md
QA=docs/phase02-qa-findings.md
usage() {
  sed -n '4,9p' "$0" | sed 's/^# \{0,1\}//'
}

MODE="${1:---fast}"
case "$MODE" in
  --fast | --python | --security | --live | --all | --post) ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    usage >&2
    exit 2
    ;;
esac

# A Python 3.11+ for tomllib/json/ast; the Windows Store stub fails -c.
PY=""
for candidate in python3 python; do
  if command -v "$candidate" > /dev/null 2>&1 \
    && "$candidate" -c 'import sys, tomllib; sys.exit(0)' > /dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "verify-phase02.sh: needs python3 (3.11 or later) on PATH" >&2
  exit 2
fi

TMP="$(mktemp -d)"
# Git Bash: a mixed path (E:/...) means the same directory to bash and to
# native tools, which see paths unconverted under MSYS_NO_PATHCONV.
if command -v cygpath > /dev/null 2>&1; then TMP="$(cygpath -m "$TMP")"; fi
# Keep a crash's exit status: the trap's own status must not become the
# script's (#217).
trap 'rc=$?; rm -rf "$TMP"; exit $rc' EXIT

# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

declare -A RESULT     # static check number -> PASS/FAIL
declare -A MODE_PASS  # mode -> passed count
declare -A MODE_FAIL  # mode -> failed count
CURRENT_MODE=fast
FAILED=0

record() { # record <PASS|FAIL> <id> <description> [detail]
  local status=$1 id=$2 desc=$3 detail=${4:-}
  if [ "$status" = PASS ]; then
    MODE_PASS[$CURRENT_MODE]=$((${MODE_PASS[$CURRENT_MODE]:-0} + 1))
  else
    MODE_FAIL[$CURRENT_MODE]=$((${MODE_FAIL[$CURRENT_MODE]:-0} + 1))
    FAILED=1
  fi
  if [ -n "$detail" ]; then
    printf '%s  %-6s %s (%s)\n' "$status" "$id" "$desc" "$detail"
  else
    printf '%s  %-6s %s\n' "$status" "$id" "$desc"
  fi
}

# check <n> <description> <function>: runs a static check in a subshell so
# each one is independent; its stdout becomes the FAIL detail.
check() {
  local n=$1 desc=$2 fn=$3 out
  shift 3
  if out="$("$fn" "$@" 2>&1)"; then
    RESULT[$n]=PASS
    record PASS "$n" "$desc"
  else
    RESULT[$n]=FAIL
    record FAIL "$n" "$desc" "$(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"
  fi
}

# vcheck <id> <description> <function>: a V-check that runs commands.
vcheck() {
  local id=$1 desc=$2 fn=$3 out
  if out="$($fn 2>&1)"; then
    record PASS "$id" "$desc"
  else
    # The failing lines (a prek hook's "Failed", an error), else the tail.
    local why
    why=$(printf '%s\n' "$out" | grep -E 'Failed$|[Ee]rror|FAIL' | head -n 5)
    [ -n "$why" ] || why=$(printf '%s\n' "$out" | tail -n 5)
    record FAIL "$id" "$desc" "$(printf '%s' "$why" | tr '\n' ' ' | cut -c1-240)"
  fi
}

# vstatic <id> <description> <first> <last>: a V-check over static checks.
vstatic() {
  local id=$1 desc=$2 first=$3 last=$4 n bad=""
  for n in $(seq "$first" "$last"); do
    [ "${RESULT[$n]:-FAIL}" = PASS ] || bad="$bad $n"
  done
  if [ -z "$bad" ]; then
    record PASS "$id" "$desc"
  else
    record FAIL "$id" "$desc" "failed:$bad"
  fi
}

section() { printf '\n== %s ==\n' "$1"; }

fail() { # print a reason and end the check (each runs in a subshell)
  echo "$*"
  exit 1
}

tracked() { [ -n "$(git ls-files -- "$1")" ]; }


# Stdlib only: --fast never installs or imports the package/development tools.
# Checks run in independent subprocesses, so one failure cannot hide another.
static_check() {
  "$PY" - "$1" << 'PY'
import ast
import re
import subprocess
import sys
import tomllib
from pathlib import Path

n = int(sys.argv[1])
def text(path):
    return Path(path).read_text(encoding="utf-8")
def files(*paths):
    assert all(Path(p).is_file() for p in paths), paths
def contains(path, *tokens):
    body = text(path)
    assert all(token in body for token in tokens), (path, tokens)
def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()
def definitions(path, names, kind=ast.FunctionDef):
    nodes = ast.parse(text(path)).body
    assert set(names) <= {x.name for x in nodes if isinstance(x, kind)}, path
project = tomllib.loads(text("pyproject.toml"))
deps = project["project"]["dependencies"]
groups = project["dependency-groups"]
extras = project["project"]["optional-dependencies"]
entry = project["project"]["entry-points"]["pyeconomics.models"]
core = "src/pyeconomics/core/"
ci = text(".github/workflows/ci.yml")
def dependency(items, name):
    return any(isinstance(x, str) and re.match(re.escape(name) + r"(?:[>=<;\[]|$)", x, re.I) for x in items)
catalog = {
    "foundations": "time_value returns risk_statistics hypothesis_tests simulation",
    "fixed_income": "bond_pricing money_market curve_bootstrap duration convexity credit_spread",
    "derivatives": "forwards interest_rate_swap black_scholes_merton binomial_tree futures_fx_options",
    "international": "parity_conditions",
    "equity": "dividend_discount free_cash_flow",
    "corporate": "cost_of_capital capital_budgeting leverage",
    "accounting": "financial_ratios scoring_models",
    "portfolio": "mean_variance utility",
    "performance": "return_measurement risk_adjusted brinson_attribution",
    "risk": "value_at_risk var_backtest",
    "econometrics": "ols",
}
def entries(*domains):
    assert all(d in entry for d in domains), domains
def models(*domains):
    for d in domains:
        body = "\n".join(p.read_text(encoding="utf-8") for p in Path("src/pyeconomics/models", d).glob("*.py"))
        declared = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)', body))
        assert {d + "." + name for name in catalog[d].split()} <= declared, d
def goldens(*domains):
    for d in domains:
        files(*(f"tests/golden/{d}/{name}.toml" for name in catalog[d].split()))

if n == 1: assert git("ls-files", "--", "docs/roadmap/phase02-roadmap.md")
elif n == 2:
    adr = text("docs/adr/0008-numerical-conventions.md")
    assert "Status: Accepted" in adr
    date = re.search(r"^- Date: (\S+)", adr, re.M).group(1)
    rows = [s for s in text("docs/adr/README.md").splitlines() if "[0008]" in s]
    assert any("Accepted" in row and date in row for row in rows)
elif n == 3:
    body = text("docs/adr/0008-numerical-conventions.md").split("## Decision outcome", 1)[1].split("### Consequences", 1)[0]
    assert set(range(1, 15)) <= {int(x) for x in re.findall(r"^### (\d+)\.", body, re.M)}
elif n == 4:
    for name in ("pydantic", "numpy", "scipy", "pandas"):
        requirement = next(x for x in deps if x.startswith(name + ">="))
        assert "<" not in requirement
elif n == 5:
    entries_ = tomllib.loads(text("scripts/checks/licence_exceptions.toml")).get("exception", [])
    excluded = {"financepy", "rateslib", "getfactormodels", "dbnomics", "full-fred", "openbb"}
    for item in entries_:
        assert all(isinstance(item.get(k), str) and item[k].strip() for k in ("package", "licence", "reason"))
        assert item["package"].lower().replace("_", "-") not in excluded
elif n == 6:
    files(*(core + s + ".py" for s in "units rates compounding tolerance random numerics errors warnings".split()))
    tree = ast.parse(text(core + "warnings.py"))
    warning = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "PyeconomicsDeprecationWarning")
    assert any(isinstance(b, ast.Name) and b.id == "FutureWarning" for b in warning.bases)
elif n == 7:
    cff = text("CITATION.cff")
    assert re.search(r'^version:\s*["\']?' + re.escape(project["project"]["version"]) + r'["\']?\s*$', cff, re.M)
    assert re.search(r'^license:\s*["\']?Apache-2\.0["\']?\s*$', cff, re.M)
elif n in (8, 35):
    job = "pyodide" if n == 8 else "docs"
    assert re.search(r"^  " + job + r":", ci, re.M)
    aggregate = ci.split("\n  test:\n", 1)[1]
    assert job in re.search(r"needs:\s*\[([^]]+)\]", aggregate).group(1).split(", ")
    if n == 8:
        files("scripts/smoke.py")
        assert "smoke.py" in ci.split("\n  package:\n", 1)[1].split("\n  pyodide:", 1)[0]
    else: assert re.search(r"sphinx-build\s+-W", ci.split("\n  docs:\n", 1)[1])
elif n == 9: contains(core + "daycount.py", *"THIRTY_360_US THIRTY_E_360 ACT_360 ACT_365_FIXED ACT_ACT_ISDA ACT_ACT_ICMA".split())
elif n == 10:
    contains(core + "calendars.py", *"UNADJUSTED FOLLOWING MODIFIED_FOLLOWING PRECEDING MODIFIED_PRECEDING".split())
    files(core + "schedule.py")
elif n == 11: assert dependency(deps, "holidays") and dependency(groups["test"], "quantlib")
elif n == 12:
    for name in ("daycount", "calendars"):
        contains(f"tests/unit/core/test_{name}.py", "import QuantLib")
elif n == 13:
    definitions("src/pyeconomics/registry.py", "ids get models domains resolve".split())
    tree = ast.parse(text("src/pyeconomics/registry.py"))
    assert any(isinstance(x, ast.ImportFrom) and any(a.name == "validate" for a in x.names) for x in tree.body)
elif n == 14:
    definitions(core + "spec.py", "ModelSpec Reference Invariant Example CostClass Evidence".split(), ast.ClassDef)
    contains(core + "spec.py", *('"' + s + '"' for s in "standard practitioner contested rejected historical".split()))
elif n == 15: contains(core + "registry.py", "pyeconomics.models", "entry_points")
elif n == 16: files(".semgrep/rules/model-purity.yaml", ".semgrep/tests/model-purity.py")
elif n == 17: files(core + "_released.py")
elif n == 18: files("tests/registry/test_validate_rules.py", "tests/registry/test_model_imports.py")
elif n == 19:
    contains("src/pyeconomics/__init__.py", "run", "run_batch")
    files(*(core + s + ".py" for s in "results manifest canonical schema cards".split()))
elif n == 20: contains("tests/results/test_canonical.py", "RFC 8785", "Appendix B")
elif n in (21, 55):
    extra, package = ("plot", "plotly") if n == 21 else ("econometrics", "statsmodels")
    assert dependency(extras[extra], package) and dependency(extras["all"], package)
elif n == 22: assert all(dependency(groups["test"], p) for p in ("jsonschema", "rfc8785"))
elif n == 23: contains(".github/workflows/release-smoke.yml", "smoke.py", "--min-domains")
elif n == 24: contains(core + "schema.py", "https://json-schema.org/draft/2020-12/schema")
elif n == 25: files("tests/golden/README.md", "tests/golden/test_golden.py")
elif n == 26:
    markers = project["tool"]["pytest"]["ini_options"]["markers"]
    assert all(any(m.startswith(s + "(") for m in markers) for s in ("invariant", "oracle"))
    files("tests/models/test_invariant_coverage.py")
elif n == 27:
    tree = ast.parse(text("scripts/checks/coverage_floors.py"))
    value = next(x.value for x in tree.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) and x.target.id == "FLOORS")
    floors = {name: bound for name, _, bound in ast.literal_eval(value)}
    assert floors["core"] >= 95 and floors["models"] >= 90
    assert "scripts/checks/coverage_floors.py" in ci
elif n == 28: contains("CONTRIBUTING.md", "Model definition of done", "tests/golden/", "invariant")
elif n == 29: contains(".github/pull_request_template.md", "## Model checklist")
elif n == 30: files("tests/golden/test_sources.py")
elif n == 31:
    entries("foundations")
    contains("scripts/checks/dist_contents.py", "entry_points\\.txt")
elif n in (32, 33): (models if n == 32 else goldens)("foundations")
elif n == 34:
    files("docs/conf.py", "docs/index.md", ".readthedocs.yaml")
    assert re.search(r"^\s+fail_on_warning:\s*true\s*$", text(".readthedocs.yaml"), re.M)
elif n == 36:
    assert all(dependency(groups["docs"], p) for p in ("sphinx", "myst-nb", "sphinx-autoapi", "pydata-sphinx-theme"))
    assert dependency(groups["test"], "sybil")
elif n == 37:
    contains("docs/conftest.py", "Sybil(")
    contains("docs/conf.py", '"roadmap/**"', '"adr/**"', '"releases/**"')
elif n == 38:
    files("docs/errata.md")
    notice = next(s.strip('"') for s in re.findall(r'"CFA[^"\n]+"', text("docs/roadmap/ROADMAP.md")))
    contains("docs/notices.md", notice, "not investment advice")
elif n == 39:
    tail = text("docs/roadmap/phase01-roadmap.md").split("## Post-merge addendum", 1)[1]
    assert "Static check 44" in tail and "Static check 19" in tail
elif n == 40: entries("fixed_income")
elif n in (41, 42): (models if n == 41 else goldens)("fixed_income")
elif n == 43:
    entries("derivatives", "international")
    assert dependency(groups["test"], "vollib")
elif n in (44, 45): (models if n == 44 else goldens)("derivatives", "international")
elif n == 46: entries("equity", "corporate", "accounting")
elif n in (47, 48): (models if n == 47 else goldens)("equity", "corporate", "accounting")
elif n == 49: entries("portfolio", "performance")
elif n in (50, 51): (models if n == 50 else goldens)("portfolio", "performance")
elif n == 52: entries("risk", "econometrics")
elif n == 53: models("risk", "econometrics")
elif n == 54:
    goldens("risk", "econometrics")
    contains("tests/golden/econometrics/ols.toml", "NIST", "Statistical Reference Datasets")
elif n == 56:
    body = text("docs/releases/1.0.0a1-readiness.md")
    assert set(range(1, 12)) <= {int(x) for x in re.findall(r"^## (\d+)\.", body, re.M)}
    assert re.search(r"^Decision: GO", body, re.M)
    assert not re.search(r"\|\s*FAIL\s*\||^FAIL\b", body, re.M)
elif n == 57:
    files("scripts/checks/python_floor.py")
    tags = git("tag", "--merged", "origin/main", "--list", "v1.0.0a1.dev*")
    assert tags
elif n == 58:
    subprocess.check_call(["git", "merge-base", "--is-ancestor", "v1.0.0a1", "origin/main"])
elif n == 59: assert re.search(r"^## \[1\.0\.0a1\] - \d{4}-\d{2}-\d{2}", text("CHANGELOG.md"), re.M)
elif n == 60:
    files("scripts/release_ledger.py")
    ledger = text(core + "_released.py")
    for domain, names in catalog.items():
        assert all('"' + domain + "." + name + '"' in ledger for name in names.split())
elif n == 61: contains("docs/releases/1.0.0a1.md", "https://pyeconomics.readthedocs.io/en/main/")
elif n == 62:
    files("scripts/verify-phase02.sh")
    assert git("ls-files", "--stage", "--", "scripts/verify-phase02.sh").startswith("100755 ")
elif n == 63: files("docs/phase02-qa-findings.md")
elif n == 64: files("docs/roadmap/phase02-roadmap.md")
elif n == 65:
    matrices = re.findall(r"^\s+phase:\s*\[([^]]+)\]\s*$", text(".github/workflows/phase-verify.yml"), re.M)
    assert len(matrices) >= 2 and all('"02"' in m for m in matrices)
else: raise ValueError(n)
PY
}

c66() {
  # Patterns are assembled at run time so this file never matches itself.
  local dashes pem aws ghp pypi hits
  dashes=$(printf -- '-%.0s' 1 2 3 4 5)
  pem="${dashes}BEGIN ([A-Z0-9]+ )*PRIVATE KEY${dashes}"
  aws='(AKIA|ASIA)[0-9A-Z]{16}'
  ghp='(gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})'
  pypi='pypi-AgE[A-Za-z0-9_-]{50,}'
  hits=$(git grep -lIE "$pem|$aws|$ghp|$pypi" -- . 2> /dev/null || true)
  [ -z "$hits" ] || fail "credential pattern in: $hits"
  local hook
  for hook in gitleaks bandit semgrep pip-audit licences zizmor; do
    grep -qE "^[[:space:]]+- id: $hook$" .pre-commit-config.yaml || fail "missing $hook hook"
  done
  [ -f .github/workflows/security.yml ] || fail "security workflow missing"
}

run_static() {
  CURRENT_MODE=fast
  section "Static checks 1-66"
  check 1 "Phase 2 roadmap tracked" static_check 1
  check 2 "ADR-0008 accepted and indexed with date" static_check 2
  check 3 "Fourteen numerical decisions" static_check 3
  check 4 "Runtime baseline has lower bounds only" static_check 4
  check 5 "Licence exceptions justified; exclusions respected" static_check 5
  check 6 "Core conventions and FutureWarning deprecation" static_check 6
  check 7 "Citation version and licence" static_check 7
  check 8 "Pyodide aggregate and package smoke" static_check 8
  check 9 "Six day counts" static_check 9
  check 10 "Five business conventions and schedules" static_check 10
  check 11 "holidays runtime and QuantLib test dependency" static_check 11
  check 12 "Date/calendar QuantLib oracles" static_check 12
  check 13 "Registry facade APIs" static_check 13
  check 14 "Spec types and evidence vocabulary" static_check 14
  check 15 "Entry-point discovery" static_check 15
  check 16 "Purity rule and fixtures" static_check 16
  check 17 "Released-id module" static_check 17
  check 18 "Registry validation and import tests" static_check 18
  check 19 "Run APIs and result modules" static_check 19
  check 20 "RFC 8785 vectors" static_check 20
  check 21 "Plot extra included in all" static_check 21
  check 22 "Schema and JCS test oracles" static_check 22
  check 23 "Release smoke min-domains" static_check 23
  check 24 "2020-12 schema dialect" static_check 24
  check 25 "Golden harness and format" static_check 25
  check 26 "Invariant/oracle markers and meta-test" static_check 26
  check 27 "Core/models coverage floors in CI" static_check 27
  check 28 "Contributor model quality rules" static_check 28
  check 29 "PR model checklist" static_check 29
  check 30 "Citation guard" static_check 30
  check 31 "Foundations discovery and packaged entry points" static_check 31
  check 32 "Foundations ids" static_check 32
  check 33 "Foundations goldens" static_check 33
  check 34 "Docs and RTD warnings-as-errors" static_check 34
  check 35 "Docs job required by test aggregate" static_check 35
  check 36 "Docs tools and Sybil" static_check 36
  check 37 "Sybil and docs exclusions" static_check 37
  check 38 "Errata and legal notices" static_check 38
  check 39 "Phase 1 cross-phase addendum" static_check 39
  check 40 "Fixed-income entry point" static_check 40
  check 41 "Fixed-income ids" static_check 41
  check 42 "Fixed-income goldens" static_check 42
  check 43 "Derivatives/international discovery and vollib" static_check 43
  check 44 "Derivatives/international ids" static_check 44
  check 45 "Derivatives/international goldens" static_check 45
  check 46 "Equity/corporate/accounting discovery" static_check 46
  check 47 "Equity/corporate/accounting ids" static_check 47
  check 48 "Equity/corporate/accounting goldens" static_check 48
  check 49 "Portfolio/performance discovery" static_check 49
  check 50 "Portfolio/performance ids" static_check 50
  check 51 "Portfolio/performance goldens" static_check 51
  check 52 "Risk/econometrics discovery" static_check 52
  check 53 "Risk/econometrics ids" static_check 53
  check 54 "Risk/econometrics goldens and NIST" static_check 54
  check 55 "Econometrics extra included in all" static_check 55
  check 56 "Readiness GO with no unresolved FAIL" static_check 56
  check 57 "Floor checker and merged rehearsal tag" static_check 57
  check 58 "Merged alpha tag" static_check 58
  check 59 "Dated alpha changelog" static_check 59
  check 60 "All launch ids in released ledger" static_check 60
  check 61 "Release notes link preview" static_check 61
  check 62 "Executable verifier in git index" static_check 62
  check 63 "QA findings document" static_check 63
  check 64 "Phase roadmap exists" static_check 64
  check 65 "Both CI matrices include 02" static_check 65
  check 66 "Whole-tree credential backstop and security hooks" c66
  vstatic V1.1 "Step 1 deliverables" 1 8
  vstatic V2.1 "Step 2 deliverables" 9 12
  vstatic V3.1 "Step 3 deliverables" 13 18
  vstatic V4.1 "Step 4 deliverables" 19 24
  vstatic V5.1 "Step 5 deliverables" 25 30
  vstatic V6.1 "Step 6 deliverables" 31 33
  vstatic V7.1 "Step 7 deliverables" 34 39
  vstatic V8.1 "Step 8 deliverables" 40 42
  vstatic V9.1 "Step 9 deliverables" 43 45
  vstatic V10.1 "Step 10 deliverables" 46 48
  vstatic V11.1 "Step 11 deliverables" 49 51
  vstatic V12.1 "Step 12 deliverables" 52 55
  vstatic V13.1 "Step 13 deliverables" 56 57
  vstatic V14.1 "Step 14 deliverables" 58 61
  vstatic V15.1 "Fast verifier succeeds" 1 66
  vstatic V15.2 "Both phase matrices include 02" 65 65
  vstatic V15.3 "Every static check passes" 1 66
}

# Commands are grouped by the evidence they actually produce. A suite verdict
# is reused only for V-checks whose tests were included in that suite.
venv_python() {
  if [ -x "$1/bin/python" ]; then echo "$1/bin/python"; else echo "$1/Scripts/python.exe"; fi
}
lint_types() {
  uv sync --locked --all-extras --group docs && uv run --locked ruff format --check \
    && uv run --locked ruff check && uv run --locked mypy
}
suite() {
  HYPOTHESIS_PROFILE=ci uv run --locked pytest --cov --cov-report="json:$TMP/coverage.json" -q \
    && uv run --locked python scripts/checks/coverage_floors.py "$TMP/coverage.json" \
    && (cd "$TMP" && uv run --project "$ROOT" --locked python -c 'from pyeconomics import registry; registry.validate()')
}
docs_build() {
  uv run --locked --group docs --all-extras sphinx-build -E -W --keep-going -b html docs "$TMP/docs" || return 1
  # A successful build alone must not stand in for generated-card coverage.
  (cd "$TMP" && uv run --project "$ROOT" --locked --all-extras python - "$TMP/docs" << 'PY'
import sys
from pathlib import Path
from pyeconomics import registry
root = Path(sys.argv[1]) / "reference" / "models"
for model_id in registry.ids():
    assert (root.joinpath(*model_id.split(".")).with_suffix(".html")).is_file(), model_id
PY
  )
}
artifact_build() {
  uv build --out-dir "$TMP/dist" \
    && uvx --no-config twine==7.0.0 check --strict "$TMP"/dist/* \
    && uv run --no-project python scripts/checks/dist_contents.py "$TMP/dist"
}
wheel_smoke() {
  local py wheel interpreter
  # Match the interpreter that just passed the local suite. uv's global
  # default can otherwise select a different supported minor version.
  interpreter=$(uv python find --no-config) || return 1
  wheel=$(printf '%s\n' "$TMP"/dist/*.whl)
  [ -f "$wheel" ] || fail "build did not produce a wheel"
  mkdir -p "$TMP/smoke" || return 1
  cp scripts/smoke.py "$TMP/smoke/" || return 1
  uv venv --no-config --python "$interpreter" -q "$TMP/core" || return 1
  py=$(venv_python "$TMP/core")
  uv pip install --no-config --python "$py" "$wheel" || return 1
  (cd "$TMP/smoke" && "$py" smoke.py --all --min-domains 11) || return 1
  uv venv --no-config --python "$interpreter" -q "$TMP/extras" || return 1
  py=$(venv_python "$TMP/extras")
  uv pip install --no-config --python "$py" "${wheel}[econometrics,plot]" || return 1
  (cd "$TMP/smoke" && "$py" smoke.py --all --extras --min-domains 11)
}
run_python() {
  CURRENT_MODE=python
  section "--python"
  vcheck TYPES "Locked all-extras/docs environment; format, lint and strict types" lint_types
  local suite_status=PASS id
  suite > "$TMP/suite.log" 2>&1 || suite_status=FAIL
  for id in V1.2 V2.2 V3.2 V4.2 V5.2 V6.2 V8.2 V9.2 V10.2 V11.2 V12.2; do
    record "$suite_status" "$id" "Full socket-isolated suite, registry and coverage floors" "$(log_detail "$TMP/suite.log")"
  done
  vcheck V7.2 "Sphinx warnings-as-errors with executed tutorial; Sybil in suite" docs_build
  vcheck BUILD "Wheel/sdist, strict Twine and artifact allowlist" artifact_build
  local smoke_status=PASS
  wheel_smoke > "$TMP/smoke.log" 2>&1 || smoke_status=FAIL
  record "$smoke_status" V4.3 "Installed-wheel all-model smoke" "$(log_detail "$TMP/smoke.log")"
  record "$smoke_status" V12.3 "Separate clean core/extras installations" "$(log_detail "$TMP/smoke.log")"
}

log_detail() {
  tail -n 4 "$1" | tr '\n' ' ' | cut -c1-400
}

security_gate() {
  uv run --locked prek run semgrep-test --all-files || return 1
  uv run --locked pytest tests/registry/test_model_imports.py -q || return 1
  local skip=""
  [ "$(git rev-parse --abbrev-ref HEAD)" != main ] || skip=no-commit-to-branch
  # The only skip is the roadmap-authorized branch-name guard on main.
  SKIP="$skip" uv run --locked prek run --all-files
}
secret_scan() {
  git clone -q --no-hardlinks "$ROOT" "$TMP/scan" || return 1
  (cd "$TMP/scan" && git checkout -q --orphan gate-secrets-scan \
    && uv run --project "$ROOT" --locked prek run gitleaks --all-files)
}
run_security() {
  CURRENT_MODE=security
  section "--security"
  local status=PASS
  security_gate > "$TMP/gate.log" 2>&1 || status=FAIL
  record "$status" V1.4 "Runtime licences, audit and whole-tree hooks" "$(log_detail "$TMP/gate.log")"
  record "$status" V3.3 "Purity/import tests and semgrep-test" "$(log_detail "$TMP/gate.log")"
  local secrets=PASS
  secret_scan > "$TMP/secrets.log" 2>&1 || secrets=FAIL
  [ "$status" = PASS ] && [ "$secrets" = PASS ] || status=FAIL
  record "$status" V15.4 "Whole-tree secrets, SAST, audit and licences" "$(log_detail "$TMP/secrets.log")"
}

api() { gh api "repos/$REPO$1" "${@:2}"; }
main_ci() {
  local sha run
  sha=$(api /commits/main --jq .sha) || return 1
  run=$(gh run list -R "$REPO" --workflow ci.yml --branch main --event push --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId') || return 1
  [ -n "$run" ] || fail "no CI run for main HEAD"
  gh run view -R "$REPO" "$run" --json conclusion,jobs --jq \
    '.conclusion == "success" and ([.jobs[] | select(.name == "pyodide" or .name == "docs") | .conclusion] | length == 2 and all(. == "success"))' \
    | grep -qx true
}
rtd() {
  local sha
  sha=$(api /commits/main --jq .sha) || return 1
  "$PY" - "$sha" << 'PY'
import json
import sys
import urllib.request

base = "https://app.readthedocs.org/api/v3/projects/pyeconomics/"
def fetch(path):
    request = urllib.request.Request(base + path, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)
project = fetch("")
main = fetch("versions/main/")
latest = fetch("versions/latest/")
stable = fetch("versions/stable/")
builds = fetch("versions/main/builds/?limit=1")["results"]
assert project["default_version"] == "stable" and project["default_branch"] == "legacy/0.2.x"
assert main["active"] and main["built"] and not main["hidden"]
assert builds and builds[0]["success"] and builds[0]["commit"] == sys.argv[1]
assert latest["identifier"] == "legacy/0.2.x" and latest["active"] and latest["built"]
assert stable["active"] and stable["built"]
for version, marker in (("stable", "0.2.6 documentation"), ("latest", "0.2.6 documentation"), ("main", "1.0 preview")):
    request = urllib.request.Request(f"https://pyeconomics.readthedocs.io/en/{version}/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        assert marker in response.read().decode()
PY
}
attested() {
  "$PY" - "$1" "$2" << 'PY'
import json
import sys
import urllib.parse
import urllib.request

host, version = sys.argv[1:]
def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)
data = fetch(f"https://{host}.org/pypi/pyeconomics/{version}/json")
assert len(data["urls"]) == 2
assert {u["packagetype"] for u in data["urls"]} == {"bdist_wheel", "sdist"}
for item in data["urls"]:
    name = urllib.parse.quote(item["filename"], safe="")
    provenance = fetch(f"https://{host}.org/integrity/pyeconomics/{version}/{name}/provenance")
    assert provenance["attestation_bundles"]
PY
}
rehearsal() {
  local tag version
  tag=$(git tag --merged origin/main --list 'v1.0.0a1.dev*' --sort=-version:refname | head -n 1 | tr -d '\r')
  version=${tag#v}
  [ -n "$version" ] || fail "no merged rehearsal tag"
  attested test.pypi "$version"
}
production() {
  attested pypi 1.0.0a1 || return 1
  gh release view v1.0.0a1 -R "$REPO" --json isDraft,isPrerelease,tagName \
    --jq '.isDraft == false and .isPrerelease == true and .tagName == "v1.0.0a1"' | grep -qx true
}
required_checks() {
  api /branches/main/protection/required_status_checks --jq \
    '.strict == true and (.contexts | index("phase-verify-fast (02)") != null and index("phase-verify-security (02)") != null)' | grep -qx true
}
floor() { uv run --locked python scripts/checks/python_floor.py; }
run_live() {
  CURRENT_MODE=live
  section "--live"
  vcheck V1.3 "Main HEAD CI, Pyodide and docs green" main_ci
  vcheck V7.3 "RTD main HEAD preview and unchanged stable/latest" rtd
  vcheck V13.2 "Merged TestPyPI rehearsal wheel/sdist provenance" rehearsal
  vcheck V13.3 "Live NumPy/SciPy Python floor" floor
  vcheck V14.2 "PyPI alpha provenance and GitHub pre-release" production
  vcheck V15.7 "Both phase 02 checks required, strict" required_checks
}

published_install() {
  local py
  uv venv --no-config --seed --python 3.12 "$TMP/published" || return 1
  py=$(venv_python "$TMP/published")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --pre --index-url https://pypi.org/simple/ pyeconomics==1.0.0a1 || return 1
  mkdir -p "$TMP/published-smoke" || return 1
  # The release's own smoke script, as release-smoke.yml checks out its tag's
  # scripts: the working tree's copy tests what main builds, not 1.0.0a1
  # (Phase 3 Step 2's addendum in docs/roadmap/phase02-roadmap.md).
  MSYS_NO_PATHCONV=1 git show v1.0.0a1:scripts/smoke.py > "$TMP/published-smoke/smoke.py" || return 1
  (cd "$TMP/published-smoke" && "$py" -c 'import pyeconomics; assert pyeconomics.__version__ == "1.0.0a1"' \
    && "$py" smoke.py --all --min-domains 11) || return 1
  "$py" -m pip --isolated install --timeout 30 --retries 2 --pre --index-url https://pypi.org/simple/ 'pyeconomics[econometrics,plot]==1.0.0a1' || return 1
  (cd "$TMP/published-smoke" && "$py" smoke.py --all --extras --min-domains 11 && "$py" -m pip check) || return 1
  uv venv --no-config --seed --python 3.12 "$TMP/stable" || return 1
  py=$(venv_python "$TMP/stable")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --index-url https://pypi.org/simple/ pyeconomics || return 1
  (cd "$TMP" && "$py" -c 'from importlib.metadata import version; assert version("pyeconomics") == "0.2.6"' && "$py" -m pip check)
}
alarm() {
  local id
  id=$(sed -nE 's#^Synthetic alarm run: https://github.com/[^/]+/[^/]+/actions/runs/([0-9]+).*#\1#p' "$QA" | head -n 1)
  [ -n "$id" ] || fail "no recorded alarm run"
  grep -qE '^Notification received: confirmed by the maintainer ' "$QA" || fail "maintainer confirmation missing"
  gh run view -R "$REPO" "$id" --json workflowName,conclusion,event --jq \
    '.workflowName == "release-smoke" and .conclusion == "failure" and .event == "workflow_dispatch"' | grep -qx true
}
phase01() { bash scripts/verify-phase01.sh --post; }
pr_checks() {
  local branch
  gh auth status > /dev/null 2>&1 || return 0
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [ "$branch" != main ] && gh pr view "$branch" -R "$REPO" > /dev/null 2>&1; then
    gh pr checks "$branch" -R "$REPO"
    return $?
  fi
  return 0
}
run_post() {
  CURRENT_MODE=post
  section "--post"
  vcheck V14.3 "Fresh PyPI alpha core/extras and ordinary stable pip installs" published_install
  vcheck V15.5 "Failed synthetic alarm and maintainer notification confirmation" alarm
  vcheck V15.6 "Phase 1 --post remains green" phase01
  vcheck PR "Current branch pull request checks when authenticated" pr_checks
}

START=$SECONDS
run_static
case "$MODE" in
  --python) run_python ;;
  --security) run_security ;;
  --live) run_live ;;
  --all) run_python; run_security ;;
  --post) run_python; run_security; run_live; run_post ;;
esac
section "Summary ($MODE, $((SECONDS - START))s)"
printf '%-10s %6s %6s\n' mode passed failed
for m in fast python security live post; do
  if [ -n "${MODE_PASS[$m]:-}${MODE_FAIL[$m]:-}" ]; then
    printf '%-10s %6s %6s\n' "$m" "${MODE_PASS[$m]:-0}" "${MODE_FAIL[$m]:-0}"
  fi
done
if [ "$FAILED" = 0 ]; then echo "RESULT: PASS"; exit 0; fi
echo "RESULT: FAIL"
exit 1
