#!/usr/bin/env bash
# scripts/verify-phase04.sh
#
# Phase 4 verification: 64 independent static checks and the V1-V16 matrix.
# --fast (default): static checks; --python: suite, parity, fuzz, docs, build;
# --node: TS client, edge Worker, Inspector, npm; --container: image build,
# scan and smoke; --security: whole-tree gate; --live: GitHub, staging and
# registries; --all: fast + python + node + container + security; --post: all
# + live + published installs, alarm evidence, Phase 3 --post and PR checks.
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
ROADMAP=docs/roadmap/phase04-roadmap.md
QA=docs/phase04-qa-findings.md
usage() {
  sed -n '4,10p' "$0" | sed 's/^# \{0,1\}//'
}

MODE="${1:---fast}"
case "$MODE" in
  --fast | --python | --node | --container | --security | --live | --all | --post) ;;
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
  echo "verify-phase04.sh: needs python3 (3.11 or later) on PATH" >&2
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

log_detail() { tail -n 4 "$1" | tr '\n' ' ' | cut -c1-400; }

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
    missing = [p for p in paths if not Path(p).is_file()]
    assert not missing, missing

def contains(path, *tokens):
    body = text(path)
    missing = [token for token in tokens if token not in body]
    assert not missing, (path, missing)

def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

def definitions(path, names, kind=ast.FunctionDef):
    nodes = ast.parse(text(path)).body
    assert set(names) <= {x.name for x in nodes if isinstance(x, kind)}, path

def dependency(items, name):
    return any(isinstance(x, str) and re.match(re.escape(name) + r"(?:[>=<;\[ ]|$)", x, re.I) for x in items)

def requirement(items, name):
    return next(x for x in items if re.match(re.escape(name) + r"(?:[>=<;\[ ]|$)", x, re.I))

project = tomllib.loads(text("pyproject.toml"))
deps = project["project"]["dependencies"]
extras = project["project"]["optional-dependencies"]
groups = project["dependency-groups"]
pkg = "src/pyeconomics/"

def workflow(name):
    # Comment lines may name a permission they explain; only YAML counts.
    lines = text(".github/workflows/" + name + ".yml").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#")) + "\n"

def triggers(body):
    block = body.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    return set(re.findall(r"^  ([a-z_]+):", block, re.M))

def jobs(body):
    block = body.split("\njobs:\n", 1)[1]
    parts = re.split(r"(?=^  [a-z][a-z0-9_-]*:\s*$)", block, flags=re.M)
    return {re.match(r"  ([a-z][a-z0-9_-]*):", p)[1]: p for p in parts if re.match(r"  [a-z]", p)}

def aggregate(*names):
    ci = jobs(workflow("ci"))
    for name in names:
        assert name in ci, name
    needs = re.search(r"needs:\s*\[([^]]+)\]", ci["test"])[1]
    assert set(names) <= {x.strip() for x in needs.split(",")}, needs

def toctree():
    body = text("docs/index.md")
    entries = set()
    for block in re.findall(r"```\{toctree\}\n(.*?)```", body, re.S):
        entries |= {line.strip() for line in block.splitlines() if line.strip() and not line.startswith(":")}
    return entries

def in_toctree(*pages):
    files(*(f"docs/{page}.md" for page in pages))
    assert set(pages) <= toctree(), pages

def ecosystems():
    return set(re.findall(r"package-ecosystem:\s*\"?([a-z_-]+)", text(".github/dependabot.yml")))

def hooks():
    return set(re.findall(r"^\s+- id:\s*(\S+)\s*$", text(".pre-commit-config.yaml"), re.M))

def ledger(source):
    tree = ast.parse(source)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "MappingProxyType" and node.args and isinstance(node.args[0], ast.Dict):
            target = found.setdefault(len(found), {})
            for key, value in zip(node.args[0].keys, node.args[0].values):
                target[ast.literal_eval(key)] = ast.dump(value)
    return found

if n == 1:
    assert git("ls-files", "--", "docs/roadmap/phase04-roadmap.md")
    assert git("ls-files", "--", "planning/")
elif n == 2:
    files("tests/unit/core/test_context_concurrency.py")
    contains(pkg + "core/context.py", "threading.RLock()", "showwarning")
elif n == 3: files("tests/unit/core/test_core_concurrency.py", "tests/data/test_data_concurrency.py")
elif n == 4:
    adr = text("docs/adr/0012-programmatic-surfaces.md")
    assert re.search(r"^- Status: Accepted\s*$", adr, re.M)
    assert set(range(1, 21)) <= {int(x) for x in re.findall(r"^### (\d+)\.", adr, re.M)}
    assert re.search(r"^\| \[0012\]\(0012-programmatic-surfaces\.md\) \|[^|]+\| Accepted \|", text("docs/adr/README.md"), re.M)
elif n == 5: files(*(pkg + "surfaces/" + x + ".py" for x in "invoke problems codec envelope budgets".split()))
elif n == 6:
    tree = ast.parse(text("scripts/checks/coverage_floors.py"))
    node = next(x.value for x in tree.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) and x.target.id == "FLOORS")
    floors = {name: bound for name, _, bound in ast.literal_eval(node)}
    assert floors["surfaces"] >= 95, floors
    contains(".github/workflows/ci.yml", "scripts/checks/coverage_floors.py")
elif n == 7:
    files("tests/surfaces/test_surface_layering.py")
    contains("tests/surfaces/test_surface_layering.py", "pyeconomics.surfaces")
elif n == 8:
    parent = text("docs/roadmap/ROADMAP.md")
    assert "Upstash Redis" in parent and "Upstash Valkey" not in parent
    assert "Cloudflare Worker" in parent
    assert "Phases 4–7: anonymous hosted access with per-IP limits, no accounts; staging behind Cloudflare Access" in parent
elif n == 9:
    files(pkg + "surfaces/registry_export.py", pkg + "surfaces/registry_schema.py")
    contains(pkg + "surfaces/registry_export.py", "def registry_document", "def write_registry")
elif n == 10:
    files("tests/surfaces/test_registry_export.py", "tests/surfaces/test_registry_snapshots.py")
    assert git("ls-files", "--", "tests/surfaces/__snapshots__/test_registry_snapshots")
elif n == 11: in_toctree("registry")
elif n == 12: assert project["project"]["scripts"]["pyeconomics"] == "pyeconomics.cli:main"
elif n == 13:
    spec = requirement(deps, "cyclopts")
    assert re.fullmatch(r"cyclopts>=[0-9.]+", spec.replace(" ", "")), spec
elif n == 14:
    files(*(pkg + "cli/" + x + ".py" for x in "app context output model_commands data_commands key_commands cache_commands exporting serve_command mcp_command".split()))
elif n == 15:
    definitions(pkg + "data/credentials/chain.py", ["store_key", "delete_key", "key_source"])
    contains(pkg + "data/credentials/__init__.py", '"store_key"', '"delete_key"', '"key_source"')
