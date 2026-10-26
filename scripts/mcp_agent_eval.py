# scripts/mcp_agent_eval.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Evaluate the MCP server's tool descriptions with a real agent (Phase 4 Step 9).

Each task of scripts/mcp/agent_tasks.py goes, as its prompt, to Claude Code
headless (``claude -p``) with ``pyeconomics mcp`` from this working tree as its
only MCP server and no built-in tool: the agent reaches pyeconomics through the
tools' names, descriptions and schemas alone. The script records each tool call
the agent makes (name, arguments, whether it failed and its problem), its final
answer and the tokens its first request held, and checks the task:

- the agent called the task's tools in order (a headline tool is also matched by
  ``run_model`` naming its model);
- its answer's last line, ``ANSWER: <value>``, holds the value the Python API
  computes now, from the same live data, within the task's tolerance, and
  names the attribution a series must be credited to; or, for a refusal, the
  tool answered that problem and the agent reported the data unavailable.

It runs on the maintainer's machine, never in CI: sockets are open and the
user's keys are read as the library reads them, except FRED's and ALFRED's,
which the server and the expected values withhold
(:func:`pyeconomics.data.credentials.withheld`), so the ``llm_use`` gate, not a
missing key, is what refuses FRED's data. The record holds tool names,
arguments and answers only; the script refuses to write one that holds a path of
this machine or the value of a key variable. Step 14 reruns it on the release
candidate.

    uv run python scripts/mcp_agent_eval.py --markdown docs/mcp-evaluations.md
    uv run python scripts/mcp_agent_eval.py --task bond_duration --task option_price
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess  # nosec B404 # runs the Claude Code CLI with fixed arguments
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from types import ModuleType

ROOT: Final = Path(__file__).resolve().parents[1]
SERVER: Final = "pyeconomics"
PREFIX: Final = f"mcp__{SERVER}__"
WITHHELD: Final = ("fred", "alfred")
TIMEOUT: Final = 600
#: The shortest environment value the record is checked for.
SHORTEST_SECRET: Final = 8
MAX_TURNS: Final = 16
#: What every prompt ends with, so the answer can be read without judgement.
ANSWER_RULE: Final = (
    "\n\nAnswer with the pyeconomics tools. End your reply with one line of the "
    "form `ANSWER: <value>`: the number as the tool returned it, as a plain "
    "decimal (0.05, not 5%), or `ANSWER: unavailable` if the tools cannot "
    "provide it."
)
_ANSWER: Final = re.compile(r"^\W*ANSWER:\s*(.+?)\W*$", re.MULTILINE)


def _load_tasks() -> ModuleType:
    path = ROOT / "scripts" / "mcp" / "agent_tasks.py"
    spec = importlib.util.spec_from_file_location("mcp_agent_tasks", path)
    if spec is None or spec.loader is None:  # pragma: no cover - the file is here
        msg = f"cannot load {path.name}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def _withheld() -> Iterator[None]:
    from pyeconomics.data.credentials import withheld  # noqa: PLC0415

    with contextlib.ExitStack() as stack:
        for provider in WITHHELD:
            stack.enter_context(withheld(provider))
        yield


def serve() -> int:
    """Run ``pyeconomics mcp`` over stdio, with FRED's and ALFRED's keys withheld."""
    from pyeconomics.cli import main  # noqa: PLC0415

    with _withheld():
        return main(["mcp"])


# --- one task -----------------------------------------------------------------


def _claude() -> str:
    found = shutil.which("claude")
    if found is None:
        msg = "the claude command (Claude Code) is not on PATH"
        raise SystemExit(msg)
    return found


def _command(claude: str, config: Path, model: str) -> list[str]:
    return [
        claude,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-turns",
        str(MAX_TURNS),
        "--mcp-config",
        str(config),
        "--strict-mcp-config",
        "--tools",
        "",
        "--allowedTools",
        f"mcp__{SERVER}",
        "--setting-sources",
        "project",
        "--disable-slash-commands",
        "--no-session-persistence",
    ]


def _events(output: str) -> list[dict[str, Any]]:
    events = []
    for line in output.splitlines():
        line = line.strip()  # noqa: PLW2901 - one JSON object per line
        if line.startswith("{"):
            with contextlib.suppress(json.JSONDecodeError):
                events.append(json.loads(line))
    return events


