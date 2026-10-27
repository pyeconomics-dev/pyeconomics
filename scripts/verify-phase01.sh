#!/usr/bin/env bash
# scripts/verify-phase01.sh
#
# Phase 1 (Reset & Foundation) verification: the phase roadmap's 45 static
# deliverable checks (Steps 1-11), 5 Step 12 self-checks, and the V1-V12
# post-implementation matrix (docs/roadmap/phase01-roadmap.md,
# "Post-Implementation Verification"). Later phases copy its mode contract.
#
#   --fast       static checks 1-50 (the default; CI-safe on Ubuntu)
#   --python     static + uv sync, ruff, mypy, pytest --cov, build, twine,
#                artifact allowlist and a clean-venv import
#   --security   the security gate over the whole tree, and zizmor over
#                legacy/0.2.x's workflows (CI-safe on Ubuntu)
#   --live       GitHub settings, PyPI, TestPyPI, Read the Docs, RDAP and
#                funding profiles; local only, with the maintainer's gh session
#   --all        --fast + --python + --security
#   --post       --all + --live + the post checks (fixture re-record, clean
#                installs, planted-finding proof, synthetic alarm) + gh pr checks
#
# Every check prints one PASS or FAIL line naming its deliverable. The script
# exits 0 when every check it ran passed, 1 otherwise, and 2 on bad usage.
# It never prints a token, a secret value or the environment.

set -uo pipefail

REPO="${VERIFY_REPO:-pyeconomics-dev/pyeconomics}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "verify-phase01.sh: run inside the repository" >&2
  exit 2
}
cd "$ROOT" || exit 2
export MSYS_NO_PATHCONV=1 # Git Bash: keep rev:path arguments intact

LEGACY=origin/legacy/0.2.x
ROADMAP=docs/roadmap/phase01-roadmap.md
QA=docs/phase01-qa-findings.md

usage() {
  sed -n '8,18p' "$0" | sed 's/^# \{0,1\}//'
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
  echo "verify-phase01.sh: needs python3 (3.11 or later) on PATH" >&2
  exit 2
fi

TMP="$(mktemp -d)"
# Git Bash: a mixed path (E:/...) means the same directory to bash and to
# native tools, which see paths unconverted under MSYS_NO_PATHCONV.
if command -v cygpath > /dev/null 2>&1; then TMP="$(cygpath -m "$TMP")"; fi
trap 'rm -rf "$TMP"' EXIT

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
  if out="$($fn 2>&1)"; then
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

legacy_show() { git show "$LEGACY:$1"; }

# Every `uses:` in the given workflow text is a 40-hex SHA pin or a local
# reusable workflow (`./...`).
unpinned_uses() {
  grep -E '^\s*(-\s+)?uses:' \
    | sed -E 's/^\s*(-\s+)?uses:\s*//; s/\s+#.*$//; s/["'\'']//g' \
    | grep -vE '^\./' \
    | grep -vE '@[0-9a-f]{40}$' || true
}

# Each job's first step uses step-security/harden-runner, and every job has
# steps (a reusable-workflow call has none and is reported).
harden_first() { # harden_first <file>
  awk '
    function finish() { if (job != "" && !ok) bad = bad " " job }
    /^jobs:/ { injobs = 1; next }
    injobs && /^  [A-Za-z0-9_-]+:[[:space:]]*$/ {
      finish(); job = $1; sub(":", "", job); ok = 0; state = 0; next
    }
    injobs && /^    steps:/ { state = 1; next }
    state == 1 && /^      - / { state = 2 }
    state == 2 && /^      - / && started { state = 3 }
    state == 2 { started = 1; if ($0 ~ /step-security\/harden-runner@/) ok = 1 }
    state != 2 { started = 0 }
    END { finish(); if (bad != "") { print "no harden-runner first:" bad; exit 1 } }
  ' "$1"
}

# --------------------------------------------------------------------------
# Static checks 1-50
# --------------------------------------------------------------------------

# Step 1 — preserve and bootstrap
c01() {
  tracked docs/roadmap/ROADMAP.md || fail "ROADMAP.md untracked"
  tracked docs/roadmap/phase01-roadmap.md || fail "phase01-roadmap.md untracked"
}
c02() {
  local p
  for p in planning/model-selector.txt planning/model-tier-cost-scale.md \
    planning/settings-display.md planning/templates planning/prompts \
    planning/HOW-TO-USE.md; do
    tracked "$p" || fail "$p untracked"
  done
  tracked planning/user-context.md && fail "planning/user-context.md is tracked"
  git check-ignore -q planning/user-context.md || fail "planning/user-context.md not ignored"
}
c03() {
  local sha
  sha=$(git rev-parse -q --verify 'refs/tags/archive/dev-2024-10^{commit}') || fail "tag missing"
  [ "$sha" = d4a692d7c76c75119c98dbc980d0ec5454a8fa05 ] || fail "peels to $sha"
}
c04() {
  local sha
  sha=$(git rev-parse -q --verify 'refs/tags/archive/legacy-dev-0.2.6^{commit}') || fail "tag missing"
  [ "$sha" = 2b7e8a6e1dd3dbc11b4a8e395e8679fe31487d15 ] || fail "peels to $sha"
}
c05() {
  local parent
  parent=$(git rev-parse -q --verify 'refs/remotes/origin/archive/0.2-dev-wip^') || fail "branch missing"
  [ "$parent" = d4a692d7c76c75119c98dbc980d0ec5454a8fa05 ] || fail "parent is $parent"
}

# Step 2 — legacy fix and pipeline (read from legacy/0.2.x)
c06() {
  local src="$TMP/fred_api.py"
  legacy_show pyeconomics/api/fred_api.py > "$src" || fail "fred_api.py missing"
  "$PY" - "$src" << 'EOF'
import ast, re, sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
methods = {"debug", "info", "warning", "warn", "error", "critical", "exception", "log"}
key = re.compile(r"api_key|key_retrieved", re.IGNORECASE)
bad = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in methods:
        base = node.func.value
        name = getattr(base, "id", "") or getattr(base, "attr", "")
        if not re.search(r"log", name, re.IGNORECASE):
            continue
        for arg in [*node.args, *(k.value for k in node.keywords)]:
            for sub in ast.walk(arg):
                ident = getattr(sub, "id", None) or getattr(sub, "attr", None)
                if ident and key.search(ident):
                    bad.append(node.lineno)
if bad:
    print("logging call interpolates the key at line(s)", sorted(set(bad)))
    sys.exit(1)
EOF
}
c07() {
  local p
  for p in tests/test_credential_logging.py scripts/check_credential_logging.py; do
    git cat-file -e "$LEGACY:$p" 2> /dev/null || fail "$p missing on legacy/0.2.x"
  done
}
c08() {
  local wf
  wf=$(legacy_show .github/workflows/release.yml) || fail "release.yml missing"
  printf '%s\n' "$wf" | grep -qE "^\s+tags:\s*\[\s*['\"]v0\.2\.\*['\"]\s*\]\s*$" || fail "tag trigger is not v0.2.* only"
  [ "$(printf '%s\n' "$wf" | grep -cE '^\s+tags:')" = 1 ] || fail "more than one tag trigger"
  printf '%s\n' "$wf" | grep -qE '^\s*password:' && fail "password: present"
  printf '%s\n' "$wf" | grep -qE '^\s+name:\s*testpypi\s*$' || fail "no testpypi environment"
  printf '%s\n' "$wf" | grep -qE '^\s+name:\s*pypi\s*$' || fail "no pypi environment"
  [ "$(printf '%s\n' "$wf" | grep -cE '^\s+id-token:\s*write')" = 2 ] || fail "id-token: write is not on exactly two jobs"
}
c09() {
  local f bad=""
  for f in $(git ls-tree --name-only "$LEGACY" .github/workflows/); do
    bad="$bad$(legacy_show "$f" | unpinned_uses)"
  done
  [ -z "$bad" ] || fail "unpinned: $bad"
  git cat-file -e "$LEGACY:.github/workflows/docs.yml" 2> /dev/null && fail "docs.yml present"
  return 0
}
c10() {
  git rev-parse -q --verify 'refs/tags/v0.2.6.dev1' > /dev/null || fail "tag missing"
  git merge-base --is-ancestor v0.2.6.dev1 "$LEGACY" || fail "not an ancestor of legacy/0.2.x"
}

