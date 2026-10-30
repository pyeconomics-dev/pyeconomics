#!/usr/bin/env bash
# scripts/verify-phase03.sh
#
# Phase 3 verification: 78 independent static checks and the V1-V20 matrix.
# --fast (default): static checks; --python: tests, docs, artifacts and smoke;
# --security: whole-tree gate; --live: authenticated/public service reads;
# --all: fast + python + security; --post: all + live + published installs,
# alarm evidence, Phases 1 and 2 post verification and current PR checks.
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
ROADMAP=docs/roadmap/phase03-roadmap.md
QA=docs/phase03-qa-findings.md
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
  echo "verify-phase03.sh: needs python3 (3.11 or later) on PATH" >&2
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
import hashlib
import io
import json
import re
import subprocess
import sys
import tomllib
import tokenize
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

def dependency(items, name):
    return any(isinstance(x, str) and re.match(re.escape(name) + r"(?:[>=<;\[]|$)", x, re.I) for x in items)

project = tomllib.loads(text("pyproject.toml"))
deps = project["project"]["dependencies"]
extras = project["project"]["optional-dependencies"]
entry = project["project"]["entry-points"]["pyeconomics.models"]
providers = project["project"]["entry-points"]["pyeconomics.providers"]
core = "src/pyeconomics/core/"
data = "src/pyeconomics/data/"
roadmap = text("docs/roadmap/phase03-roadmap.md")

def section(body, heading):
    return body.split(heading, 1)[1].split("\n## ", 1)[0]

def source_plan():
    table = roadmap.split("**The source plan.**", 1)[1].split("\n\n", 1)[1].split("\n\n", 1)[0]
    rows = re.findall(r"^\| `([a-z_]+)`\s*\|", table, re.M)
    assert len(rows) == 31 and len(set(rows)) == 31, "source plan must name all 31 released sources"
    return set(rows)

def released(name):
    tree = ast.parse(text(data + "_released.py"))
    node = next(x.value for x in tree.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) and x.target.id == name)
    return {ast.literal_eval(k) for k in node.args[0].keys}

def provider_group(names):
    for name in names.split():
        assert providers.get(name) == "pyeconomics.data.providers." + name, name
        files(data + "providers/" + name + ".py")

catalog = {
    "macro": "policy_rule neutral_rate output_gap okun_law phillips_curve solow_growth recession_probability debt_dynamics",
    "fixed_income": "curve_fitting interest_rate_tree",
    "equity": "implied_risk_premium cape",
    "asset_pricing": "factor_regression factor_model_tests",
    "portfolio": "black_litterman risk_based_allocation",
    "econometrics": "garch time_series",
}

def models(*domains):
    for domain in domains:
        for name in catalog[domain].split():
            contains(f"src/pyeconomics/models/{domain}/{name}.py", f'id="{domain}.{name}"')

def goldens(*domains):
    for domain in domains:
        files(*(f"tests/golden/{domain}/{name}.toml" for name in catalog[domain].split()))

def workflow(name):
    return text(".github/workflows/" + name + ".yml")

if n == 1:
    assert git("ls-files", "--", "docs/roadmap/phase03-roadmap.md")
    assert git("ls-files", "--", "planning/")
elif n == 2:
    files("tests/unit/core/test_unit_coercion.py", "tests/unit/core/test_cashflows.py", "tests/registry/test_validate_rules.py")
    contains("tests/unit/core/test_cashflows.py", "endpoint")
elif n == 3: contains("docs/errata.md", "IRR", "1.0.0a2")
elif n == 4:
    adr = text("docs/adr/0011-data-platform.md")
    assert "Status: Accepted" in adr
    assert set(range(1, 19)) <= {int(x) for x in re.findall(r"^### (\d+)\.", adr, re.M)}
elif n == 5:
    files(core + "provenance.py", *(data + x + ".py" for x in "types terms vintage errors".split()))
elif n == 6:
    tree = ast.parse(text("scripts/checks/coverage_floors.py"))
    node = next(x.value for x in tree.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) and x.target.id == "FLOORS")
    floors = {name: bound for name, _, bound in ast.literal_eval(node)}
    assert floors["data"] >= 95
    contains(".github/workflows/ci.yml", "scripts/checks/coverage_floors.py")
elif n == 7: contains("scripts/smoke.py", "pyeconomics.data", "Series")
elif n == 8:
    contains("docs/roadmap/ROADMAP.md", "3.3", "3.4", "3.7", "3.8", "never")
    contains("docs/roadmap/phase02-roadmap.md", "Phase 3", "addendum")
elif n == 9:
    files(*(data + x for x in ("credentials/__init__.py", "credentials/chain.py", "credentials/secret.py", "config.py", "redaction.py")))