elif n == 16: in_toctree("cli")
elif n == 17: files(*(pkg + "exports/" + x + ".py" for x in "layout delimited spreadsheet columnar document bundle reproduction".split()))
elif n == 18:
    definitions(pkg + "exports/bundle.py", ["check_bundle"])
    assert re.search(r"^REPRODUCE_SCRIPT: Final = ", text(pkg + "exports/reproduction.py"), re.M)
elif n == 19: files("tests/providers/test_export_notices.py")
elif n == 20: in_toctree("exports")
elif n == 21:
    assert dependency(extras["server"], "fastapi") and dependency(extras["server"], "uvicorn")
    assert dependency(extras["all"], "fastapi") and dependency(extras["all"], "uvicorn")
elif n == 22:
    files(*(pkg + "server/" + x + ".py" for x in "app pool work formats settings logs".split()))
    definitions(pkg + "server/app.py", ["create_app"])
    contains(pkg + "cli/serve_command.py", "is_loopback")
elif n == 23:
    files("tests/server/test_openapi_snapshot.py")
    assert git("ls-files", "--", "tests/server/__snapshots__/test_openapi_snapshot")
elif n == 24: in_toctree("api")
elif n == 25:
    assert any(re.match(r"limits\[redis\]", x) for x in extras["server"]), extras["server"]
    assert any(re.match(r"limits\[redis\]", x) for x in extras["all"]), extras["all"]
elif n == 26:
    assert dependency(groups["fuzz"], "schemathesis")
    options = project["tool"]["pytest"]["ini_options"]
    assert any(m.startswith("fuzz:") or m == "fuzz" for m in options["markers"])
    selection = options["addopts"][options["addopts"].index("-m") + 1]
    assert re.search(r"\bnot fuzz\b", selection), selection
    files("tests/server/test_api_fuzz.py")
    aggregate("api-fuzz")
elif n == 27:
    assert git("ls-files", "--", "tools/node/package.json") and git("ls-files", "--", "tools/node/package-lock.json")
    files(*("scripts/clients/" + x + ".py" for x in "retitle_openapi python_smoke compare_runs".split()))
    aggregate("clients")
elif n == 28:
    assert "npm-audit" in hooks()
    assert {"npm", "uv", "github-actions"} <= ecosystems()
elif n == 29:
    assert re.search(r"^class SourceDisabledError\(", text(pkg + "data/errors.py"), re.M)
    contains(pkg + "data/config.py", "disabled_providers")
    contains(pkg + "surfaces/problems.py", '"edge-required"', '"too-many-requests"', '"limits-unavailable"', '"source-disabled"')
elif n == 30:
    spec = requirement(extras["mcp"], "mcp")
    floor = re.search(r">=\s*([0-9]+)\.([0-9]+)", spec)
    assert floor and (int(floor[1]), int(floor[2])) >= (2, 3), spec
    assert dependency(extras["all"], "mcp")
elif n == 31:
    files(*(pkg + "mcp/" + x + ".py" for x in "server tools headline schemas execution transport".split()))
    assert re.search(r"^HEADLINE: Final", text(pkg + "mcp/headline.py"), re.M)
elif n == 32:
    files("tests/mcp/test_mcp_tools.py")
    assert git("ls-files", "--", "tests/mcp/__snapshots__/test_mcp_tools")
elif n == 33:
    files("scripts/mcp/inspector_checks.py")
    aggregate("mcp-inspector")
elif n == 34:
    contains(pkg + "data/resolver.py", '"llm_use":')
    contains(pkg + "surfaces/gate.py", "def check_document")
    contains(pkg + "data/config.py", "allow_unclear_llm_use")
    in_toctree("mcp")
elif n == 35:
    contains(pkg + "mcp/apps.py", 'CHART_URI: Final = "ui://pyeconomics/chart"', "PLOTLY_JS_VERSION", "PLOTLY_JS_INTEGRITY")
    files("tests/mcp/test_mcp_apps.py")
elif n == 36:
    import json
    entry = json.loads(text("server.json"))
    version = project["project"]["version"]
    assert entry["name"] == "io.github.pyeconomics-dev/pyeconomics" and entry["version"] == version, entry["version"]
    assert entry["packages"] and all(p["version"] == version for p in entry["packages"])
    assert text("server.json").count(version) >= 3
    contains("README.md", "<!-- mcp-name: io.github.pyeconomics-dev/pyeconomics -->")
elif n == 37:
    body = workflow("mcp-registry")
    assert re.search(r"^permissions: \{\}\s*$", body, re.M)
    assert body.count("id-token: write") == 1
    assert re.search(r"^    environment:\s*\n      name: mcp-registry\s*$", body, re.M)
    assert re.search(r"MCP_PUBLISHER_SHA256: [0-9a-f]{64}\s*$", body, re.M)
    assert "sha256sum --check --strict" in body and "login github-oidc" in body
    assert not re.search(r"\bsecrets\.", body)
elif n == 38:
    body = text("docs/mcp-evaluations.md")
    result = re.search(r"^- Result: (\d+) of (\d+) tasks succeeded", body, re.M)
    assert result and result[1] == result[2] and int(result[2]) >= 8, result
    assert not re.search(r"^\|[^|\n]+\|\s*failed\s*\|", body, re.M | re.I)
    in_toctree("mcp-evaluations")
elif n == 39: files(*("tests/parity/" + x + ".py" for x in "parity_support parity_world test_parity_golden test_parity_bound test_parity_exports".split()))
elif n == 40: files("tests/parity/test_generator_guard.py")
elif n == 41:
    files("scripts/parity/check_installed.py")
    aggregate("parity")
elif n == 42:
    for name in ("Anthropic", "OpenAI", "Gemini", "OpenRouter"):
        assert re.search(r"^class " + name + r"\(AiProvider\):", text(pkg + "ai/providers.py"), re.M), name
    contains(pkg + "ai/prices.py", "MAX_PRICE_AGE_DAYS: Final = 180", "SOURCES: Final", "read_on")
    files("tests/ai/test_ai_prices.py")
elif n == 43:
    assert extras["ai"] == [], extras["ai"]
    in_toctree("ai")
elif n == 44:
    names = {p["name"] for p in tomllib.loads(text("uv.lock"))["package"]}
    banned = {"anthropic", "openai", "google-genai", "google-generativeai", "mistralai", "cohere", "litellm"}
    assert not names & banned, names & banned
elif n == 45:
    docker = text("Dockerfile")
    froms = re.findall(r"^FROM\s+(\S+)", docker, re.M)
    assert froms and all(re.search(r"@sha256:[0-9a-f]{64}$", image) for image in froms), froms
    user = re.findall(r"^USER\s+(\S+)", docker, re.M)
    assert user and user[-1].split(":")[0] not in {"root", "0"}, user
    assert "PYECONOMICS_MODE=hosted" in docker
    ignored = {line.strip() for line in text(".dockerignore").splitlines()}
    assert {".git", ".env", ".roadmodel/", ".claude/", "planning/"} <= ignored, ignored