# Step 3 — readiness gate
c11() {
  local f=docs/releases/0.2.6-readiness.md n
  [ -f "$f" ] || fail "$f missing"
  for n in 1 2 3 4 5 6 7 8 9 10; do
    grep -qE "^## $n\. " "$f" || fail "section $n missing"
  done
  # A FAIL verdict cell must read "FAIL, resolved".
  grep -nE '\|\s*FAIL\s*(\||$)' "$f" && fail "unresolved FAIL"
  grep -qE '^Decision: GO' "$f" || fail "no Decision: GO line"
}

# Step 4 — 0.2.6 release
c12() {
  git merge-base --is-ancestor v0.2.6 "$LEGACY" || fail "v0.2.6 not on legacy/0.2.x"
  git show v0.2.6:__version__.py | grep -qE "^__version__ = ['\"]0\.2\.6['\"]" || fail "__version__ at v0.2.6 is not 0.2.6"
}
c13() {
  # Consume each producer's full output: grep -q can cause a false SIGPIPE
  # failure under pipefail when a valid match occurs before the pipe drains.
  legacy_show markdown/CHANGELOG.md | grep -E '^## \[0\.2\.6\] - [0-9]{4}-[0-9]{2}-[0-9]{2}' > /dev/null || fail "no dated [0.2.6] entry"
  sed -n '/^## Release record/,$p' docs/releases/0.2.6-readiness.md \
    | grep -E 'GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}' > /dev/null || fail "no Release record with a GHSA id"
}

# Step 5 — characterize and archive
c14() {
  "$PY" - << 'EOF'
import hashlib, json, pathlib, sys

base = pathlib.Path("tests/fixtures/legacy")
manifest = json.loads((base / "manifest.json").read_bytes())
bad = []
for name, digest in manifest["files"].items():
    path = base / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        bad.append(name)
recorder = pathlib.Path("scripts/legacy/record_characterization.py")
if hashlib.sha256(recorder.read_bytes()).hexdigest() != manifest["recorder_sha256"]:
    bad.append(str(recorder))
if bad:
    print("mismatch:", ", ".join(bad))
    sys.exit(1)
EOF
}
c15() {
  local f=scripts/legacy/record_characterization.py
  sed -n '/^# \/\/\/ script$/,/^# \/\/\/$/p' "$f" | grep -qE '"pyeconomics==0\.2\.6"' || fail "PEP 723 block does not pin pyeconomics==0.2.6"
}
c16() {
  local heads open_heads branch bad=""
  [ -z "$(git ls-files dev/)" ] || fail "dev/ paths are tracked"
  heads=$(git ls-remote --heads origin | sed 's#.*refs/heads/##') || fail "git ls-remote failed"
  open_heads=$(open_pr_heads)
  for branch in $heads; do
    case "$branch" in
      main | legacy/0.2.x | archive/*) continue ;;
    esac
    printf '%s\n' "$open_heads" | grep -qxF "$branch" && continue
    bad="$bad $branch"
  done
  [ -z "$bad" ] || fail "unexpected branches:$bad"
}
# Head branches of open pull requests, through the GitHub API (gh in CI
# reads GH_TOKEN; locally, the maintainer's session).
open_pr_heads() {
  command -v gh > /dev/null 2>&1 || return 0
  gh api "repos/$REPO/pulls?state=open&per_page=100" --paginate --jq '.[].head.ref' 2> /dev/null || true
}

# Step 6 — ADRs
ADRS="0001 0002 0003 0004 0005 0006 0007 0009 0010"
c17() {
  local n
  [ -f docs/adr/README.md ] || fail "README.md missing"
  [ -f docs/adr/template.md ] || fail "template.md missing"
  for n in $ADRS; do
    compgen -G "docs/adr/$n-*.md" > /dev/null || fail "ADR $n missing"
  done
}
c18() {
  local n f date
  for n in $ADRS; do
    f=$(compgen -G "docs/adr/$n-*.md" | head -n 1)
    grep -qE '^- Status: Accepted\s*$' "$f" || fail "$f is not Accepted"
    date=$(sed -nE 's/^- Date: ([0-9-]+).*/\1/p' "$f" | head -n 1)
    grep -qE "^\| \[$n\]\($(basename "$f")\) \|.*\| Accepted \| $date \|" docs/adr/README.md \
      || fail "index row for $n is not Accepted with $date"
  done
  # ADR-0008: reserved in Phase 1, accepted by Phase 2 Step 1 (post-merge
  # addendum in the phase roadmap). Either state passes; a half-done one fails.
  grep -qE '^\| 0008 \|.*Reserved' docs/adr/README.md && return 0
  f=$(compgen -G "docs/adr/0008-*.md" | head -n 1)
  [ -n "$f" ] || fail "0008 is neither reserved nor written"
  grep -qE '^- Status: Accepted\s*$' "$f" || fail "$f is not Accepted"
  date=$(sed -nE 's/^- Date: ([0-9-]+).*/\1/p' "$f" | head -n 1)
  grep -qE "^\| \[0008\]\($(basename "$f")\) \|.*\| Accepted \| $date \|" docs/adr/README.md \
    || fail "index row for 0008 is neither reserved nor Accepted with $date"
}