elif n == 10: files(".semgrep/rules/secret-reveal.yaml", ".semgrep/tests/secret-reveal.py")
elif n == 11: assert dependency(extras["keyring"], "keyring") and dependency(extras["all"], "keyring")
elif n == 12: assert dependency(deps, "platformdirs")
elif n == 13: contains("docs/data/keys.md", "keyring", "FRED")
elif n == 14:
    files("tests/config_isolation.py", "tests/data/leakcheck.py", "tests/data/credentials/test_canary_sinks.py")
    contains("tests/data/leakcheck.py", "LeakCheck", "canary")
elif n == 15: files(*(data + x for x in ("providers/base.py", "registry.py", "transport/base.py", "transport/http.py", "modes.py")))
elif n == 16: assert providers
elif n == 17:
    options = project["tool"]["pytest"]["ini_options"]
    assert "--disable-socket" in options["addopts"]
    # The -m expression deselects live tests (Phase 4 Step 7 adds "and not fuzz").
    selection = options["addopts"][options["addopts"].index("-m") + 1]
    assert re.fullmatch(r"not live( and not \w+)*", selection)
    assert any(m.startswith("live:") for m in options["markers"])
elif n == 18: files("scripts/record_cassettes.py", "tests/providers/provider_contract.py", "tests/providers/test_provider_contract.py")
elif n == 19:
    files("tests/providers/test_bloomberg_spike.py")
    for p in Path("src").rglob("*.py"):
        # Tokenization handles Python 3.12 generics on the system's 3.11,
        # comma-separated imports and continuations, without reading strings.
        importing = False
        for token in tokenize.generate_tokens(io.StringIO(text(p)).readline):
            if token.type == tokenize.NAME and token.string in {"import", "from"}:
                importing = True
            if importing and token.type == tokenize.NAME:
                assert token.string != "blpapi", str(p)
            if token.type == tokenize.NEWLINE or token.string == ";":
                importing = False
elif n == 20: files("docs/data/writing-a-provider.md", "docs/data/index.md", "docs/_ext/provider_pages.py")
elif n == 21: files("tests/providers/test_notices.py")
elif n == 22: files(*(data + "cache/" + x for x in ("__init__.py", "policy.py", "store.py")))
elif n == 23: contains("tests/data/cache/test_cache_policy.py", "FORBIDDEN", "fred")
elif n == 24: provider_group("fred bls bea census")
elif n == 25:
    paths = list(Path("tests/providers/cassettes/fred").glob("*.json"))
    assert paths
    assert all(json.loads(text(p))["synthetic"] is True for p in paths)
elif n in (26, 27):
    body = workflow("providers-live" if n == 26 else "providers-heartbeat")
    triggers = body.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert set(re.findall(r"^  ([a-z_]+):", triggers, re.M)) == {"schedule", "workflow_dispatch"}
elif n == 28:
    for name, allowed in (("providers-live", "report"), ("providers-heartbeat", "heartbeat")):
        body = workflow(name)
        assert re.search(r"^permissions: \{\}\s*$", body, re.M)
        jobs = body.split("\njobs:\n", 1)[1]
        for job in re.split(r"(?=^  [a-z_]+:\s*$)", jobs, flags=re.M):
            if "issues: write" in job: assert re.match(r"  " + allowed + r":", job)
elif n == 29:
    paths = [Path("tests/providers/test_provider_fred.py")]
    assert paths
    assert any("BEA" in text(p) and "2023-10-26" in text(p) and "2024-09-26" in text(p) for p in paths)
elif n == 30:
    provider_group("treasury fed_board nyfed openfigi sec_edgar")
    assert source_plan() == set(providers) == released("PROVIDERS"), "source-plan/entry-point/released-id mismatch"
    readiness = section(text("docs/releases/1.0.0a2-readiness.md"), "## 2.")
    recorded = set(re.findall(r"^\| `([a-z_]+)`\s*\|", readiness, re.M))
    assert recorded == source_plan(), "readiness/source-plan mismatch"
    files("tests/providers/cassettes/sec_edgar/facts.json")
elif n == 31:
    assert "Build Your Package" not in "\n".join(text(p) for p in Path("src/pyeconomics/data").rglob("*.py"))
elif n == 32: assert dependency(deps, "openpyxl") and dependency(deps, "defusedxml")
elif n == 33: assert dependency(extras["sdmx"], "sdmx1") and dependency(extras["all"], "sdmx1")
elif n == 34: provider_group("ecb bis imf oecd eurostat world_bank dbnomics")
elif n == 35: contains("scripts/checks/licence_exceptions.toml", 'package = "certifi"', "MPL-2.0")
elif n == 36: provider_group("philadelphia_fed atlanta_fed cleveland_fed cbo penn_world_table")
elif n == 37:
    table = roadmap.split("**The source plan.**", 1)[1].split("\n\n", 1)[1].split("\n\n", 1)[0]
    assert not re.search(r"\bTBD\b", table)