elif n == 46: aggregate("container")
elif n == 47: assert "docker" in ecosystems()
elif n == 48:
    body = workflow("deploy-staging")
    assert triggers(body) == {"push", "workflow_dispatch"}
    assert re.search(r"^  push:\s*\n    branches:\s*\[main\]", body, re.M)
    assert re.search(r"^permissions: \{\}\s*$", body, re.M)
    found = jobs(body)
    holders = [name for name, job in found.items() if "id-token: write" in job]
    assert holders == ["deploy"] and body.count("id-token: write") == 1, holders
    assert re.search(r"^    environment:\s*(?:staging\s*$|\n      name: staging\s*$)", found["deploy"], re.M)
    assert re.search(r"uses: google-github-actions/auth@[0-9a-f]{40}\b", body)
    assert "credentials_json" not in body and "workload_identity_provider" in body
elif n == 49:
    body = workflow("staging-health")
    assert triggers(body) == {"schedule", "workflow_dispatch"}
    assert re.search(r"^permissions: \{\}\s*$", body, re.M)
    holders = [name for name, job in jobs(body).items() if "issues: write" in job]
    assert holders == ["report"], holders
    assert "simulate_failure" in body
elif n == 50: contains("docs/operations/staging.md", "rollback", "staging-health")
elif n == 51:
    files("tools/node/edge/worker.mjs", "tools/node/edge/worker.test.mjs")
    contains("tools/node/edge/worker.mjs", "/healthz", "/version")
elif n == 52: assert re.search(r"^## Post-merge addendum \(\d{4}-\d{2}-\d{2}\) — Phase 4 changes to verify-phase03\.sh", text("docs/roadmap/phase03-roadmap.md"), re.M)
elif n == 53:
    body = text("docs/releases/1.0.0b1-readiness.md")
    assert set(range(1, 15)) <= {int(x) for x in re.findall(r"^## (\d+)\.", body, re.M)}
    assert re.search(r"^\*{0,2}Decision: GO\*{0,2}", body, re.M)
    assert not re.search(r"\|\s*FAIL\s*\||^FAIL\b", body, re.M)
elif n == 54: assert git("tag", "--merged", "origin/main", "--list", "v1.0.0b1.dev*")
elif n == 55: subprocess.check_call(["git", "merge-base", "--is-ancestor", "v1.0.0b1", "origin/main"])
elif n == 56: assert re.search(r"^## \[1\.0\.0b1\] - \d{4}-\d{2}-\d{2}", text("CHANGELOG.md"), re.M)
elif n == 57:
    contains("docs/releases/1.0.0b1.md", "# pyeconomics 1.0.0b1", "50 model", "31 provider", "171 concept",
             "pip install --pre 'pyeconomics==1.0.0b1'", "uvx --from 'pyeconomics[mcp]==1.0.0b1' pyeconomics mcp")
elif n == 58:
    contains("README.md", "pip install --pre pyeconomics==1.0.0b1", "0.2.6", "pyeconomics serve", "pyeconomics mcp")
    contains("docs/index.md", *("{doc}`" + page + "`" for page in "cli exports api mcp ai".split()))
elif n == 59:
    # Every id an earlier phase's release shipped is still in the ledger,
    # recorded exactly as it was.
    for path in ("src/pyeconomics/core/_released.py", "src/pyeconomics/data/_released.py"):
        before = ledger(git("show", "v1.0.0a2:" + path))
        now = ledger(text(path))
        assert before and len(before) == len(now), path
        for index, entries in before.items():
            changed = [key for key, value in entries.items() if now[index].get(key) != value]
            assert not changed, (path, changed[:5])
elif n == 60:
    files("scripts/verify-phase04.sh")
    assert git("ls-files", "--stage", "--", "scripts/verify-phase04.sh").startswith("100755 ")
elif n == 61: files("docs/phase04-qa-findings.md")
elif n == 62: files("docs/roadmap/phase04-roadmap.md")
elif n == 63:
    matrices = re.findall(r"^\s+phase:\s*\[([^]]+)\]\s*$", workflow("phase-verify"), re.M)
    assert len(matrices) >= 2 and all('"04"' in m for m in matrices)
else: raise ValueError(n)

PY
}

c64() {
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
  for hook in gitleaks bandit semgrep pip-audit npm-audit licences zizmor; do
    grep -qE "^[[:space:]]+- id: $hook$" .pre-commit-config.yaml || fail "missing $hook hook"
  done
  [ -f .github/workflows/security.yml ] || fail "security workflow missing"
  "$PY" - << 'PY'
import re
from pathlib import Path
staging_secrets = {"GITHUB_TOKEN", "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET"}
for path in Path(".github/workflows").glob("*.yml"):
    if path.name == "providers-live.yml":
        continue
    # github.token and secrets.GITHUB_TOKEN are ephemeral built-in tokens.
    body = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"\bsecrets\s*\[|toJSON\(secrets\)", body), path.name
    names = re.findall(r"\bsecrets\.([A-Za-z_][A-Za-z_0-9]*)", body)
    if path.name in {"deploy-staging.yml", "staging-health.yml"}:
        assert set(names) <= staging_secrets, path.name
        assert re.search(r"^\s+environment:\s*(?:staging\s*$|\n\s+name:\s*staging\s*$)", body, re.M), path.name
    else:
        assert set(names) <= {"GITHUB_TOKEN"}, path.name