# Step 7 — reset and skeleton
c19() {
  local p bad=""
  for p in setup.py requirements.txt __version__.py pytest.ini MANIFEST.in \
    .coveragerc .readthedocs.yml start.sh \
    test_import.py pyeconomics/ examples/ media/ markdown/; do
    tracked "$p" && bad="$bad $p"
  done
  # Phase 2 Step 7 adds a new site. Reject the legacy config, while requiring
  # the new static API generator and executed MyST notebooks (ADR-0007).
  if tracked docs/conf.py; then
    for p in myst_nb autoapi.extension pydata_sphinx_theme model_pages; do
      grep -qF "$p" docs/conf.py || bad="$bad docs/conf.py:$p"
    done
    grep -qF '../src/pyeconomics' docs/conf.py || bad="$bad docs/conf.py:src-layout"
  fi
  # Phase 4 Step 12 adds the hosted-service container (ADR-0012 decision 19).
  # Reject the 0.2.x JupyterLab Dockerfile and .dockerignore while requiring
  # the new non-root hosted-mode container markers.
  if tracked Dockerfile; then
    for p in PYECONOMICS_MODE=hosted pyeconomics.server --require-hashes; do
      grep -qF "$p" Dockerfile || bad="$bad Dockerfile:$p"
    done
    grep -qi 'jupyter' Dockerfile && bad="$bad Dockerfile:jupyter"
  fi
  if tracked .dockerignore; then
    for p in .roadmodel/ CLAUDE.local.md planning/user-context.md; do
      grep -qF "$p" .dockerignore || bad="$bad .dockerignore:$p"
    done
  fi
  [ -z "$(git ls-files 'docs/roadmap*.rst')" ] || bad="$bad docs/roadmap*.rst"
  [ -z "$bad" ] || fail "tracked:$bad"
}
c20() {
  grep -q 'importlib.metadata' src/pyeconomics/__init__.py || fail "__init__ does not read importlib.metadata"
  tracked src/pyeconomics/py.typed || fail "py.typed untracked"
}
c21() {
  "$PY" - << 'EOF'
import subprocess, sys, tomllib

d = tomllib.load(open("pyproject.toml", "rb"))
p = d["project"]
bad = []
if d["build-system"].get("build-backend") != "uv_build":
    bad.append("build-backend")
if p.get("requires-python") != ">=3.12":
    bad.append("requires-python")
if p.get("license") != "Apache-2.0":
    bad.append("license")
if "dependency-groups" not in d:
    bad.append("[dependency-groups]")
names = subprocess.run(["git", "ls-files", "src"], capture_output=True, text=True, check=True).stdout.split()
names += list(p.get("scripts", {})) + list(p.get("gui-scripts", {}))
names += list(p.get("urls", {}).values())
names += [a.get("email", "") for a in p.get("authors", []) + p.get("maintainers", [])]
names += list(p.get("optional-dependencies", {}))
names += [d.get("tool", {}).get("uv", {}).get("build-backend", {}).get("module-name", "")]
cfa = [n for n in names if "cfa" in n.lower()]
if cfa:
    bad.append(f"'cfa' in {cfa}")
if bad:
    print("; ".join(bad))
    sys.exit(1)
EOF
}
c22() {
  tracked uv.lock || fail "uv.lock untracked"
  tracked pylock.toml || fail "pylock.toml untracked"
}
c23() {
  grep -qE '^\*\s+text=auto\s+eol=lf' .gitattributes || fail ".gitattributes lacks * text=auto eol=lf"
  local crlf
  crlf=$(git ls-files --eol | awk '$1 ~ /^i\/(crlf|mixed)$/ { print $NF }')
  [ -z "$crlf" ] || fail "CRLF in the index: $crlf"
}
c24() {
  local line
  for line in .worktrees/ planning/user-context.md dev/ .env; do
    grep -qxF "$line" .gitignore || fail ".gitignore lacks $line"
  done
  grep -qxE '\*\.(json|csv)' .gitignore && fail "blanket *.json or *.csv ignore"
  return 0
}
c25() {
  grep -q 'Apache License' LICENSE && grep -q 'Version 2.0, January 2004' LICENSE || fail "LICENSE is not Apache-2.0"
  [ -f NOTICE ] || fail "NOTICE missing"
  grep -l '®' LICENSE NOTICE pyproject.toml CITATION.cff && fail "® present"
  return 0
}

# Step 8 — security gate
c26() {
  local id
  for id in gitleaks bandit semgrep pip-audit licences no-commit-to-branch; do
    grep -qE "^\s+- id: $id\s*$" .pre-commit-config.yaml || fail "hook $id missing"
  done
}
c27() {
  grep -rqE 'pickle' .semgrep/rules || fail "no pickle rule"
  grep -rqE '\beval\b' .semgrep/rules || fail "no eval rule"
  grep -rqE '\bexec\b' .semgrep/rules || fail "no exec rule"
  grep -rqE 'yaml\.load' .semgrep/rules || fail "no yaml.load rule"
  grep -rqiE 'credential|api_key' .semgrep/rules || fail "no credential-logging rule"
  [ -n "$(git ls-files .semgrep/tests/)" ] || fail ".semgrep/tests/ empty"
}
c28() {
  local f=.github/workflows/security.yml w
  grep -q 'trufflesecurity/trufflehog@' "$f" || fail "no trufflehog"
  grep -qE 'zizmor' "$f" || fail "no zizmor"
  grep -q 'actions/dependency-review-action@' "$f" || fail "no dependency-review"
  for w in security codeql scorecard; do
    [ -f ".github/workflows/$w.yml" ] || fail "$w.yml missing"
    harden_first ".github/workflows/$w.yml" || fail "$w.yml"
  done
}
c29() {
  local f=.github/pull_request_template.md
  grep -q '^## Sensitive-data checklist' "$f" || fail "no sensitive-data checklist"
  grep -q '^## Rollback plan' "$f" || fail "no rollback plan"
  grep -q '^## Licence check' "$f" || fail "no licence check"
}
c30() {
  grep -qE 'package-ecosystem:\s*"?uv"?' .github/dependabot.yml || fail "no uv ecosystem"
  grep -qE 'package-ecosystem:\s*"?github-actions"?' .github/dependabot.yml || fail "no github-actions ecosystem"
}

# Step 9 — quality toolchain
c31() {
  "$PY" -c 'import sys, tomllib; d = tomllib.load(open("pyproject.toml", "rb")); sys.exit(d["tool"]["ruff"]["lint"].get("select") != ["ALL"])' \
    || fail "ruff lint does not select ALL"
}
c32() {
  "$PY" -c 'import sys, tomllib; m = tomllib.load(open("pyproject.toml", "rb"))["tool"]["mypy"]; sys.exit(not (m.get("strict") is True and "pydantic.mypy" in m.get("plugins", [])))' \
    || fail "mypy is not strict with pydantic.mypy"
}
c33() {
  "$PY" - << 'EOF' || fail "pytest/coverage settings"
import sys, tomllib

t = tomllib.load(open("pyproject.toml", "rb"))["tool"]
addopts = t["pytest"]["ini_options"]["addopts"]
cov = t["coverage"]
ok = (
    "--disable-socket" in addopts
    and "--doctest-modules" in addopts
    and cov["run"].get("branch") is True
    and cov["report"].get("fail_under", 0) >= 95
)
sys.exit(not ok)
EOF
}
c34() {
  local id
  for id in ruff-format ruff-check mypy; do
    grep -qE "^\s+- id: $id\s*$" .pre-commit-config.yaml || fail "hook $id missing"
  done
}