elif n == 38: contains("docs/roadmap/ROADMAP.md", "Penn World Table", "library-only")
elif n == 39: provider_group("ken_french shiller aqr hou_xue_zhang jkp open_source_asset_pricing cboe coin_metrics damodaran yfinance")
elif n == 40: assert dependency(extras["yfinance"], "yfinance") and dependency(extras["all"], "yfinance")
elif n == 41:
    contains(data + "config.py", "enable_yfinance")
    contains(data + "providers/yfinance.py", "require_enabled", "excluded from automated live runs")
elif n == 42:
    body = workflow("providers-live").split("allowed-endpoints:", 1)[1].split("\n      - name:", 1)[0]
    assert "yahoo" not in body.lower()
elif n == 43: assert dependency(deps, "xlrd")
elif n == 44: files(data + "catalog/definitions.py", data + "catalog/transforms.py", data + "resolver.py")
elif n == 45: definitions(data + "api.py", "get search describe vintages sources".split())
elif n == 46: files("docs/data/index.md", "docs/_ext/concept_pages.py")
elif n == 47:
    files(core + "transforms.py")
    assert released("CONCEPTS")
elif n == 48: files(core + "binding.py", data + "bindings.py")
elif n == 49: contains(core + "model.py", "bindings:")
elif n == 50:
    tree = ast.parse(text(core + "manifest.py"))
    node = next(x.value for x in tree.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) and x.target.id == "MANIFEST_SCHEMA_VERSION")
    assert ast.literal_eval(node) >= 2
elif n == 51: contains(core + "describe.py", '"bindings"')
elif n == 52: contains("scripts/new_model.py", "--bound")
elif n == 53:
    assert "macro" in entry
    files("src/pyeconomics/models/macro/policy_rule.py", "src/pyeconomics/models/macro/neutral_rate.py")
elif n == 54: files("tests/golden/macro/policy_rule.toml", "tests/golden/macro/neutral_rate.toml")
elif n == 55: contains("tests/models/macro/test_legacy_parity.py", "fixtures", "legacy")
elif n == 56:
    root = Path("tests/fixtures/legacy")
    for name, digest in json.loads(text(root / "manifest.json"))["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
elif n == 57: models("macro")
elif n == 58: goldens("macro")
elif n == 59: assert re.search(r"^def least_squares\(", text(core + "regression.py"), re.M)
elif n == 60: models("fixed_income", "equity")
elif n == 61: goldens("fixed_income", "equity")
elif n == 62: assert "asset_pricing" in entry
elif n == 63: models("asset_pricing", "portfolio")
elif n == 64: goldens("asset_pricing", "portfolio")
elif n == 65:
    models("econometrics")
    goldens("econometrics")
elif n == 66: assert dependency(extras["econometrics"], "arch") and dependency(extras["all"], "arch")
elif n == 67:
    body = text("docs/releases/1.0.0a2-readiness.md")
    assert set(range(1, 15)) <= {int(x) for x in re.findall(r"^## (\d+)\.", body, re.M)}
    assert re.search(r"^Decision: GO", body, re.M)
    assert not re.search(r"\|\s*FAIL\s*\||^FAIL\b", body, re.M)
elif n == 68: assert git("tag", "--merged", "origin/main", "--list", "v1.0.0a2.dev*")
elif n == 69: subprocess.check_call(["git", "merge-base", "--is-ancestor", "v1.0.0a2", "origin/main"])
elif n == 70: assert re.search(r"^## \[1\.0\.0a2\] - \d{4}-\d{2}-\d{2}", text("CHANGELOG.md"), re.M)
elif n == 71:
    ledger = text(core + "_released.py")
    for domain, names in catalog.items():
        assert all('"' + domain + "." + name + '"' in ledger for name in names.split())
elif n == 72: assert released("PROVIDERS") == source_plan()
elif n == 73: contains("docs/releases/1.0.0a2.md", "sec_edgar", "31", "https://pyeconomics.readthedocs.io/en/main/")
elif n == 74:
    files("scripts/verify-phase03.sh")
    assert git("ls-files", "--stage", "--", "scripts/verify-phase03.sh").startswith("100755 ")
elif n == 75: files("docs/phase03-qa-findings.md")
elif n == 76: files("docs/roadmap/phase03-roadmap.md")
elif n == 77:
    matrices = re.findall(r"^\s+phase:\s*\[([^]]+)\]\s*$", workflow("phase-verify"), re.M)
    assert len(matrices) >= 2 and all('"03"' in m for m in matrices)
else: raise ValueError(n)

PY
}