PY
}
run_static() {
  CURRENT_MODE=fast
  section "Static checks 1-64"
  check 1 "Phase 4 roadmap and planning kit tracked" static_check 1
  check 2 "Concurrency regression and core/context.py's lock" static_check 2
  check 3 "Audit's threaded core and data tests" static_check 3
  check 4 "ADR-0012 accepted with twenty decisions and indexed" static_check 4
  check 5 "Surface core: invoke, problems, codec, envelope, budgets" static_check 5
  check 6 "Surfaces coverage floor at 95% in CI" static_check 6
  check 7 "Surface layering test" static_check 7
  check 8 "Parent amendments: Upstash Redis, edge, no hosted keys" static_check 8
  check 9 "Registry export and schema" static_check 9
  check 10 "Registry export and schema snapshot tests" static_check 10
  check 11 "Registry guide in the toctree" static_check 11
  check 12 "pyeconomics console script" static_check 12
  check 13 "Cyclopts a floor-only runtime dependency" static_check 13
  check 14 "CLI command groups" static_check 14
  check 15 "store_key, delete_key and key_source exported" static_check 15
  check 16 "CLI guide in the toctree" static_check 16
  check 17 "Exports and their writers" static_check 17
  check 18 "Bundle check and the reproduce template" static_check 18
  check 19 "Per-provider export notice test" static_check 19
  check 20 "Exports guide in the toctree" static_check 20
  check 21 "Server extra with FastAPI and Uvicorn, in all" static_check 21
  check 22 "Server app factory, pool and serve's loopback guard" static_check 22
  check 23 "OpenAPI snapshot test" static_check 23
  check 24 "REST API guide in the toctree" static_check 24
  check 25 "limits[redis] in the server extra and all" static_check 25
  check 26 "Fuzz group, marker, deselection and api-fuzz in test" static_check 26
  check 27 "tools/node lockfile, client scripts, clients in test" static_check 27
  check 28 "npm-audit hook and npm ecosystem" static_check 28
  check 29 "Disable switch, SourceDisabledError and four rows" static_check 29
  check 30 "MCP extra at mcp>=2.3, in all" static_check 30
  check 31 "MCP server modules and the headline list" static_check 31
  check 32 "tools/list snapshot test" static_check 32
  check 33 "Inspector checks and mcp-inspector in test" static_check 33
  check 34 "llm_use gate, resolver skip reason, MCP guide" static_check 34
  check 35 "MCP Apps chart resource pinned by version and SRI" static_check 35
  check 36 "server.json at the project version; README marker" static_check 36
  check 37 "MCP Registry workflow: OIDC, environment, checksum pin" static_check 37
  check 38 "Agent evaluations: no failed task, in the toctree" static_check 38
  check 39 "Cross-surface parity suite" static_check 39
  check 40 "Generator guard" static_check 40
  check 41 "Installed parity helper and parity in test" static_check 41
  check 42 "AI providers and the dated price table" static_check 42
  check 43 "Empty ai extra and the AI guide in the toctree" static_check 43
  check 44 "No AI client library in the lock" static_check 44
  check 45 "Dockerfile pinned, non-root, hosted; context exclusions" static_check 45
  check 46 "Container job in test" static_check 46
  check 47 "Docker ecosystem" static_check 47
  check 48 "deploy-staging: main/dispatch, staging, OIDC by SHA" static_check 48
  check 49 "staging-health: schedule/dispatch, issues only in report" static_check 49
  check 50 "Staging operations runbook" static_check 50
  check 51 "Edge Worker source and tests" static_check 51
  check 52 "Phase 3 roadmap's Phase 4 addendum" static_check 52
  check 53 "Fourteen-section readiness GO; no unresolved FAIL" static_check 53
  check 54 "Merged beta rehearsal tag" static_check 54
  check 55 "Production beta tag merged into main" static_check 55
  check 56 "Dated 1.0.0b1 changelog" static_check 56
  check 57 "Release notes: counts and install commands" static_check 57
  check 58 "README and index describe the shipped surfaces" static_check 58
  check 59 "Earlier phases' ledger entries unchanged" static_check 59
  check 60 "Executable Phase 4 verifier in index" static_check 60
  check 61 "QA findings document" static_check 61
  check 62 "Phase roadmap exists" static_check 62
  check 63 "Both CI matrices include 04" static_check 63
  check 64 "Credential backstop, hooks and workflow secret boundary" c64
  vstatic V1.1 "Step 1 deliverables" 1 3
  vstatic V2.1 "Step 2 deliverables" 4 8
  vstatic V3.1 "Step 3 deliverables" 9 11
  vstatic V4.1 "Step 4 deliverables" 12 16
  vstatic V5.1 "Step 5 deliverables" 17 20
  vstatic V6.1 "Step 6 deliverables" 21 24
  vstatic V7.1 "Step 7 deliverables" 25 29
  vstatic V8.1 "Step 8 deliverables" 30 34
  vstatic V9.1 "Step 9 deliverables" 35 38
  vstatic V10.1 "Step 10 deliverables" 39 41
  vstatic V11.1 "Step 11 deliverables" 42 44
  vstatic V12.1 "Step 12 deliverables" 45 47
  vstatic V13.1 "Step 13 deliverables" 48 52
  vstatic V14.1 "Step 14 deliverables" 53 54
  vstatic V15.1 "Step 15 deliverables" 55 59
  vstatic V16.1 "Fast verifier succeeds" 1 64
  vstatic V16.2 "Both phase matrices include 04" 63 63
  vstatic V16.3 "Every static check passes" 1 64
}

# Commands are grouped by the evidence they actually produce. A suite verdict
# is reused only for V-checks whose tests were included in that suite.
venv_python() {
  if [ -x "$1/bin/python" ]; then echo "$1/bin/python"; else echo "$1/Scripts/python.exe"; fi
}
venv_bin() { # venv_bin <venv> <console script>
  if [ -d "$1/bin" ]; then echo "$1/bin/$2"; else echo "$1/Scripts/$2.exe"; fi
}
interpreter() { uv python find --no-config; }