# Step 10 — CI/CD
c35() {
  local f=.github/workflows/ci.yml os
  for os in ubuntu windows macos; do
    grep -qE "^\s+os:\s*\[.*$os-latest" "$f" || fail "matrix lacks $os"
  done
  grep -q 'uv sync --locked' "$f" || fail "no uv sync --locked"
  "$PY" - << 'EOF' || fail "classifiers and the matrix's Python versions differ"
import re, sys, tomllib

ci = open(".github/workflows/ci.yml", encoding="utf-8").read()
line = re.search(r"^\s+python-version:\s*\[(.*)\]", ci, re.MULTILINE)
matrix = set(re.findall(r'"(3\.\d+)"', line.group(1))) if line else set()
classifiers = tomllib.load(open("pyproject.toml", "rb"))["project"]["classifiers"]
declared = {m.group(1) for c in classifiers if (m := re.fullmatch(r"Programming Language :: Python :: (3\.\d+)", c))}
print("matrix", sorted(matrix), "classifiers", sorted(declared))
sys.exit(not (matrix == declared == {"3.12", "3.13", "3.14", "3.15"}))
EOF
}
c36() {
  local f=.github/workflows/release.yml jobs
  grep -q 'v0\.\*' "$f" || fail "does not refuse v0.* tags"
  grep -q 'merge-base --is-ancestor "$commit" origin/main' "$f" || fail "does not refuse tags off main"
  grep -q 'uv version --short' "$f" || fail "does not compare the tag with uv version"
  grep -qE '^\s+name:\s*testpypi\s*$' "$f" || fail "no testpypi environment"
  grep -qE '^\s+name:\s*pypi\s*$' "$f" || fail "no pypi environment"
  jobs=$(awk '/^  [A-Za-z0-9_-]+:[[:space:]]*$/ { job = $1 } /id-token:[[:space:]]*write/ { sub(":", "", job); print job }' "$f" | sort | tr '\n' ' ')
  [ "$jobs" = "publish-pypi publish-testpypi " ] || fail "id-token: write on: $jobs"
  grep -qE '^\s+workflow_call:' .github/workflows/release-smoke.yml || fail "release-smoke lacks workflow_call"
  grep -qE '^\s+workflow_dispatch:' .github/workflows/release-smoke.yml || fail "release-smoke lacks workflow_dispatch"
}
c37() {
  local f checkouts persist bad=""
  for f in $(git ls-files '.github/workflows/*.yml' '.github/workflows/*.yaml'); do
    grep -qE '^permissions:\s*\{\}\s*$' "$f" || bad="$bad $f:permissions"
    checkouts=$(grep -cE 'uses:\s*actions/checkout@' "$f")
    persist=$(grep -cE 'persist-credentials:\s*false' "$f")
    [ "$checkouts" = "$persist" ] || bad="$bad $f:persist-credentials"
    [ -z "$(unpinned_uses < "$f")" ] || bad="$bad $f:unpinned"
    grep -q 'pull_request_target' "$f" && bad="$bad $f:pull_request_target"
  done
  [ -z "$bad" ] || fail "$bad"
}
c38() {
  tracked .github/workflows/tests.yml && fail "tests.yml present"
  tracked .github/workflows/docs.yml && fail "docs.yml present"
  return 0
}
c39() {
  local job
  for job in pr-title dco test; do
    grep -qE "^  $job:\s*$" .github/workflows/ci.yml || fail "no $job job"
  done
  awk '/^  test:/ { t = 1; next } t && /^  [a-z]/ { t = 0 } t && /^    name: test\s*$/ { ok = 1 } t && /^    needs:/ { n = 1 } END { exit !(ok && n) }' \
    .github/workflows/ci.yml || fail "test is not the named aggregate"
}
c40() {
  git rev-parse -q --verify 'refs/tags/v1.0.0.dev1' > /dev/null || fail "tag missing"
  git merge-base --is-ancestor v1.0.0.dev1 origin/main || fail "not an ancestor of origin/main"
}