def _text_of(content: Any) -> str:  # noqa: ANN401 - a tool result's content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text", "")) for block in content if isinstance(block, dict)
        )
    return ""


def _problem(text: str) -> str | None:
    with contextlib.suppress(json.JSONDecodeError, AttributeError):
        first = json.loads(text.split("\n", 1)[0])
        return str(first["type"]).rsplit("/", 1)[-1]
    return None


def _tokens(usage: dict[str, Any]) -> int:
    names = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return sum(int(usage.get(name) or 0) for name in names)


def _tool_uses(message: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    calls = []
    for block in message.get("content") or ():
        if block.get("type") == "tool_use":
            call = {
                "tool": str(block.get("name", "")).removeprefix(PREFIX),
                "arguments": block.get("input") or {},
                "is_error": False,
                "problem": None,
            }
            calls.append((str(block.get("id")), call))
    return calls


def _failures(message: dict[str, Any]) -> list[tuple[str, str | None]]:
    return [
        (str(block.get("tool_use_id")), _problem(_text_of(block.get("content"))))
        for block in message.get("content") or ()
        if isinstance(block, dict)
        and block.get("type") == "tool_result"
        and block.get("is_error")
    ]


def _transcript(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Return the tool calls, answer, model and first-request tokens of a run."""
    by_id: dict[str, dict[str, Any]] = {}
    found: dict[str, Any] = {"model": "", "answer": "", "turns": 0}
    first_tokens: int | None = None
    for event in events:
        kind = event.get("type")
        message = event.get("message") or {}
        if kind == "system" and event.get("subtype") == "init":
            found["model"] = str(event.get("model", ""))
        elif kind == "assistant":
            if first_tokens is None and message.get("usage"):
                first_tokens = _tokens(message["usage"])
            by_id.update(_tool_uses(message))
        elif kind == "user":
            for use_id, problem in _failures(message):
                if use_id in by_id:
                    by_id[use_id].update(is_error=True, problem=problem)
        elif kind == "result":
            found["answer"] = str(event.get("result") or "")
            found["turns"] = int(event.get("num_turns") or 0)
    return {
        **found,
        "calls": list(by_id.values()),
        "first_request_tokens": first_tokens,
    }


def _in_order(wanted: Sequence[str], calls: Sequence[dict[str, Any]]) -> bool:
    from pyeconomics.mcp.tools import tool_name  # noqa: PLC0415

    names: list[set[str]] = []
    for call in calls:
        matched = {call["tool"]}
        model_id = call["arguments"].get("model_id")
        if call["tool"] == "run_model" and isinstance(model_id, str):
            with contextlib.suppress(Exception):
                matched.add(tool_name(model_id))
        names.append(matched)
    remaining = iter(names)
    return all(any(name in matched for matched in remaining) for name in wanted)


def _value(text: str) -> float | str | None:
    found = _ANSWER.findall(text)
    if not found:
        return None
    raw = found[-1].strip().strip("`*").strip()
    if raw.lower().startswith("unavailable"):
        return "unavailable"
    cleaned = raw.replace(",", "").replace("$", "").strip()
    percent = cleaned.endswith("%")
    match = re.match(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", cleaned.rstrip("%").strip())
    if match is None:
        return raw
    number = float(match.group(0))
    return number / 100 if percent else number


def _judge(task: Any, run: dict[str, Any], expected: Any) -> list[str]:  # noqa: ANN401
    """Return why the run failed its task; an empty list when it succeeded."""
    reasons = []
    if not _in_order(task.tools, run["calls"]):
        reasons.append(f"did not call {', '.join(task.tools)} in order")
    value = _value(run["answer"])
    if task.refusal is not None:
        if not any(call["problem"] == task.refusal for call in run["calls"]):
            reasons.append(f"no tool answered {task.refusal}")
        if value != "unavailable":
            reasons.append(f"answered {value!r}, not unavailable")
        return reasons
    if not isinstance(value, float):
        reasons.append(f"answered {value!r}, not a number")
    elif not math.isclose(value, float(expected), rel_tol=task.tolerance, abs_tol=0):
        reasons.append(f"answered {value!r}, expected {expected!r}")
    reasons.extend(
        f"did not name {text!r}" for text in task.mentions if text not in run["answer"]
    )
    return reasons


def run_task(task: Any, claude: str, model: str) -> dict[str, Any]:  # noqa: ANN401
    """Give one task to the agent and return its record."""
    with tempfile.TemporaryDirectory(prefix="pyeconomics-eval-") as scratch:
        config = Path(scratch) / "mcp.json"
        server = {
            "type": "stdio",
            "command": sys.executable,
            "args": [str(Path(__file__).resolve()), "serve"],
        }
        config.write_bytes(json.dumps({"mcpServers": {SERVER: server}}).encode())
        started = time.monotonic()
        completed = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments
            _command(claude, config, model),
            input=task.prompt + ANSWER_RULE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=scratch,
            timeout=TIMEOUT,
            check=False,
        )
        seconds = round(time.monotonic() - started, 1)
    run = _transcript(_events(completed.stdout))
    with _withheld():
        expected = None if task.expected is None else task.expected()
    reasons = _judge(task, run, expected)
    if completed.returncode != 0:
        reasons.append(f"claude exited with {completed.returncode}")
    return {
        "id": task.id,
        "prompt": task.prompt,
        "expected_tools": list(task.tools),
        "expected": task.refusal if task.refusal is not None else expected,
        "value": _value(run["answer"]),
        "seconds": seconds,
        "ok": not reasons,
        "reasons": reasons,
        **run,
    }


# --- the record ---------------------------------------------------------------


def _forbidden_texts() -> list[str]:
    """Return what the record must not hold: this machine's paths, key values."""
    texts = [str(ROOT), str(Path.home()), tempfile.gettempdir(), sys.executable]
    texts += [text.replace("\\", "/") for text in texts]
    texts += [
        value
        for name, value in os.environ.items()
        if len(value) >= SHORTEST_SECRET
        and (name.endswith("_API_KEY") or name.startswith("PYECONOMICS_"))
    ]
    return [text for text in texts if text]


def check_record(record: Any) -> None:  # noqa: ANN401 - JSON values
    """Raise if the record holds a path of this machine or a key's value."""
    text = json.dumps(record, ensure_ascii=False)
    lowered = text.lower()
    for forbidden in _forbidden_texts():
        if forbidden.lower() in lowered:
            msg = "the record holds a path of this machine or an environment value"
            raise SystemExit(msg)


def _tools_list_size() -> tuple[int, int]:
    from mcp import types  # noqa: PLC0415

    from pyeconomics.mcp.tools import build_tools  # noqa: PLC0415

    specs = build_tools()
    tools = [
        types.Tool(
            name=s.name,
            description=s.description,
            input_schema=s.input_schema,
            output_schema=s.output_schema,
        ).model_dump(by_alias=True, exclude_none=True, mode="json")
        for s in specs
    ]
    return len(json.dumps(tools, separators=(",", ":")).encode()), len(specs)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _call_text(call: dict[str, Any]) -> str:
    arguments = json.dumps(call["arguments"], sort_keys=True, separators=(", ", ": "))
    failed = f" → {call['problem'] or 'error'}" if call["is_error"] else ""
    return f"`{call['tool']}` {arguments}{failed}"


def markdown(record: dict[str, Any]) -> str:
    """Return docs/mcp-evaluations.md for a record."""
    runs = record["runs"]
    passed = sum(1 for run in runs if run["ok"])
    lines = [
        "# MCP agent evaluations",
        "",
        (
            "The MCP server's tool descriptions are tested by giving a real agent "
            "questions it can answer only through the tools "
            "(`scripts/mcp_agent_eval.py`, tasks in `scripts/mcp/agent_tasks.py`). "
            "The agent runs headless with `pyeconomics mcp` as its only MCP server "
            "and no other tool; FRED's and ALFRED's keys are withheld, so the "
            "`llm_use` gate is what refuses their data. A task succeeds when the "
            "agent calls its tools in order and answers the value the Python API "
            "computes from the same data, within the task's tolerance. CI runs the "
            "same tasks' scripted calls (`tests/mcp/test_mcp_agent_tasks.py`)."
        ),
        "",
        "## Latest run",
        "",
        f"- Date: {record['date']}",
        f"- Agent: {record['agent']}",
        f"- Model: `{record['model']}`",
        (
            f"- Server: pyeconomics {record['server_version']}, from the working "
            f"tree at commit `{record['commit']}`"
        ),
        f"- Result: {passed} of {len(runs)} tasks succeeded",
        (
            f"- Tool list: {record['tools']} tools, {record['tools_list_bytes']:,} "
            "bytes of names, descriptions and schemas; the agent's first request "
            f"held {record['baseline_tokens']:,} tokens without the server and "
            f"{record['first_request_tokens']:,} with it"
        ),
        "",
        "| Task | Result | Tool calls | Answer | Expected |",
        "|------|--------|------------|--------|----------|",
    ]
    for run in runs:
        tools = ", ".join(f"`{call['tool']}`" for call in run["calls"]) or "none"
        lines.append(
            f"| `{run['id']}` | {'succeeded' if run['ok'] else 'failed'} | {tools} | "
            f"{_cell(str(run['value']))} | {_cell(str(run['expected']))} |"
        )
    lines += ["", "## Each task", ""]
    for run in runs:
        lines += [f"### {run['id']}", "", f"> {run['prompt']}", ""]
        lines += [
            f"{index}. {_call_text(call)}" for index, call in enumerate(run["calls"], 1)
        ]
        if run["reasons"]:
            lines += ["", "Failed: " + "; ".join(run["reasons"]) + "."]
        lines += [
            "",
            "The agent's answer:",
            "",
            "```text",
            run["answer"].strip(),
            "```",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _baseline_tokens(claude: str, model: str) -> int:
    """Return the first request's tokens with no MCP server, for comparison."""
    with tempfile.TemporaryDirectory(prefix="pyeconomics-eval-") as scratch:
        config = Path(scratch) / "mcp.json"
        config.write_bytes(b'{"mcpServers": {}}')
        completed = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments
            _command(claude, config, model),
            input="Reply with the word OK.",
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=scratch,
            timeout=TIMEOUT,
            check=False,
        )
    return _transcript(_events(completed.stdout))["first_request_tokens"] or 0


def _commit() -> str:
    git = shutil.which("git")
    if git is None:
        return "unknown"
    completed = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments
        [git, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    return completed.stdout.strip() or "unknown"


def evaluate(args: argparse.Namespace) -> int:
    """Run the chosen tasks and write the record; 0 when every task succeeded."""
    import pyeconomics  # noqa: PLC0415

    tasks_module = _load_tasks()
    chosen = [t for t in tasks_module.TASKS if not args.task or t.id in args.task]
    claude = _claude()
    version = subprocess.run(  # noqa: S603 # nosec B603 - fixed arguments
        [claude, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    runs = []
    for task in chosen:
        run = run_task(task, claude, args.model)
        runs.append(run)
        verdict = "ok" if run["ok"] else "FAILED: " + "; ".join(run["reasons"])
        tools = ", ".join(call["tool"] for call in run["calls"])
        sys.stdout.write(f"{task.id}: {verdict} [{tools}] ({run['seconds']} s)\n")
        sys.stdout.flush()
    size, count = _tools_list_size()
    first = [run["first_request_tokens"] for run in runs if run["first_request_tokens"]]
    agent = f"Claude Code {(version or 'unknown').split()[0]}, headless (claude -p)"
    record = {
        "date": dt.datetime.now(dt.UTC).date().isoformat(),
        "agent": agent,
        "model": next((run["model"] for run in runs if run["model"]), args.model),
        "server_version": pyeconomics.__version__,
        "commit": _commit(),
        "tools": count,
        "tools_list_bytes": size,
        "baseline_tokens": _baseline_tokens(claude, args.model),
        "first_request_tokens": min(first) if first else 0,
        "runs": runs,
    }
    check_record(record)
    if args.json:
        Path(args.json).write_bytes(
            (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        )
    if args.markdown:
        Path(args.markdown).write_bytes(markdown(record).encode("utf-8"))
    return 0 if all(run["ok"] for run in runs) else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the command line and run the evaluation, or serve (``serve``)."""
    given = list(sys.argv[1:] if argv is None else argv)
    if given[:1] == ["serve"]:
        return serve()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", default="sonnet", help="the agent's model")
    parser.add_argument("--task", action="append", help="run only this task id")
    parser.add_argument("--json", help="write the record as JSON here")
    parser.add_argument("--markdown", help="write the evaluations page here")
    return evaluate(parser.parse_args(given))


if __name__ == "__main__":
    sys.exit(main())