# serving <url> <server command...> -- <client command...>: start a server,
# wait until <url> answers at all, run the client, then stop the server with
# Ctrl+C (Ctrl+Break on Windows) so its workers stop with it, and return the
# client's status. Standard library only.
serving() {
  "$PY" - "$@" << 'PY'
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

url, rest = sys.argv[1], sys.argv[2:]
split = rest.index("--")
server, client = rest[:split], rest[split + 1:]
windows = os.name == "nt"
flags = subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0
proc = subprocess.Popen(server, creationflags=flags, start_new_session=not windows)
status = 1
try:
    for _ in range(240):
        try:
            urllib.request.urlopen(url, timeout=2).close()
            break
        except urllib.error.HTTPError:
            break
        except OSError:
            if proc.poll() is not None:
                sys.exit("the server exited before it answered")
            time.sleep(0.5)
    else:
        sys.exit("the server never answered")
    status = subprocess.call(client)
finally:
    if proc.poll() is None:
        proc.send_signal(signal.CTRL_BREAK_EVENT if windows else signal.SIGINT)
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
sys.exit(status)
PY
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
# The fuzz group runs on Python 3.14 (Schemathesis has no 3.15 wheel), in its
# own environment so the project's .venv keeps its interpreter.
fuzz() {
  UV_PROJECT_ENVIRONMENT="$TMP/fuzz-venv" uv run --locked --python 3.14 --group fuzz \
    pytest -m fuzz tests/server/test_api_fuzz.py -p no:cacheprovider -q
}
docs_build() {
  uv run --locked --group docs --all-extras sphinx-build -E -W --keep-going -b html docs "$TMP/docs" || return 1
  # A successful build alone must not stand in for the surface guides.
  local page
  for page in cli api mcp mcp-evaluations ai exports registry problems; do
    [ -f "$TMP/docs/$page.html" ] || fail "docs build lacks $page.html"
  done
}
artifact_build() {
  uv build --out-dir "$TMP/dist" \
    && uvx --no-config twine==7.0.0 check --strict "$TMP"/dist/* \
    && uv run --no-project python scripts/checks/dist_contents.py "$TMP/dist"
}
wheel_file() {
  local wheel
  wheel=$(printf '%s\n' "$TMP"/dist/*.whl)
  [ -f "$wheel" ] || fail "build did not produce a wheel"
  echo "$wheel"
}
# ci.yml's package job: the console script and a bundle from the clean wheel.
# A subshell, because it works in its own directory.
wheel_package() (
  local wheel py cli
  wheel=$(wheel_file) || return 1
  uv venv --no-config --python "$(interpreter)" -q "$TMP/clean" || return 1
  py=$(venv_python "$TMP/clean")
  cli=$(venv_bin "$TMP/clean" pyeconomics)
  uv pip install --no-config --python "$py" "$wheel" || return 1
  mkdir -p "$TMP/package" && cd "$TMP/package" || return 1
  [ "$("$cli" --version | tr -d '\r')" = "pyeconomics $(cd "$ROOT" && uv version --short)" ] || fail "console script version"
  "$cli" models run foundations.time_value --calculation present_value --rate 0.05 \
    --periods 10 --future-value 100 > cli-run.json || return 1
  "$py" -c 'import pathlib, pyeconomics; inputs = {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}; expected = pyeconomics.run("foundations.time_value", inputs).to_json().encode() + b"\n"; assert pathlib.Path("cli-run.json").read_bytes().replace(b"\r\n", b"\n") == expected, "the console script printed other bytes"' || return 1
  "$cli" models run foundations.time_value --calculation irr --cash-flows "[-100, 30, 40, 50]" \
    --bundle irr.zip > /dev/null && "$cli" bundle check irr.zip > /dev/null || return 1
  uv venv --no-config --python "$(interpreter)" -q "$TMP/reproduce" || return 1
  py=$(venv_python "$TMP/reproduce")
  uv pip install --no-config --python "$py" "$wheel" || return 1
  mkdir irr && "$py" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' irr.zip irr || return 1
  (cd irr && "$py" reproduce.py --out rerun.json && cmp rerun.json result.json)
)
wheel_smoke() {
  local py wheel
  wheel=$(wheel_file) || return 1
  mkdir -p "$TMP/smoke" || return 1
  cp scripts/smoke.py "$TMP/smoke/" || return 1
  py=$(venv_python "$TMP/clean")
  (cd "$TMP/smoke" && "$py" smoke.py --all --min-domains 13) || return 1
  uv venv --no-config --python "$(interpreter)" -q "$TMP/extras" || return 1
  py=$(venv_python "$TMP/extras")
  uv pip install --no-config --python "$py" "${wheel}[econometrics,plot]" || return 1
  (cd "$TMP/smoke" && "$py" smoke.py --all --extras --min-domains 13)
}
# ci.yml's parity job: every surface of the installed wheel, out of process.
wheel_parity() {
  local wheel py
  wheel=$(wheel_file) || return 1
  uv venv --no-config --python "$(interpreter)" -q "$TMP/parity" || return 1
  py=$(venv_python "$TMP/parity")
  uv pip install --no-config --python "$py" "${wheel}[server,mcp]" || return 1
  (cd "$TMP" && "$py" -I "$ROOT/scripts/parity/check_installed.py" "$ROOT/tests/golden" "$(venv_bin "$TMP/parity" pyeconomics)")
}
# Pyodide needs a Linux cross-build environment, so V4.3 reads ci.yml's
# pyodide job for this commit rather than rebuilding it here.
pyodide_job() {
  local sha run
  sha=$(git rev-parse HEAD) || return 1
  run=$(gh run list -R "$REPO" --workflow ci.yml --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId') || return 1
  [ -n "$run" ] || fail "no CI run for HEAD $sha (push it first)"
  gh run view -R "$REPO" "$run" --json jobs --jq \
    '[.jobs[] | select(.name == "pyodide") | .conclusion] | length == 1 and all(. == "success")' | grep -qx true
}
run_python() {
  CURRENT_MODE=python
  cd "$ROOT" || exit 2
  section "--python"
  vcheck TYPES "Locked extras/docs; format, lint and strict types" lint_types
  local suite_status=PASS fuzz_status=PASS combined id
  suite > "$TMP/suite.log" 2>&1 || suite_status=FAIL
  for id in V1.2 V2.2 V3.2 V5.2 V6.2 V8.2 V9.2 V10.2 V11.2; do
    record "$suite_status" "$id" "Full socket-isolated suite, registries, bindings and four coverage floors" "$(log_detail "$TMP/suite.log")"
  done
  fuzz > "$TMP/fuzz.log" 2>&1 || fuzz_status=FAIL
  combined=PASS
  [ "$suite_status" = PASS ] && [ "$fuzz_status" = PASS ] || combined=FAIL
  record "$combined" V7.2 "Hosted-mode suite and Schemathesis on Python 3.14 in both modes" "$(log_detail "$TMP/fuzz.log")"
  vcheck DOCS "Sphinx -W; every surface guide built" docs_build
  vcheck BUILD "Wheel/sdist, strict Twine and artifact allowlist" artifact_build
  local package_status=PASS
  wheel_package > "$TMP/package.log" 2>&1 || package_status=FAIL
  combined=PASS
  [ "$suite_status" = PASS ] && [ "$package_status" = PASS ] || combined=FAIL
  record "$combined" V4.2 "CLI suite and the clean wheel's console script bytes" "$(log_detail "$TMP/package.log")"
  record "$package_status" V5.3 "A bundle from the wheel reruns to identical bytes in a fresh venv" "$(log_detail "$TMP/package.log")"
  local smoke_status=PASS
  wheel_smoke > "$TMP/smoke.log" 2>&1 || smoke_status=FAIL
  record "$smoke_status" SMOKE "Clean core/extras wheel smokes across thirteen domains" "$(log_detail "$TMP/smoke.log")"
  vcheck V10.3 "Out-of-process parity on the installed wheel" wheel_parity
  vcheck V4.3 "ci.yml's pyodide job builds the CLI for this commit" pyodide_job
}

# A free loopback port: a fixed one may belong to another program.
free_port() {
  "$PY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'
}
node_tools() {
  (cd tools/node && npm ci --ignore-scripts --no-fund --no-audit && npm audit --audit-level=high)
}
edge_tests() { (cd tools/node && node --test edge/worker.test.mjs); }
clients() {
  local cli port
  uv run --locked --all-extras --group clients pyeconomics registry export --out tools/node/generated || return 1
  (cd tools/node && npx --no-install openapi-ts && npx --no-install tsc --noEmit && npx --no-install tsc) || return 1
  uv run --locked --all-extras --group clients python scripts/clients/retitle_openapi.py \
    tools/node/generated/openapi.json "$TMP/openapi-titled.json" || return 1
  uv run --locked --all-extras --group clients openapi-python-client generate \
    --path "$TMP/openapi-titled.json" --output-path "$TMP/python-client/pyeconomics_client" \
    --meta none --fail-on-warning || return 1
  cli=$(venv_bin "$ROOT/.venv" pyeconomics)
  port=$(free_port) || return 1
  serving "http://127.0.0.1:$port/healthz" "$cli" serve --port "$port" --workers 1 -- \
    bash -c "cd tools/node && node smoke.mjs http://127.0.0.1:$port '$TMP/ts-run.json'" || return 1
  port=$(free_port) || return 1
  serving "http://127.0.0.1:$port/healthz" "$cli" serve --port "$port" --workers 1 -- \
    uv run --locked --all-extras --group clients python scripts/clients/python_smoke.py \
    "$TMP/python-client" "http://127.0.0.1:$port" "$TMP/py-run.json" || return 1
  uv run --locked --all-extras --group clients python scripts/clients/compare_runs.py "$TMP/ts-run.json" "$TMP/py-run.json"
}
inspector() {
  local cli py port
  export MCP_CATALOG_PATH="$TMP/inspector-catalog.json"
  cli=$(venv_bin "$ROOT/.venv" pyeconomics)
  py=$(venv_python "$ROOT/.venv")
  "$py" scripts/mcp/inspector_checks.py tools/node "$cli" mcp || return 1
  port=$(free_port) || return 1
  serving "http://127.0.0.1:$port/healthz" "$cli" serve --port "$port" --workers 1 -- \
    "$py" scripts/mcp/inspector_checks.py tools/node "http://127.0.0.1:$port/mcp" || return 1
  port=$(free_port) || return 1
  serving "http://127.0.0.1:$port/mcp" "$cli" mcp --transport http --port "$port" -- \
    "$py" scripts/mcp/inspector_checks.py tools/node "http://127.0.0.1:$port/mcp"
}
run_node() {
  CURRENT_MODE=node
  cd "$ROOT" || exit 2
  section "--node"
  vcheck NPM "npm ci and npm audit --audit-level=high in tools/node" node_tools
  vcheck EDGE "Edge Worker tests" edge_tests
  vcheck V7.3 "TypeScript client generated and type-checked; both clients equal" clients
  vcheck V8.3 "MCP Inspector over stdio and Streamable HTTP" inspector
}

IMAGE=pyeconomics:verify-phase04
CONTAINER=pyeconomics-verify-$$
image_scan() {
  local trivy="ghcr.io/aquasecurity/trivy:0.69.3@sha256:bcc376de8d77cfe086a917230e818dc9f8528e3c852f7b1aff648949b6258d1c"
  docker build --build-arg "GIT_SHA=$(git rev-parse HEAD)" -t "$IMAGE" . || return 1
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$TMP:/out" "$trivy" \
    image --skip-version-check --format cyclonedx --output /out/container-sbom.cdx.json "$IMAGE" || return 1
  [ -s "$TMP/container-sbom.cdx.json" ] || fail "no SBOM"
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$trivy" \
    image --skip-version-check --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 "$IMAGE"
}
image_smoke() {
  local port uid status=0
  port=$(free_port) || return 1
  docker run -d --name "$CONTAINER" --read-only --tmpfs /tmp -p "127.0.0.1:$port:8080" \
    -e PYECONOMICS_WORKERS=2 "$IMAGE" > /dev/null || return 1
  uid=$(docker exec "$CONTAINER" id -u | tr -d '\r')
  [ "$uid" = 10001 ] || { docker rm -f "$CONTAINER" > /dev/null; fail "uid $uid, expected 10001"; }
  docker exec "$CONTAINER" python -c "
import importlib.metadata as md
names = {d.metadata['Name'].lower() for d in md.distributions() if d.metadata['Name']}
for banned in ('yfinance', 'keyring', 'blpapi'):
    assert not any(banned in n for n in names), banned
assert 'pyarrow' in names
" || status=1
  docker exec "$CONTAINER" python -c "
import sys, pyeconomics
res = pyeconomics.run('foundations.time_value', calculation='future_value', present_value=1000.0, rate=0.05, periods=10)
sys.stdout.buffer.write(res.to_json().encode('utf-8'))
" > "$TMP/expected-run.json" || status=1
  [ "$status" = 0 ] && "$PY" - "$port" "$(git rev-parse HEAD)" "$TMP/expected-run.json" << 'PY' || status=1
import json
import sys
import time
import urllib.error
import urllib.request
port, sha, expected = sys.argv[1:]
base = f"http://127.0.0.1:{port}"
def call(path, body=None):
    request = urllib.request.Request(base + path, data=body, headers={"Content-Type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
for _ in range(60):
    try:
        status, payload = call("/healthz")
        break
    except OSError:
        time.sleep(0.5)
assert status == 200 and json.loads(payload) == {"status": "ok"}, status
status, payload = call("/version")
version = json.loads(payload)
assert version["git_sha"] == sha and version["mode"] == "hosted", version
run = b'{"calculation":"future_value","present_value":1000.0,"rate":0.05,"periods":10}'
status, payload = call("/v1/models/foundations.time_value/run", run)
assert status == 200 and payload == open(expected, "rb").read(), "the image answered other bytes"
for fmt in ("xlsx", "parquet", "arrow"):
    status, payload = call("/v1/models/foundations.time_value/run?format=" + fmt, run)
    assert status == 200 and payload, fmt
status, payload = call("/v1/series/fred:UNRATE")
problem = json.loads(payload)
assert status == 403 and problem["type"].endswith("/problems/licence-refused") and problem["terms"], status
PY
  docker rm -f "$CONTAINER" > /dev/null 2>&1
  return "$status"
}
run_container() {
  CURRENT_MODE=container
  cd "$ROOT" || exit 2
  section "--container"
  local scan=PASS
  image_scan > "$TMP/image.log" 2>&1 || scan=FAIL
  record "$scan" V12.2 "Image builds; no fixable Critical/High; SBOM kept" "$(log_detail "$TMP/image.log")"
  if [ "$scan" = PASS ]; then
    vcheck V12.3 "Running image: wheel bytes, 403 library-only, non-root, no excluded library" image_smoke
  else
    record FAIL V12.3 "Running image: wheel bytes, 403 library-only, non-root, no excluded library" "no image"
  fi
}

layering() {
  uv run --locked pytest -q tests/surfaces/test_surface_layering.py tests/server/test_server_layering.py \
    tests/mcp/test_mcp_layering.py tests/ai/test_ai_layering.py tests/data/test_layering.py \
    tests/registry/test_model_imports.py tests/parity/test_generator_guard.py
}
security_gate() {
  uv run --locked prek run semgrep-test --all-files || return 1
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
cassette_scan() { uv run --locked pytest -q tests/providers/test_cassette_files.py tests/ai/test_ai_cassettes.py; }
npm_audit() { (cd tools/node && npm audit --audit-level=high); }
run_security() {
  CURRENT_MODE=security
  cd "$ROOT" || exit 2
  section "--security"
  local layers=PASS gate=PASS secrets=PASS cassettes=PASS npm=PASS status=PASS
  layering > "$TMP/layering.log" 2>&1 || layers=FAIL
  record "$layers" V2.3 "Layering, model-import and generator-guard tests" "$(log_detail "$TMP/layering.log")"
  security_gate > "$TMP/gate.log" 2>&1 || gate=FAIL
  cassette_scan > "$TMP/cassettes.log" 2>&1 || cassettes=FAIL
  secret_scan > "$TMP/secrets.log" 2>&1 || secrets=FAIL
  npm_audit > "$TMP/npm.log" 2>&1 || npm=FAIL
  local why=""
  for part in layers gate cassettes secrets npm; do
    [ "${!part}" = PASS ] || { status=FAIL; why="$why $part"; }
  done
  record "$status" V16.4 "Whole-tree secrets, SAST, audit, licences, cassettes and npm audit" "${why:+failed:$why }$( [ "$status" = PASS ] || log_detail "$TMP/gate.log")"
}

api() { gh api "repos/$REPO$1" "${@:2}"; }
issue_closed() { gh issue view "$1" -R "$REPO" --json state --jq .state | grep -qx CLOSED; }
issue_157() { issue_closed 157; }
issue_162() { issue_closed 162; }
# The staging host and origin are environment variables, not secrets.
staging_env() {
  STAGING_HOST=$(api /environments/staging/variables/STAGING_HOST --jq .value) || return 1
  ORIGIN_URL=$(api /environments/staging/variables/ORIGIN_URL --jq .value) || return 1
  export STAGING_HOST ORIGIN_URL
}
newest_run() { # newest_run <workflow file>: "<conclusion> <head sha>" of the newest run on main
  api "/actions/workflows/$1/runs?branch=main&per_page=1" --jq '.workflow_runs[0] | "\(.conclusion) \(.head_sha)"'
}
deployed() {
  local run
  run=$(newest_run deploy-staging.yml) || return 1
  [ "${run%% *}" = success ] || fail "newest deploy-staging run: ${run%% *}"
  staging_env || return 1
  uv run --locked --all-extras python scripts/verify_phase04_live.py version "${run#* }"
}
staging() {
  staging_env || return 1
  uv run --locked --all-extras python scripts/verify_phase04_live.py staging
}
# gcloud's Git Bash wrapper passes its own /c/... path to Python, which only
# works with the path conversion MSYS_NO_PATHCONV turns off.
gcloud() { env -u MSYS_NO_PATHCONV gcloud "$@"; }
health_budget() {
  local run billing
  run=$(newest_run staging-health.yml) || return 1
  [ "${run%% *}" = success ] || fail "newest staging-health run: ${run%% *}"
  # Read-only; the billing account and budget are never printed.
  billing=$(gcloud billing projects describe pyeconomics-staging --format='value(billingAccountName)' 2> /dev/null) || fail "gcloud cannot read the project's billing"
  gcloud billing budgets list --billing-project=pyeconomics-staging --billing-account="${billing#billingAccounts/}" --format=json 2> /dev/null > "$TMP/budgets.json" || fail "gcloud cannot list budgets"
  "$PY" - "$TMP/budgets.json" << 'PY'
import json
import sys
# The staging project's own budget, found by its scope rather than its name.
budgets = [b for b in json.load(open(sys.argv[1])) if b.get("budgetFilter", {}).get("projects") == ["projects/129496897969"]]
assert len(budgets) == 1, "no single budget scoped to pyeconomics-staging"
budget = budgets[0]
amount = budget["amount"]["specifiedAmount"]
assert amount.get("currencyCode") == "USD" and int(amount.get("units", 0)) == 1, "budget amount"
assert sorted(t["thresholdPercent"] for t in budget["thresholdRules"]) == [0.5, 0.9, 1.0], "thresholds"
assert budget.get("notificationsRule", {}).get("pubsubTopic", "").endswith("/topics/staging-budget-alerts"), "topic"
PY
}
rtd() {
  local sha
  sha=$(api /commits/main --jq .sha) || return 1
  "$PY" - "$sha" << 'PY'
import json
import sys
import urllib.request
base = "https://app.readthedocs.org/api/v3/projects/pyeconomics/"
# Cloudflare in front of Read the Docs refuses Python's default User-Agent.
def fetch(url, decode=True):
    request = urllib.request.Request(url, headers={"User-Agent": "pyeconomics-verify/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response) if decode else response.read().decode()
main = fetch(base + "versions/main/")
builds = fetch(base + "versions/main/builds/?limit=1")["results"]
assert main["active"] and main["built"] and not main["hidden"]
assert builds and builds[0]["success"] and builds[0]["commit"] == sys.argv[1], "newest main build is not main's HEAD"
assert "0.2.6 documentation" in fetch("https://pyeconomics.readthedocs.io/en/stable/", False)
for page in ("cli", "api", "mcp", "exports", "ai"):
    assert "<html" in fetch(f"https://pyeconomics.readthedocs.io/en/main/{page}.html", False), page
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
  tag=$(git tag --merged origin/main --list 'v1.0.0b1.dev*' --sort=-version:refname | head -n 1 | tr -d '\r')
  version=${tag#v}
  [ -n "$version" ] || fail "no merged rehearsal tag"
  attested test.pypi "$version"
}
production() {
  attested pypi 1.0.0b1 || return 1
  gh release view v1.0.0b1 -R "$REPO" --json isDraft,isPrerelease,tagName \
    --jq '.isDraft == false and .isPrerelease == true and .tagName == "v1.0.0b1"' | grep -qx true || fail "GitHub pre-release"
  "$PY" - << 'PY' || return 1
import json
import urllib.request
url = "https://registry.modelcontextprotocol.io/v0.1/servers/io.github.pyeconomics-dev%2Fpyeconomics/versions/1.0.0b1"
with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pyeconomics-verify/1.0"}), timeout=30) as response:
    entry = json.load(response)
server = entry.get("server", entry)
assert server["name"] == "io.github.pyeconomics-dev/pyeconomics" and server["version"] == "1.0.0b1", server.get("version")
PY
  rtd
}
required_checks() {
  api /branches/main/protection/required_status_checks --jq \
    '.strict == true and (.contexts | length == 24 and index("phase-verify-fast (04)") != null and index("phase-verify-security (04)") != null)' | grep -qx true
}
environment_policy() {
  api /environments/staging --jq '.deployment_branch_policy.custom_branch_policies == true' | grep -qx true || fail "staging lacks a custom branch policy"
  api /environments/staging/deployment-branch-policies --jq \
    '[.branch_policies[] | "\(.type):\(.name)"] == ["branch:main"]' | grep -qx true || fail "staging deploys from more than main"
  gh secret list -R "$REPO" --env staging --json name > "$TMP/staging-secrets.json" || return 1
  "$PY" - "$TMP/staging-secrets.json" << 'PY' || return 1
import json
import sys
with open(sys.argv[1]) as stream:
    names = {item["name"] for item in json.load(stream)}
assert {"CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET"} <= names
PY
  [ "$(gh secret list -R "$REPO" --json name --jq length)" = 0 ] || fail "a repository secret exists"
}
run_live() {
  CURRENT_MODE=live
  cd "$ROOT" || exit 2
  section "--live"
  vcheck V1.3 "Issue #157 closed" issue_157
  vcheck V7.4 "Issue #162 closed" issue_162
  vcheck V13.2 "Newest deploy-staging on main green; edge /version reports its SHA" deployed
  vcheck V13.3 "Edge: run equals the API, hosted-safe 200, library-only 403, refusals, both 429 layers" staging
  vcheck V13.4 "Newest staging-health on main green; budget at 50/90/100%" health_budget
  vcheck V14.2 "TestPyPI rehearsal wheel/sdist provenances" rehearsal
  vcheck V15.2 "PyPI beta provenances, pre-release, MCP Registry and RTD guides" production
  vcheck V16.7 "Both phase 04 jobs required, strict, 24 checks" required_checks
  vcheck V16.8 "Staging environment main-only; named secrets; no repo secrets" environment_policy
}

# Run the isolated helper with every ambient credential removed; the tested
# credential chain may read the maintainer's OS keyring. No value is logged.
isolated_helper() { # isolated_helper <python> <args...>
  "$PY" - "$ROOT/scripts/verify_phase04_live.py" "$TMP" "$@" << 'PY'
import os
import subprocess
import sys
from pathlib import Path
script, temp, py, *args = sys.argv[1:]
env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY") and not k.startswith("PYECONOMICS_")}
env.update(PYECONOMICS_CONFIG_DIR=str(Path(temp) / "recipe-config"), PYECONOMICS_CACHE_DIR=str(Path(temp) / "recipe-cache"))
subprocess.run([py, "-I", script, *args], cwd=temp, env=env, check=True)
PY
}
published_install() {
  local py wrapper
  mkdir -p "$TMP/published-smoke" || return 1
  git show v1.0.0b1:scripts/smoke.py > "$TMP/published-smoke/smoke.py" || return 1
  uv venv --no-config --seed --python "$(interpreter)" "$TMP/published" || return 1
  py=$(venv_python "$TMP/published")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --pre --index-url https://pypi.org/simple/ pyeconomics==1.0.0b1 || return 1
  (cd "$TMP/published-smoke" && "$py" smoke.py --all --min-domains 13 && "$py" -m pip check) || return 1
  isolated_helper "$py" published "$(venv_bin "$TMP/published" pyeconomics)" || return 1
  # The MCP server through uvx; the Inspector compares its answers with the
  # same release installed on the same interpreter. A wrapper without flags,
  # because the Inspector's CLI would read uvx's --from as its own.
  uv venv --no-config --seed --python 3.12 "$TMP/published-mcp" || return 1
  py=$(venv_python "$TMP/published-mcp")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --pre --index-url https://pypi.org/simple/ 'pyeconomics[mcp]==1.0.0b1' || return 1
  if [ -d "$TMP/published-mcp/Scripts" ]; then
    wrapper="$TMP/uvx-mcp.cmd"
    printf '@echo off\r\nuvx --no-config --python 3.12 --from "pyeconomics[mcp]==1.0.0b1" pyeconomics mcp\r\n' > "$wrapper"
  else
    wrapper="$TMP/uvx-mcp.sh"
    printf '#!/bin/sh\nexec uvx --no-config --python 3.12 --from "pyeconomics[mcp]==1.0.0b1" pyeconomics mcp\n' > "$wrapper"
    chmod +x "$wrapper"
  fi
  [ -d tools/node/node_modules ] || (cd tools/node && npm ci --ignore-scripts --no-fund --no-audit) || return 1
  MCP_CATALOG_PATH="$TMP/published-catalog.json" "$py" -I scripts/mcp/inspector_checks.py tools/node "$wrapper" || return 1
  # 0.2.6 declares Python >=3.11,<3.13, so the stable check stays on 3.12.
  uv venv --no-config --seed --python 3.12 "$TMP/stable" || return 1
  py=$(venv_python "$TMP/stable")
  "$py" -m pip --isolated install --timeout 30 --retries 2 --index-url https://pypi.org/simple/ pyeconomics || return 1
  (cd "$TMP" && "$py" -c 'from importlib.metadata import version; assert version("pyeconomics") == "0.2.6"' && "$py" -m pip check)
}
alarms() {
  "$PY" - "$QA" "$REPO" << 'PY'
import json
import re
import subprocess
import sys
from pathlib import Path
body = Path(sys.argv[1]).read_text(encoding="utf-8")
repo = sys.argv[2]
assert re.search(r"^Notification received: confirmed by the maintainer", body, re.M), "no confirmed notification"
assert re.search(r"^Budget notification received: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", body, re.M), "no budget notification"
match = re.search(r"^Synthetic staging-health alarm run: https://github.com/[^/]+/[^/]+/actions/runs/([0-9]+)", body, re.M)
assert match, "no alarm run"
run = json.loads(subprocess.check_output(["gh", "run", "view", match[1], "-R", repo, "--json", "workflowName,conclusion,event,headBranch,jobs"]))
assert (run["workflowName"], run["conclusion"], run["event"], run["headBranch"]) == ("staging-health", "failure", "workflow_dispatch", "main"), run
assert {job["name"]: job["conclusion"] for job in run["jobs"]}.get("report the probe failure") == "success", "report job"
issue = re.search(r"^Synthetic staging-health issue: https://github.com/[^/]+/[^/]+/issues/([0-9]+)", body, re.M)
assert issue, "no alarm issue"
evidence = json.loads(subprocess.check_output(["gh", "issue", "view", issue[1], "-R", repo, "--json", "body,state,comments,labels"]))
assert evidence["state"] == "CLOSED" and match[1] in evidence["body"], "issue state or run link"
assert any(label["name"] == "staging-health" for label in evidence["labels"]), "label"
assert any("phase04-qa-findings.md" in comment["body"] for comment in evidence["comments"]), "QA comment"
newest = json.loads(subprocess.check_output(["gh", "api", f"repos/{repo}/actions/workflows/staging-health.yml/runs?branch=main&per_page=1"]))
assert newest["workflow_runs"][0]["conclusion"] == "success", "newest staging-health run is not green"
PY
}
earlier_phases() {
  # Phase 3 executes Phase 2 --post (which executes Phase 1's) as V20.6.
  # Require its fresh nested verdict, so each command runs once.
  HYPOTHESIS_PROFILE=ci bash scripts/verify-phase03.sh --post > "$TMP/phase03.log" 2>&1
  local third=$?
  log_detail "$TMP/phase03.log"
  [ "$third" -eq 0 ] && grep -qE '^PASS  V20\.6[[:space:]]' "$TMP/phase03.log"
}
main_ci() {
  local sha run
  sha=$(api /commits/main --jq .sha) || return 1
  run=$(gh run list -R "$REPO" --workflow ci.yml --branch main --event push --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId') || return 1
  [ -n "$run" ] || fail "no CI run for main HEAD"
  gh run view -R "$REPO" "$run" --json conclusion --jq '.conclusion == "success"' | grep -qx true
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
  cd "$ROOT" || exit 2
  section "--post"
  vcheck V15.3 "Fresh PyPI install, CLI and smoke; uvx MCP Inspector; stable 0.2.6" published_install
  vcheck V16.5 "Synthetic staging alarm, its issue, confirmed notification, budget notice" alarms
  vcheck V16.6 "Phase 3 full --post (with Phases 2 and 1) remains green" earlier_phases
  vcheck PR "Current pull request checks or main HEAD CI" pr_checks
}

START=$SECONDS
run_static
case "$MODE" in
  --python) run_python ;;
  --node) run_node ;;
  --container) run_container ;;
  --security) run_security ;;
  --live) run_live ;;
  --all) run_python; run_node; run_container; run_security ;;
  --post) run_python; run_node; run_container; run_security; run_live; run_post ;;
esac
section "Summary ($MODE, $((SECONDS - START))s)"
printf '%-10s %6s %6s\n' mode passed failed
for m in fast python node container security live post; do
  if [ -n "${MODE_PASS[$m]:-}${MODE_FAIL[$m]:-}" ]; then
    printf '%-10s %6s %6s\n' "$m" "${MODE_PASS[$m]:-0}" "${MODE_FAIL[$m]:-0}"
  fi
done
if [ "$FAILED" = 0 ]; then echo "RESULT: PASS"; exit 0; fi
echo "RESULT: FAIL"
exit 1