# Step 11 — governance
c41() {
  local p
  for p in README.md CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md \
    CITATION.cff NOTICE AGENTS.md CLAUDE.md funding.json .github/CODEOWNERS \
    .github/FUNDING.yml; do
    [ -f "$p" ] || fail "$p missing"
  done
  # github: returns with the Sponsors listing (issue #68, ROADMAP 8.1);
  # V11.4 then requires the listing to be live.
  grep -qE '^thanks_dev:' .github/FUNDING.yml || fail "FUNDING.yml lacks thanks_dev:"
}
c42() {
  local d=.github/ISSUE_TEMPLATE
  [ -f "$d/bug.yml" ] || fail "bug.yml missing"
  required_field "$d/model-request.yml" citation || fail "model-request.yml: citation not required"
  required_field "$d/data-source-request.yml" terms || fail "data-source-request.yml: terms not required"
  grep -qE '^blank_issues_enabled:\s*false' "$d/config.yml" || fail "blank issues not off"
}
required_field() { # required_field <form> <id>: the field's block sets required: true
  awk -v id="$2" '
    /^  - type:/ { inblk = 0 }
    $0 ~ "^    id: " id "[[:space:]]*$" { inblk = 1 }
    inblk && /^      required: true/ { found = 1 }
    END { exit !found }
  ' "$1"
}
c43() {
  local notice
  notice=$(grep -oE '"CFA® and Chartered Financial Analyst®[^"]*"' docs/roadmap/ROADMAP.md | head -n 1 | tr -d '"')
  [ -n "$notice" ] || fail "no CFA notice in ROADMAP §5"
  grep -qF "$notice" README.md || fail "README lacks the CFA notice verbatim"
  grep -qF 'legacy/0.2.x' README.md || fail "no 0.2.x pointer"
  grep -qE '^## Not to be confused with' README.md || fail "no disambiguation note"
  grep -qi 'not investment advice' README.md || fail "no 'not investment advice'"
  grep -qiE '^#+ .*wish ?list' README.md && fail "wishlist section present"
  return 0
}
c44() {
  # Phase 2 moved the version (post-merge addendum): CITATION.cff follows
  # pyproject.toml at every commit instead of naming 1.0.0.dev1.
  local cff project
  cff=$(sed -nE 's/^version:\s*"?([^" ]+)"?\s*$/\1/p' CITATION.cff | head -n 1)
  project=$("$PY" -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
  [ -n "$cff" ] && [ "$cff" = "$project" ] || fail "CITATION.cff says ${cff:-no version}, pyproject.toml $project"
  grep -qE '^license:\s*"?Apache-2\.0"?\s*$' CITATION.cff || fail "license is not Apache-2.0"
}
c45() {
  grep -qi 'step lifecycle' AGENTS.md || fail "AGENTS.md lacks the step lifecycle"
  grep -qi 'security gate' AGENTS.md || fail "AGENTS.md lacks the security gate"
  grep -q 'Triage rule' AGENTS.md || fail "AGENTS.md lacks the Triage rule"
  grep -qxF '@AGENTS.md' CLAUDE.md || fail "CLAUDE.md does not import AGENTS.md"
}

# Step 12 — self-checks
c46() {
  [ -f scripts/verify-phase01.sh ] || fail "missing"
  [ "$(git ls-files -s scripts/verify-phase01.sh | cut -d' ' -f1)" = 100755 ] || fail "index mode is not 100755"
}
c47() { [ -f "$QA" ] || fail "$QA missing"; }
c48() { [ -f "$ROADMAP" ] || fail "$ROADMAP missing"; }
c49() {
  grep -qE '^\s+phase:\s*\[.*"01".*\]' .github/workflows/phase-verify.yml || fail "matrix lacks \"01\""
}
c50() {
  # Patterns are assembled at run time so this file never matches itself.
  local dashes pem aws ghp pypi hits
  dashes=$(printf -- '-%.0s' 1 2 3 4 5)
  pem="${dashes}BEGIN ([A-Z0-9]+ )*PRIVATE KEY${dashes}"
  aws='(AKIA|ASIA)[0-9A-Z]{16}'
  ghp='(gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})'
  pypi='pypi-AgE[A-Za-z0-9_-]{50,}'
  hits=$(git grep -lIE "$pem|$aws|$ghp|$pypi" -- . 2> /dev/null || true)
  [ -z "$hits" ] || fail "credential pattern in: $hits"
}

run_static() {
  CURRENT_MODE=fast
  section "Static checks (Steps 1-11) and Step 12 self-checks"
  check 1 "Roadmaps tracked" c01
  check 2 "Planning kit tracked; user-context.md ignored" c02
  check 3 "Tag archive/dev-2024-10 peels to d4a692d" c03
  check 4 "Tag archive/legacy-dev-0.2.6 peels to 2b7e8a6" c04
  check 5 "origin/archive/0.2-dev-wip's parent is d4a692d" c05
  check 6 "legacy fred_api.py logs no api_key" c06
  check 7 "legacy credential-logging test and smoke script" c07
  check 8 "legacy release.yml: v0.2.* only, OIDC, two id-token jobs" c08
  check 9 "legacy workflows SHA-pinned; no docs.yml" c09
  check 10 "Tag v0.2.6.dev1 on legacy/0.2.x" c10
  check 11 "0.2.6 readiness: ten sections, no open FAIL, Decision: GO" c11
  check 12 "Tag v0.2.6 on legacy/0.2.x at version 0.2.6" c12
  check 13 "legacy CHANGELOG [0.2.6] dated; release record with GHSA" c13
  check 14 "Characterization fixtures match manifest.json" c14
  check 15 "Recorder's PEP 723 block pins pyeconomics==0.2.6" c15
  check 16 "No dev/ tracked; origin has only main, legacy, archive/ and open-PR heads" c16
  check 17 "docs/adr: README, template and nine ADRs" c17
  check 18 "Nine ADRs Accepted and indexed with dates; 0008 reserved or Accepted" c18
  check 19 "No 0.2.x path tracked on main" c19
  check 20 "src/pyeconomics reads importlib.metadata; py.typed" c20
  check 21 "pyproject: uv_build, >=3.12, Apache-2.0, groups; no 'cfa' names" c21
  check 22 "uv.lock and pylock.toml tracked" c22
  check 23 "eol=lf; no CRLF in the index" c23
  check 24 ".gitignore entries; no blanket *.json/*.csv" c24
  check 25 "Apache-2.0 LICENSE; NOTICE; no ®" c25
  check 26 "prek hooks: gitleaks, bandit, semgrep, pip-audit, licences, no-commit-to-branch" c26
  check 27 "semgrep rules (pickle, eval/exec, yaml.load, credentials) and tests" c27
  check 28 "security, codeql, scorecard workflows; harden-runner first" c28
  check 29 "PR template: sensitive data, rollback, licence" c29
  check 30 "Dependabot: uv and github-actions" c30
  check 31 "ruff lint selects ALL" c31
  check 32 "mypy strict with pydantic.mypy" c32
  check 33 "pytest sockets off + doctests; branch coverage >= 95" c33
  check 34 "prek hooks: ruff-format, ruff-check, mypy" c34
  check 35 "ci.yml: 3 OS x 3.12-3.15, uv sync --locked; classifiers match" c35
  check 36 "release.yml routing and OIDC; release-smoke triggers" c36
  check 37 "Workflows: permissions {}, persist-credentials false, SHA pins, no pull_request_target" c37
  check 38 "tests.yml and docs.yml absent on main" c38
  check 39 "ci.yml: pr-title, dco and aggregate test jobs" c39
  check 40 "Tag v1.0.0.dev1 on main" c40
  check 41 "Community and agent files; FUNDING.yml names thanks_dev:" c41
  check 42 "Issue forms: required citation, required terms URL, blank issues off" c42
  check 43 "README: CFA notice verbatim, 0.2.x pointer, disambiguation, no wishlist" c43
  check 44 "CITATION.cff: version equals pyproject.toml's, Apache-2.0" c44
  check 45 "AGENTS.md lifecycle, gate, Triage rule; CLAUDE.md imports it" c45
  check 46 "scripts/verify-phase01.sh is 100755 in the index" c46
  check 47 "docs/phase01-qa-findings.md exists" c47
  check 48 "docs/roadmap/phase01-roadmap.md exists" c48
  check 49 "phase-verify.yml matrix includes \"01\"" c49
  check 50 "No private key, AWS key id, GitHub or PyPI token tracked" c50

  section "V-checks (static)"
  vstatic V1.1 "Preserve + bootstrap (checks 1-5)" 1 5
  vstatic V2.1 "Legacy fix + pipeline (checks 6-10)" 6 10
  vstatic V3.1 "Readiness gate (check 11)" 11 11
  vstatic V4.1 "0.2.6 release (checks 12-13)" 12 13
  vstatic V5.1 "Characterize + archive (checks 14-16)" 14 16
  vstatic V6.1 "ADRs (checks 17-18)" 17 18
  vstatic V7.1 "Reset + skeleton (checks 19-25)" 19 25
  vstatic V8.1 "Security gate (checks 26-30)" 26 30
  vstatic V9.1 "Quality toolchain (checks 31-34)" 31 34
  vstatic V10.1 "CI/CD (checks 35-40)" 35 40
  vstatic V11.1 "Governance (checks 41-45)" 41 45
  vstatic V12.1 "verify-phase01.sh --fast exits 0" 1 50
  vstatic V12.2 "phase-verify.yml matrix includes 01 (check 49)" 49 49
  vstatic V12.3 "All static checks pass" 1 50
}

# --------------------------------------------------------------------------
# --python
# --------------------------------------------------------------------------

venv_python() { # venv_python <venv dir>
  if [ -x "$1/bin/python" ]; then echo "$1/bin/python"; else echo "$1/Scripts/python.exe"; fi
}

v7_2() {
  uv sync --locked || return 1
  rm -rf "$TMP/dist"
  uv build --out-dir "$TMP/dist" || return 1
  uvx twine==7.0.0 check --strict "$TMP"/dist/* || return 1
  local py expected found interpreter
  # Use the interpreter under test, including after new minors join CI.
  interpreter=$(uv python find --no-config) || return 1
  uv venv --no-config --python "$interpreter" -q "$TMP/clean" || return 1
  py=$(venv_python "$TMP/clean")
  # The wheel has runtime dependencies since Phase 2 (post-merge addendum),
  # so they come from PyPI; --no-config keeps a user-level index out.
  uv pip install --no-config --python "$py" "$TMP"/dist/*.whl || return 1
  expected=$(uv version --short)
  found=$(cd "$TMP" && "$py" -c 'import pyeconomics; print(pyeconomics.__version__)')
  echo "installed $found; pyproject.toml says $expected"
  [ "$found" = "$expected" ]
}
v7_3() { uv run --no-project python scripts/checks/dist_contents.py "$TMP/dist"; }
v9_2() {
  uv run --locked ruff format --check && uv run --locked ruff check && uv run --locked mypy
}
v9_3() { uv run --locked pytest --cov -q; }

run_python() {
  CURRENT_MODE=python
  section "--python"
  vcheck V7.2 "uv sync --locked, uv build, twine check --strict, clean-venv import" v7_2
  vcheck V7.3 "Wheel and sdist hold only allowlisted paths" v7_3
  vcheck V9.2 "ruff format --check, ruff check and mypy clean" v9_2
  vcheck V9.3 "pytest --cov: sockets off, doctests, coverage floor" v9_3
}

# --------------------------------------------------------------------------
# --security
# --------------------------------------------------------------------------

skip_on_main() {
  if [ "$(git rev-parse --abbrev-ref HEAD)" = main ]; then
    echo "no-commit-to-branch"
  fi
}
v8_2() {
  uv run --locked prek run semgrep-test --all-files || return 1
  SKIP="$(skip_on_main)" uv run --locked prek run --all-files
}
# gitleaks' hook scans staged changes only: stage the whole committed tree
# on an orphan branch in a scratch clone, as security.yml's gate-secrets does.
v12_4_secrets() {
  git clone -q --no-hardlinks "$ROOT" "$TMP/scan" || return 1
  (cd "$TMP/scan" && git checkout -q --orphan gate-secrets-scan \
    && uv run --project "$ROOT" --locked prek run gitleaks --all-files)
}
v2_3() {
  local f
  mkdir -p "$TMP/legacy/.github/workflows"
  for f in $(git ls-tree --name-only "$LEGACY" .github/workflows/); do
    legacy_show "$f" > "$TMP/legacy/$f" || return 1
  done
  uvx zizmor==1.30.1 --min-severity medium "$TMP/legacy/.github/workflows"
}

run_security() {
  CURRENT_MODE=security
  section "--security"
  vcheck V8.2 "semgrep-test hook and prek run --all-files clean" v8_2
  vcheck V2.3 "zizmor: nothing above Low on legacy/0.2.x's workflows" v2_3
  # V12.4 is the mode's verdict: the whole-tree secret scan passes and so
  # did every check above it.
  local before=${MODE_FAIL[security]:-0}
  if [ "$before" != 0 ]; then
    record FAIL V12.4 "--security: secrets, SAST, dependency audit, licences clean" "$before earlier failure(s)"
  else
    vcheck V12.4 "--security: whole-tree secret scan; SAST, dependency audit, licences clean" v12_4_secrets
  fi
}

# --------------------------------------------------------------------------
# --live (local only; reads settings, prints no secret)
# --------------------------------------------------------------------------

api() { gh api "repos/$REPO$1" "${@:2}"; }
http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@"; }
# Fetched pages are captured before they are matched: under pipefail, grep -q
# closing the pipe early would fail the curl that feeds it.
fetch() { curl -s --max-time 30 "$@"; }

protection_ok() { # protection_ok <branch>
  api "/branches/$1/protection" --jq '[
    .required_pull_request_reviews != null,
    .enforce_admins.enabled, .required_linear_history.enabled,
    (.allow_force_pushes.enabled | not), (.allow_deletions.enabled | not)
  ] | all' | grep -qx true
}
v1_2() {
  protection_ok main || fail "main protection"
  protection_ok legacy%2F0.2.x || fail "legacy/0.2.x protection"
}
v1_3() {
  api "" --jq '.allow_squash_merge and (.allow_merge_commit | not) and (.allow_rebase_merge | not)
    and .squash_merge_commit_title == "PR_TITLE" and .delete_branch_on_merge' | grep -qx true
}
ruleset_active() {
  api /rulesets --jq ".[] | select(.name == \"$1\") | .enforcement" | grep -qx active
}
v1_4() {
  ruleset_active archive-immutable-branches || fail "archive-immutable-branches"
  ruleset_active archive-immutable-tags || fail "archive-immutable-tags"
}
v2_2() {
  local head run
  head=$(git rev-parse "$LEGACY")
  run=$(gh run list -R "$REPO" --branch legacy/0.2.x --workflow tests.yml --limit 1 \
    --json databaseId,headSha,conclusion --jq '.[0] | "\(.databaseId) \(.headSha) \(.conclusion)"')
  set -- $run
  [ "${2:-}" = "$head" ] || fail "latest legacy CI run is not on legacy/0.2.x's HEAD"
  [ "${3:-}" = success ] || fail "latest legacy CI run: ${3:-none}"
  gh run view -R "$REPO" "$1" --json jobs --jq '[.jobs[] | select(.conclusion == "success") | .name] | join(",")' \
    | grep -q '3\.11' || fail "no green Python 3.11 job"
  gh run view -R "$REPO" "$1" --json jobs --jq '[.jobs[] | select(.conclusion == "success") | .name] | join(",")' \
    | grep -q '3\.12' || fail "no green Python 3.12 job"
}
# Both files of a release carry PEP 740 provenance on the index.
attested() { # attested <pypi|test.pypi> <version>
  local host=$1 version=$2 files f
  files=$(curl -s --max-time 30 "https://$host.org/pypi/pyeconomics/$version/json" \
    | "$PY" -c 'import json, sys; print("\n".join(u["filename"] for u in json.load(sys.stdin)["urls"]))' | tr -d '\r') \
    || fail "$host $version metadata"
  [ "$(printf '%s\n' "$files" | grep -c .)" = 2 ] || fail "$host $version does not have two files"
  for f in $files; do
    [ "$(http_code "https://$host.org/integrity/pyeconomics/$version/$f/provenance")" = 200 ] || fail "no provenance for $f"
  done
}
v2_4() { attested test.pypi 0.2.6.dev1; }
env_ok() { # env_ok <name>
  api "/environments/$1/deployment-branch-policies" --jq '[.branch_policies[] | "\(.type):\(.name)"] | join(",")' | grep -qx 'tag:v\*'
}
v2_5() {
  [ -z "$(gh secret list -R "$REPO" --json name --jq '.[].name' | grep -x PYPI_API_TOKEN)" ] || fail "PYPI_API_TOKEN exists"
  env_ok testpypi || fail "testpypi tag policy"
  env_ok pypi || fail "pypi tag policy"
  api /environments/pypi --jq '[.protection_rules[] | select(.type == "required_reviewers") | .reviewers[].reviewer.login] | join(",")' \
    | grep -qx nathanramoscfa || fail "pypi reviewer is not the maintainer"
  ruleset_active release-tags || fail "release-tags ruleset"
}
v4_2_attest() { attested pypi 0.2.6; }
v4_3() {
  api /security-advisories/GHSA-j6rp-vwwv-jrr8 --jq '.state == "published"
    and ([.cwes[].cwe_id] | index("CWE-532") != null)
    and ([.vulnerabilities[] | select(.patched_versions == "0.2.6" and .vulnerable_version_range == ">= 0.2.0, <= 0.2.5")] | length == 1)' \
    | grep -qx true
}
v4_4() {
  [[ "$(fetch https://pyeconomics.readthedocs.io/en/stable/)" == *"0.2.6 documentation"* ]] || fail "stable does not serve 0.2.6"
  curl -s --max-time 30 https://readthedocs.org/api/v3/projects/pyeconomics/versions/latest/ \
    | "$PY" -c 'import json, sys; d = json.load(sys.stdin); sys.exit(not (d["identifier"] == "legacy/0.2.x" and d["active"] and d["built"]))' \
    || fail "latest does not build from legacy/0.2.x"
}
v5_3() {
  gh api repos/nathanramoscfa/pyeconomics-research-archive --jq .visibility | grep -qx private || fail "archive not private"
  gh api repos/nathanramoscfa/pyeconomics-research-archive/contents/INDEX.md --jq .name > /dev/null || fail "no INDEX.md"
}
v5_4() {
  local open
  open=$(api "/pulls?state=open&per_page=100" --paginate --jq '.[] | "\(.number) \(.user.login) \(.head.ref)"')
  printf '%s\n' "$open"
  printf '%s\n' "$open" | awk '$1 < 46 && $1 != ""' | grep -q . && fail "a pre-Phase-1 pull request is open"
  printf '%s\n' "$open" | grep -qi snyk && fail "a Snyk pull request is open"
  return 0
}
v6_2() {
  local u
  for u in https://rdap.verisign.com/com/v1/domain/pyeconomics.com \
    https://rdap.publicinterestregistry.org/rdap/domain/pyeconomics.org \
    https://rdap.identitydigital.services/rdap/domain/pyeconomics.io \
    https://pubapi.registry.google/rdap/domain/pyeconomics.dev; do
    [ "$(http_code "$u")" = 200 ] || fail "not registered: $u"
  done
}
v6_3() {
  [ "$(gh repo view "$REPO" --json nameWithOwner --jq .nameWithOwner)" = pyeconomics-dev/pyeconomics ] || fail "owner"
  [ "$(fetch -o /dev/null -w '%{redirect_url}' https://github.com/nathanramoscfa/pyeconomics)" \
    = https://github.com/pyeconomics-dev/pyeconomics ] || fail "old URL does not redirect"
}
v8_4() {
  api "" --jq '.security_and_analysis | .secret_scanning.status == "enabled"
    and .secret_scanning_push_protection.status == "enabled"
    and .dependabot_security_updates.status == "enabled"' | grep -qx true || fail "secret scanning / push protection / security updates"
  api /vulnerability-alerts --silent || fail "Dependabot alerts off"
  api /private-vulnerability-reporting --jq .enabled | grep -qx true || fail "private vulnerability reporting off"
}
required_checks() {
  api /branches/main/protection/required_status_checks --jq '.contexts[]'
}
has_checks() { # has_checks <|-separated names>
  local have name missing=""
  have=$(required_checks)
  IFS='|' read -ra names <<< "$1"
  for name in "${names[@]}"; do
    printf '%s\n' "$have" | grep -qxF "$name" || missing="$missing [$name]"
  done
  [ -z "$missing" ] || fail "not required:$missing"
}
strict_checks() {
  api /branches/main/protection/required_status_checks --jq .strict | grep -qx true || fail "strict is off"
}
v8_5() {
  has_checks "gate-secrets|gate-sast|gate-deps|gate-licences|trufflehog|zizmor|dependency-review|codeql (python)|codeql (actions)"
  strict_checks
}
v10_2() {
  local head run
  head=$(git rev-parse origin/main)
  run=$(gh run list -R "$REPO" --workflow ci.yml --branch main --event push --limit 1 \
    --json databaseId,headSha,conclusion --jq '.[0] | "\(.databaseId) \(.headSha) \(.conclusion)"')
  set -- $run
  [ "${2:-}" = "$head" ] || fail "latest ci run on main is not origin/main's HEAD"
  [ "${3:-}" = success ] || fail "latest ci run on main: ${3:-none}"
  [ "$(gh run view -R "$REPO" "$1" --json jobs --jq '[.jobs[] | select((.name | startswith("tests (")) and .conclusion == "success")] | length')" = 12 ] \
    || fail "expected twelve green matrix cells"
  gh run view -R "$REPO" "$1" --json jobs --jq '.jobs[] | select(.name == "test") | .conclusion' | grep -qx success || fail "aggregate test not green"
}
v10_3_attest() { attested test.pypi 1.0.0.dev1; }
v10_4() {
  has_checks "lint|types|test|package|lockfile|pr-title|dco|gate-secrets|gate-sast|gate-deps|gate-licences|trufflehog|zizmor|dependency-review|codeql (python)|codeql (actions)|phase-verify-fast (01)|phase-verify-security (01)"
  strict_checks
}
v10_5() {
  api /actions/permissions --jq .sha_pinning_required | grep -qx true || fail "SHA pinning not required"
  api /actions/permissions/workflow --jq '.default_workflow_permissions == "read" and (.can_approve_pull_request_reviews | not)' \
    | grep -qx true || fail "workflow token not read-only"
  [ -z "$(gh secret list -R "$REPO" --json name --jq '.[].name')" ] || fail "repository secrets exist"
}
v11_2() {
  api /community/profile --jq '.files | (.readme != null) and (.contributing != null)
    and (.code_of_conduct_file != null) and (.pull_request_template != null)' | grep -qx true || fail "community profile"
  local owner=${REPO%/*} name=${REPO#*/}
  gh api graphql -f query="{ repository(owner: \"$owner\", name: \"$name\") { isSecurityPolicyEnabled contactLinks { url } } }" \
    --jq '.data.repository | .isSecurityPolicyEnabled and (.contactLinks | length >= 2)' | grep -qx true \
    || fail "security policy or config.yml contact links"
}
v11_3() {
  local have label
  have=$(gh label list -R "$REPO" --limit 200 --json name --jq '.[].name')
  for label in spec-rot upstream-gap bug model-error architecture process security; do
    printf '%s\n' "$have" | grep -qxF "$label" || fail "label $label missing"
  done
}
v11_4() {
  if grep -qE '^github:' .github/FUNDING.yml; then
    [ "$(http_code https://github.com/sponsors/pyeconomics-dev)" = 200 ] || fail "no Sponsors listing (302 means none; issue #68)"
  fi
  [ "$(http_code https://api.thanks.dev/v1/profile/gh/pyeconomics-dev)" = 200 ] || fail "thanks.dev profile"
  curl -s --max-time 30 https://fundingjson.org/schema/v1.1.0.json -o "$TMP/funding.schema.json" || fail "schema download"
  uvx --from check-jsonschema check-jsonschema --schemafile "$TMP/funding.schema.json" funding.json || fail "funding.json invalid"
  # funding.json lists exactly the channels FUNDING.yml names.
  "$PY" - << 'EOF' || fail "funding.json and FUNDING.yml name different channels"
import json, re, sys

yml = open(".github/FUNDING.yml", encoding="utf-8").read()
named = {k for k, pat in (("github", r"^github:"), ("thanks", r"^thanks_dev:")) if re.search(pat, yml, re.M)}
addresses = [c["address"] for c in json.load(open("funding.json", encoding="utf-8"))["funding"]["channels"]]
listed = {"github" for a in addresses if "github.com/sponsors/" in a} | {"thanks" for a in addresses if "thanks.dev" in a}
print("FUNDING.yml", sorted(named), "funding.json", sorted(listed))
sys.exit(named != listed)
EOF
}