c78() {
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
  "$PY" - << 'PY'
import re
from pathlib import Path
staging_secrets = {"GITHUB_TOKEN", "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET"}
# Phase 5 Step 4: deploy-staging.yml's site job deploys with the staging
# environment's Cloudflare API token, which no other workflow may read.
staging_sets = {
    "deploy-staging.yml": staging_secrets | {"CLOUDFLARE_API_TOKEN"},
    "staging-health.yml": staging_secrets,
}
for path in Path(".github/workflows").glob("*.yml"):
    if path.name == "providers-live.yml":
        continue
    # github.token and secrets.GITHUB_TOKEN are ephemeral built-in tokens.
    body = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"\bsecrets\s*\[|toJSON\(secrets\)", body), path.name
    names = re.findall(r"\bsecrets\.([A-Za-z_][A-Za-z_0-9]*)", body)
    if path.name in staging_sets:
        assert set(names) <= staging_sets[path.name], path.name
        assert re.search(r"^\s+environment:\s*(?:staging\s*$|\n\s+name:\s*staging\s*$)", body, re.M), path.name
    else:
        assert set(names) <= {"GITHUB_TOKEN"}, path.name
PY
}
run_static() {
  CURRENT_MODE=fast
  section "Static checks 1-78"
  check 1 "Phase 3 roadmap and planning kit tracked" static_check 1
  check 2 "Core coercion, literal-unit and IRR regressions" static_check 2
  check 3 "IRR public erratum" static_check 3
  check 4 "ADR-0011 accepted with eighteen decisions" static_check 4
  check 5 "Core provenance and data value modules" static_check 5
  check 6 "Data coverage floor required in CI" static_check 6
  check 7 "Smoke imports data and constructs a Series" static_check 7
  check 8 "Parent amendments and Phase 2 addendum" static_check 8
  check 9 "Credential, configuration and redaction modules" static_check 9
  check 10 "Secret-reveal rule and fixtures" static_check 10
  check 11 "Keyring extra included in all" static_check 11
  check 12 "Platformdirs dependency" static_check 12
  check 13 "Credential setup guide" static_check 13
  check 14 "Isolation and leak canary harness" static_check 14
  check 15 "Provider SDK, registry, transport and modes" static_check 15
  check 16 "Provider entry-point group" static_check 16
  check 17 "Live deselected; sockets disabled by default" static_check 17
  check 18 "Recorder and provider contract suite" static_check 18
  check 19 "Bloomberg spike; no runtime blpapi import" static_check 19
  check 20 "Provider pages and author guide" static_check 20
  check 21 "Provider notice tests" static_check 21
  check 22 "Cache implementation" static_check 22
  check 23 "Forbidden-storage policy regression" static_check 23
  check 24 "Four keyed providers and entry points" static_check 24
  check 25 "FRED recordings exclusively synthetic" static_check 25
  check 26 "Live workflow schedule/dispatch only" static_check 26
  check 27 "Heartbeat workflow schedule/dispatch only" static_check 27
  check 28 "Workflow permissions limited to report jobs" static_check 28
  check 29 "ALFRED vintage test with source citations" static_check 29
  check 30 "Exact 31-id source/readiness/entry/ledger set including SEC" static_check 30
  check 31 "No retired Build Your Package endpoint" static_check 31
  check 32 "Bounded XML and spreadsheet dependencies" static_check 32
  check 33 "SDMX extra included in all" static_check 33
  check 34 "Seven international providers" static_check 34
  check 35 "Reviewed certifi licence exception" static_check 35
  check 36 "Five research providers" static_check 36
  check 37 "Source plan has no TBD classifications" static_check 37
  check 38 "Parent classification note" static_check 38
  check 39 "Ten research-finance providers" static_check 39
  check 40 "Yfinance extra included in all" static_check 40
  check 41 "Yahoo explicit opt-in and automation exclusion" static_check 41
  check 42 "Yahoo absent from automated egress" static_check 42
  check 43 "Xlrd dependency" static_check 43
  check 44 "Catalog and resolver" static_check 44
  check 45 "Public data facade" static_check 45
  check 46 "Data guide and generated concept pages" static_check 46
  check 47 "Transform vocabulary and concept ledger" static_check 47
  check 48 "Binding vocabulary and resolution" static_check 48
  check 49 "Model bindings declaration" static_check 49
  check 50 "Manifest schema at least 2" static_check 50
  check 51 "Describe bindings metadata" static_check 51
  check 52 "Bound model scaffold" static_check 52
  check 53 "Macro domain and policy model modules" static_check 53
  check 54 "Policy and neutral-rate goldens" static_check 54
  check 55 "Legacy fixture parity suite" static_check 55
  check 56 "Legacy fixture hashes unchanged" static_check 56
  check 57 "Eight macro modules including six launch families" static_check 57
  check 58 "Macro golden files" static_check 58
  check 59 "Shared least squares" static_check 59
  check 60 "Four fixed-income/equity launch models" static_check 60
  check 61 "Their golden cases" static_check 61
  check 62 "Asset-pricing domain entry point" static_check 62
  check 63 "Four asset-pricing/portfolio launch models" static_check 63
  check 64 "Their golden cases" static_check 64
  check 65 "GARCH/time-series modules and goldens" static_check 65
  check 66 "Arch extra with reviewed Wheel-rule marker" static_check 66
  check 67 "Fourteen-section readiness GO; no unresolved FAIL" static_check 67
  check 68 "Merged alpha rehearsal tag" static_check 68
  check 69 "Production alpha tag merged into main" static_check 69
  check 70 "Dated 1.0.0a2 changelog" static_check 70
  check 71 "All eighteen new ids in model ledger" static_check 71
  check 72 "Exact released provider set" static_check 72
  check 73 "Release notes include SEC and preview guide" static_check 73
  check 74 "Executable Phase 3 verifier in index" static_check 74
  check 75 "QA findings document" static_check 75
  check 76 "Phase roadmap exists" static_check 76
  check 77 "Both CI matrices include 03" static_check 77
  check 78 "Credential backstop, hooks and workflow secret boundary" c78
  vstatic V1.1 "Step 1 deliverables" 1 3
  vstatic V2.1 "Step 2 deliverables" 4 8
  vstatic V3.1 "Step 3 deliverables" 9 14
  vstatic V4.1 "Step 4 deliverables" 15 21
  vstatic V5.1 "Step 5 deliverables" 22 23
  vstatic V6.1 "Step 6 deliverables" 24 29
  vstatic V7.1 "Step 7 deliverables" 30 32
  vstatic V8.1 "Step 8 deliverables" 33 35
  vstatic V9.1 "Step 9 deliverables" 36 38
  vstatic V10.1 "Step 10 deliverables" 39 43
  vstatic V11.1 "Step 11 deliverables" 44 47
  vstatic V12.1 "Step 12 deliverables" 48 52
  vstatic V13.1 "Step 13 deliverables" 53 56
  vstatic V14.1 "Step 14 deliverables" 57 59
  vstatic V15.1 "Step 15 deliverables" 60 61
  vstatic V16.1 "Step 16 deliverables" 62 64
  vstatic V17.1 "Step 17 deliverables" 65 66
  vstatic V18.1 "Step 18 deliverables" 67 68
  vstatic V19.1 "Step 19 deliverables" 69 73
  vstatic V20.1 "Fast verifier succeeds" 1 78
  vstatic V20.2 "Both phase matrices include 03" 77 77
  vstatic V20.3 "Every static check passes" 1 78
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
    && (cd "$TMP" && uv run --project "$ROOT" --locked python -c 'from pyeconomics import registry; registry.validate(); from pyeconomics import data; data.registry.validate(); data.validate_bindings()')
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
from pyeconomics import data
for provider_id in data.registry.ids():
    assert (Path(sys.argv[1]) / "reference/providers" / (provider_id + ".html")).is_file(), provider_id
for concept_id in data.catalog.ids():
    assert (Path(sys.argv[1]) / "reference/concepts" / (concept_id + ".html")).is_file(), concept_id
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
  (cd "$TMP/smoke" && "$py" smoke.py --all --min-domains 13) || return 1
  uv venv --no-config --python "$interpreter" -q "$TMP/extras" || return 1
  py=$(venv_python "$TMP/extras")
  uv pip install --no-config --python "$py" "${wheel}[econometrics,plot]" || return 1
  (cd "$TMP/smoke" && "$py" smoke.py --all --extras --min-domains 13)
}
run_python() {
  CURRENT_MODE=python
  section "--python"
  vcheck TYPES "Locked extras/docs; format, lint and strict types" lint_types
  local suite_status=PASS id
  suite > "$TMP/suite.log" 2>&1 || suite_status=FAIL
  for id in V1.2 V2.2 V3.2 V4.2 V5.2 V6.2 V7.2 V9.2 V10.2 V11.2 V12.2 V13.2 V14.2 V15.2 V17.2; do
    record "$suite_status" "$id" "Full socket-isolated suite, registries, bindings and three coverage floors" "$(log_detail "$TMP/suite.log")"
  done
  local licence_status=PASS combined=PASS
  uv run --locked prek run licences --all-files > "$TMP/licences.log" 2>&1 || licence_status=FAIL
  [ "$suite_status" = PASS ] && [ "$licence_status" = PASS ] || combined=FAIL
  record "$combined" V8.2 "International provider contracts and all-extras licence closure" "$(log_detail "$TMP/licences.log")"
  vcheck DOCS "Sphinx -W; executed tutorial and every model/provider/concept page" docs_build
  vcheck BUILD "Wheel/sdist, strict Twine and artifact allowlist" artifact_build
  local smoke_status=PASS
  wheel_smoke > "$TMP/smoke.log" 2>&1 || smoke_status=FAIL
  record "$smoke_status" V17.3 "Separate core/extras wheel smokes across thirteen domains" "$(log_detail "$TMP/smoke.log")"
  combined=PASS
  [ "$suite_status" = PASS ] && [ "$smoke_status" = PASS ] || combined=FAIL
  record "$combined" V16.2 "Asset-pricing/portfolio contracts and thirteen-domain installed smoke" "$(log_detail "$TMP/smoke.log")"
}
log_detail() { tail -n 4 "$1" | tr '\n' ' ' | cut -c1-400; }