run_live() {
  CURRENT_MODE=live
  section "--live"
  if ! gh auth status > /dev/null 2>&1; then
    record FAIL live "--live needs the maintainer's gh session (gh auth login)"
    return
  fi
  vcheck V1.2 "main and legacy/0.2.x: PR, admins, linear, no force-push or deletion" v1_2
  vcheck V1.3 "Squash-only merges titled by the PR; merged branches deleted" v1_3
  vcheck V1.4 "archive-immutable-branches and -tags rulesets active" v1_4
  vcheck V2.2 "Legacy CI green on legacy/0.2.x HEAD (3.11, 3.12)" v2_2
  vcheck V2.4 "TestPyPI attestations for both 0.2.6.dev1 files" v2_4
  vcheck V2.5 "No PYPI_API_TOKEN; environments tag v*; pypi reviewer; release-tags" v2_5
  vcheck V4.2 "PyPI attestations for both 0.2.6 files" v4_2_attest
  vcheck V4.3 "Advisory published: >= 0.2.0, <= 0.2.5; patched 0.2.6; CWE-532" v4_3
  vcheck V4.4 "Read the Docs stable serves 0.2.6; latest builds legacy/0.2.x" v4_4
  vcheck V5.3 "Research archive repository private with INDEX.md" v5_3
  vcheck V5.4 "No pre-Phase-1 or Snyk pull request open" v5_4
  vcheck V6.2 "RDAP: the four ADR-0009 domains are registered" v6_2
  vcheck V6.3 "Owner matches ADR-0009; the old URL redirects" v6_3
  vcheck V8.4 "Secret scanning, push protection, Dependabot, private reporting" v8_4
  vcheck V8.5 "Gate checks required on main, strict" v8_5
  vcheck V10.2 "Aggregate test green on main's HEAD across twelve cells" v10_2
  vcheck V10.3 "TestPyPI attestations for both 1.0.0.dev1 files" v10_3_attest
  vcheck V10.4 "main's required checks complete (incl. phase-verify), strict" v10_4
  vcheck V10.5 "SHA pinning required; token read-only; no repository secret" v10_5
  vcheck V11.2 "Community profile; security policy; issue-form contact links" v11_2
  vcheck V11.3 "The seven defect-class labels exist" v11_3
  vcheck V11.4 "thanks.dev API 200; funding.json valid, matching FUNDING.yml; Sponsors 200 when named" v11_4
}

# --------------------------------------------------------------------------
# --post
# --------------------------------------------------------------------------

v4_2_install() {
  uv venv --no-config -q --python 3.12 "$TMP/v026" || return 1
  local py
  py=$(venv_python "$TMP/v026")
  uv pip install --no-config -q --python "$py" --index-url https://pypi.org/simple/ pyeconomics==0.2.6 || return 1
  mkdir -p "$TMP/legacy-check/scripts"
  legacy_show scripts/check_credential_logging.py > "$TMP/legacy-check/scripts/check_credential_logging.py" || return 1
  (cd "$TMP" && "$py" -c 'import importlib.metadata as m; v = m.version("pyeconomics"); print(v); raise SystemExit(v != "0.2.6")') || return 1
  (cd "$TMP" && FRED_API_KEY= "$py" "$TMP/legacy-check/scripts/check_credential_logging.py")
}
v5_2() { uv run --no-config --script scripts/legacy/record_characterization.py --check; }
# Expected failures: the repository's gate, copied to a scratch repository
# outside the checkout, must flag gitleaks' own fake AWS key fixture and a
# pickle.loads call.
v8_3() {
  local d="$TMP/planted" gl_sha
  gl_sha=$(sed -n '/gitleaks\/gitleaks/,/rev:/p' .pre-commit-config.yaml | sed -nE 's/.*rev: ([0-9a-f]{40}).*/\1/p')
  mkdir -p "$d" && git -C "$d" init -q || return 1
  cp .pre-commit-config.yaml .gitleaks.toml pyproject.toml "$d/" && cp -r .semgrep "$d/" || return 1
  curl -sf --max-time 30 "https://raw.githubusercontent.com/gitleaks/gitleaks/$gl_sha/testdata/repos/nogit/main.go" -o "$d/main.go" || fail "fixture download"
  printf 'import pickle\n\n\ndef load(blob: bytes) -> object:\n    return pickle.loads(blob)\n' > "$d/planted.py"
  git -C "$d" add -A || return 1
  local hook
  for hook in gitleaks bandit semgrep; do
    if (cd "$d" && uv run --project "$ROOT" --locked prek run "$hook" --all-files > "$TMP/$hook.log" 2>&1); then
      fail "$hook did not flag the planted finding"
    fi
    echo "$hook flagged the planted finding"
  done
}
v10_3_install() {
  uv venv --no-config -q "$TMP/v100" || return 1
  local py found
  py=$(venv_python "$TMP/v100")
  uv pip install --no-config -q --no-deps --python "$py" --index-url https://test.pypi.org/simple/ pyeconomics==1.0.0.dev1 || return 1
  found=$(cd "$TMP" && "$py" -c 'import pyeconomics; print(pyeconomics.__version__)')
  echo "installed $found"
  [ "$found" = 1.0.0.dev1 ]
}
# The synthetic alarm: the run recorded in the QA findings failed.
v12_5() {
  local id
  id=$(sed -nE 's#.*Synthetic alarm run: https://github.com/[^/]+/[^/]+/actions/runs/([0-9]+).*#\1#p' "$QA" | head -n 1)
  [ -n "$id" ] || fail "no 'Synthetic alarm run:' URL in $QA"
  gh run view -R "$REPO" "$id" --json workflowName,conclusion --jq '.workflowName == "release-smoke" and .conclusion == "failure"' \
    | grep -qx true || fail "run $id is not a failed release-smoke run"
  grep -qE '^Notification received: ' "$QA" || fail "no 'Notification received:' line in $QA"
}
pr_checks() {
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [ "$branch" = main ] || ! gh pr view "$branch" -R "$REPO" > /dev/null 2>&1; then
    echo "no pull request for $branch: skipped"
    return 0
  fi
  gh pr checks "$branch" -R "$REPO"
}