security_gate() {
  uv run --locked prek run semgrep-test --all-files || return 1
  uv run --locked pytest tests/registry/test_model_imports.py tests/data/test_layering.py -q || return 1
  local skip=""
  [ "$(git rev-parse --abbrev-ref HEAD)" != main ] || skip=no-commit-to-branch
  # The sole authorized skip is the branch-name guard when verifying main.
  SKIP="$skip" uv run --locked prek run --all-files
}
secret_scan() {
  git clone -q --no-hardlinks "$ROOT" "$TMP/scan" || return 1
  (cd "$TMP/scan" && git checkout -q --orphan gate-secrets-scan \
    && uv run --project "$ROOT" --locked prek run gitleaks --all-files)
}
cassette_scan() { uv run --locked pytest tests/providers/test_cassette_files.py -q; }
run_security() {
  CURRENT_MODE=security
  section "--security"
  local gate=PASS secrets=PASS cassettes=PASS status=PASS
  security_gate > "$TMP/gate.log" 2>&1 || gate=FAIL
  record "$gate" V3.3 "Purity, layering and semgrep rules; whole-tree gate" "$(log_detail "$TMP/gate.log")"
  cassette_scan > "$TMP/cassettes.log" 2>&1 || cassettes=FAIL
  record "$cassettes" V4.3 "Every cassette scanned for secrets, terms and size caps" "$(log_detail "$TMP/cassettes.log")"
  secret_scan > "$TMP/secrets.log" 2>&1 || secrets=FAIL
  [ "$gate" = PASS ] && [ "$secrets" = PASS ] && [ "$cassettes" = PASS ] || status=FAIL
  record "$status" V20.4 "Whole-tree secrets, SAST, audit, licences and cassette scan" "$(log_detail "$TMP/secrets.log")"
}