run_post() {
  CURRENT_MODE=post
  section "--post"
  vcheck V4.2 "Clean-venv PyPI 0.2.6 install reports 0.2.6 and passes the credential check" v4_2_install
  vcheck V5.2 "Fixtures re-record byte-identically (record_characterization.py --check)" v5_2
  vcheck V8.3 "The gate flags a planted fake key and pickle.loads (expected failures)" v8_3
  vcheck V10.3 "Clean-venv TestPyPI 1.0.0.dev1 install reports its version" v10_3_install
  vcheck V12.5 "Synthetic release-smoke alarm failed and was notified" v12_5
  vcheck PR "gh pr checks for this branch" pr_checks
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

START=$SECONDS
run_static
case "$MODE" in
  --python) run_python ;;
  --security) run_security ;;
  --live) run_live ;;
  --all)
    run_python
    run_security
    ;;
  --post)
    run_python
    run_security
    run_live
    run_post
    ;;
esac

section "Summary ($MODE, $((SECONDS - START))s)"
printf '%-10s %6s %6s\n' mode passed failed
for m in fast python security live post; do
  if [ -n "${MODE_PASS[$m]:-}${MODE_FAIL[$m]:-}" ]; then
    printf '%-10s %6s %6s\n' "$m" "${MODE_PASS[$m]:-0}" "${MODE_FAIL[$m]:-0}"
  fi
done
if [ "$FAILED" = 0 ]; then
  echo "RESULT: PASS"
  exit 0
fi
echo "RESULT: FAIL"
exit 1