api() { gh api "repos/$REPO$1" "${@:2}"; }
closed_core_issues() {
  local n
  for n in 75 81 85; do
    gh issue view "$n" -R "$REPO" --json state --jq .state | grep -qx CLOSED || return 1
  done
}
main_ci() {
  local sha run
  sha=$(api /commits/main --jq .sha) || return 1
  run=$(gh run list -R "$REPO" --workflow ci.yml --branch main --event push --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId') || return 1
  [ -n "$run" ] || fail "no CI run for main HEAD"
  gh run view -R "$REPO" "$run" --json conclusion,jobs --jq \
    '.conclusion == "success" and ([.jobs[] | select(.name == "pyodide") | .conclusion] | length == 1 and all(. == "success"))' | grep -qx true
}
providers_live() {
  api '/actions/workflows/providers-live.yml/runs?branch=main&status=success&per_page=1' > "$TMP/live-runs.json" || return 1
  api '/actions/workflows/providers-heartbeat.yml/runs?branch=main&per_page=1' > "$TMP/heartbeat-runs.json" || return 1
  "$PY" - "$TMP" << 'PY'
import datetime as dt
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
live = json.loads((root / "live-runs.json").read_text())["workflow_runs"]
heartbeat = json.loads((root / "heartbeat-runs.json").read_text())["workflow_runs"]
assert live and live[0]["conclusion"] == "success"
finished = dt.datetime.fromisoformat(live[0]["updated_at"].replace("Z", "+00:00"))
assert dt.timedelta(0) <= dt.datetime.now(dt.UTC) - finished < dt.timedelta(days=8)
assert heartbeat and heartbeat[0]["conclusion"] == "success"
PY
}
# Verify the individual live test in the successful run, rather than treating
# a successful empty suite or a skip as proof of a financial calculation.
live_case() {
  local pattern=$1 run archive
  run=$(api '/actions/workflows/providers-live.yml/runs?branch=main&status=success&per_page=1' --jq '.workflow_runs[0].id') || return 1
  mkdir -p "$TMP/live-junit" || return 1
  if [ ! -f "$TMP/live-junit/live-junit.xml" ]; then
    gh run download "$run" -R "$REPO" -n live-junit -D "$TMP/live-junit" || return 1
  fi
  "$PY" - "$TMP/live-junit/live-junit.xml" "$pattern" << 'PY'
import sys
import xml.etree.ElementTree as ET
cases = [c for c in ET.parse(sys.argv[1]).iter("testcase") if sys.argv[2] in c.get("classname", "") + "::" + c.get("name", "")]
assert cases and all(not any(c.find(tag) is not None for tag in ("failure", "error", "skipped")) for c in cases), sys.argv[2]
PY
}
live_taylor() { live_case test_live_policy_rule; }
live_cape() { live_case test_live_cape; }
rtd() {
  local sha
  sha=$(api /commits/main --jq .sha) || return 1
  "$PY" - "$sha" << 'PY'
import json
import sys
import urllib.request
base = "https://app.readthedocs.org/api/v3/projects/pyeconomics/"
def fetch(url, decode=True):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response) if decode else response.read().decode()
project = fetch(base)
main = fetch(base + "versions/main/")
builds = fetch(base + "versions/main/builds/?limit=1")["results"]
assert project["default_version"] == "stable" and project["default_branch"] == "legacy/0.2.x"
assert main["active"] and main["built"] and not main["hidden"]
assert builds and builds[0]["success"] and builds[0]["commit"] == sys.argv[1]
assert "0.2.6 documentation" in fetch("https://pyeconomics.readthedocs.io/en/stable/", False)
for path in ("data/index.html", "reference/concepts/us.inflation.cpi.yoy.html"):
    assert "<html" in fetch("https://pyeconomics.readthedocs.io/en/main/" + path, False)
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
  tag=$(git tag --merged origin/main --list 'v1.0.0a2.dev*' --sort=-version:refname | head -n 1 | tr -d '\r')
  version=${tag#v}
  [ -n "$version" ] || fail "no merged rehearsal tag"
  attested test.pypi "$version"
}
production() {
  attested pypi 1.0.0a2 || return 1
  gh release view v1.0.0a2 -R "$REPO" --json isDraft,isPrerelease,tagName \
    --jq '.isDraft == false and .isPrerelease == true and .tagName == "v1.0.0a2"' | grep -qx true
}
required_checks() {
  api /branches/main/protection/required_status_checks --jq \
    '.strict == true and (.contexts | index("phase-verify-fast (03)") != null and index("phase-verify-security (03)") != null)' | grep -qx true
}
environment_policy() {
  api /environments/providers-live/deployment-branch-policies --jq \
    '[.branch_policies[] | "\(.type):\(.name)"] == ["branch:main"]' | grep -qx true || return 1
  gh secret list -R "$REPO" --env providers-live --json name > "$TMP/secret-names.json" || return 1
  "$PY" - "$TMP/secret-names.json" << 'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    names = {item["name"] for item in json.load(stream)}
assert {"FRED_API_KEY", "BLS_API_KEY", "BEA_API_KEY", "CENSUS_API_KEY", "SEC_CONTACT"} <= names
PY
  [ $? -eq 0 ] || return 1
  [ "$(gh secret list -R "$REPO" --json name --jq length)" = 0 ]
}
run_live() {
  CURRENT_MODE=live
  section "--live"
  vcheck V1.3 "Core hardening issues closed" closed_core_issues
  vcheck V2.3 "Main HEAD CI and Pyodide green" main_ci
  vcheck V6.3 "Successful live round-trip under eight days; newest heartbeat green" providers_live
  vcheck V11.3 "RTD exact main guide/concept pages and legacy stable" rtd
  vcheck V13.3 "Taylor ALFRED-vintage test passed in successful live run" live_taylor
  vcheck V15.3 "Shiller CAPE test passed in successful live run" live_cape
  vcheck V18.2 "TestPyPI rehearsal wheel/sdist provenances" rehearsal
  vcheck V19.2 "PyPI alpha provenances and GitHub pre-release" production
  vcheck V20.7 "Both phase 03 jobs required, strict" required_checks
  vcheck V20.8 "Live environment main-only; five named secrets; no repo secrets" environment_policy
}

published_install() {
  local py interpreter
  interpreter=$(uv python find --no-config) || return 1
  mkdir -p "$TMP/published-smoke" || return 1
  git show v1.0.0a2:scripts/smoke.py > "$TMP/published-smoke/smoke.py" || return 1
  uv venv --no-config --seed --python "$interpreter" "$TMP/published" || return 1
  py=$(venv_python "$TMP/published")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --pre --index-url https://pypi.org/simple/ pyeconomics==1.0.0a2 || return 1
  (cd "$TMP/published-smoke" && "$py" -c 'import pyeconomics; assert pyeconomics.__version__ == "1.0.0a2"' \
    && "$py" smoke.py --all --min-domains 13 && "$py" -m pip check) || return 1
  "$py" -m pip --isolated install --timeout 30 --retries 2 --pre --index-url https://pypi.org/simple/ 'pyeconomics[econometrics,plot,keyring]==1.0.0a2' || return 1
  (cd "$TMP/published-smoke" && "$py" smoke.py --all --extras --min-domains 13 && "$py" -m pip check) || return 1
  # Run in a subprocess with all ambient credentials removed; the tested
  # credential chain may read the maintainer's OS keyring. No value is logged.
  "$PY" - "$py" "$ROOT/scripts/verify_phase03_live.py" "$TMP" << 'PY'
import os
import subprocess
import sys
from pathlib import Path
py, script, temp = sys.argv[1:]
env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY") and not k.startswith("PYECONOMICS_")}
env.update(PYECONOMICS_CONFIG_DIR=str(Path(temp) / "recipe-config"), PYECONOMICS_CACHE_DIR=str(Path(temp) / "recipe-cache"))
subprocess.run([py, "-I", script], cwd=temp, env=env, check=True)
PY
  [ $? -eq 0 ] || return 1
  # 0.2.6 declares Python >=3.11,<3.13. Keep this historical check on
  # 3.12 even when the alpha's project interpreter is newer.
  uv venv --no-config --seed --python 3.12 "$TMP/stable" || return 1
  py=$(venv_python "$TMP/stable")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --index-url https://pypi.org/simple/ pyeconomics || return 1
  (cd "$TMP" && "$py" -c 'from importlib.metadata import version; assert version("pyeconomics") == "0.2.6"' && "$py" -m pip check)
}
alarms() {
  "$PY" - "$QA" "$REPO" "$TMP" << 'PY'
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
body = Path(sys.argv[1]).read_text(encoding="utf-8")
assert re.search(r"^Notification received: confirmed by the maintainer", body, re.M)
for name in ("providers-live", "providers-heartbeat"):
    match = re.search(r"^Synthetic " + name + r" alarm run: https://github.com/[^/]+/[^/]+/actions/runs/([0-9]+)", body, re.M)
    assert match, name
    run = json.loads(subprocess.check_output(["gh", "run", "view", match[1], "-R", sys.argv[2], "--json", "workflowName,conclusion,event,headBranch"]))
    assert run == {"workflowName": name, "conclusion": "failure", "event": "workflow_dispatch", "headBranch": "main"}, name
    issue = re.search(r"^Synthetic " + name + r" issue: https://github.com/[^/]+/[^/]+/issues/([0-9]+)", body, re.M)
    assert issue, name
    evidence = json.loads(subprocess.check_output(["gh", "issue", "view", issue[1], "-R", sys.argv[2], "--json", "body,state,comments,labels"]))
    assert evidence["state"] == "CLOSED" and match[1] in evidence["body"]
    assert any(label["name"] == "provider-live" for label in evidence["labels"])
    assert any("phase03-qa-findings.md" in comment["body"] for comment in evidence["comments"])
    if name == "providers-heartbeat":
        assert "the limit is 0" in evidence["body"]
    else:
        expected = "test_live_the_alarm_fails_only_when_a_failure_is_simulated"
        assert expected in evidence["body"]
        target = Path(sys.argv[3]) / "alarm-junit"
        subprocess.run(["gh", "run", "download", match[1], "-R", sys.argv[2], "-n", "live-junit", "-D", str(target)], check=True)
        failures = [c.get("name") for c in ET.parse(target / "live-junit.xml").iter("testcase") if c.find("failure") is not None or c.find("error") is not None]
        assert expected in failures, "the intended alarm test did not fail"
PY
}
earlier_phases() {
  # Phase 2 executes Phase 1 --post as V15.6. Require its fresh nested
  # verdict, so both commands run once rather than repeating Phase 1.
  HYPOTHESIS_PROFILE=ci bash scripts/verify-phase02.sh --post > "$TMP/phase02.log" 2>&1
  local second=$?
  log_detail "$TMP/phase02.log"
  [ "$second" -eq 0 ] && grep -qE '^PASS  V15\.6[[:space:]]' "$TMP/phase02.log"
}
pr_checks() {
  local branch
  gh auth status > /dev/null 2>&1 || return 1
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [ "$branch" != main ]; then
    gh pr checks "$branch" -R "$REPO"
  else
    main_ci
  fi
}
run_post() {
  CURRENT_MODE=post
  section "--post"
  vcheck V19.3 "Fresh PyPI core/extras, BLS and ALFRED live recipe, ordinary stable install" published_install
  vcheck V20.5 "Both synthetic alarm runs, issues and confirmed notification" alarms
  vcheck V20.6 "Phases 1 and 2 full --post remain green" earlier_phases
  vcheck PR "Current pull request checks or main HEAD CI" pr_checks
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
