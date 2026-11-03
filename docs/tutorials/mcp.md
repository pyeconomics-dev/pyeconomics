# An AI assistant, through MCP

The [Model Context Protocol](https://modelcontextprotocol.io) lets an AI
assistant call tools you give it. `pyeconomics mcp` gives it every model and
every data source, so its numbers come from a cited formula and not from memory.
This lesson takes about fifteen minutes, and you need a client that speaks MCP,
such as Claude Code or Claude Desktop.

## Connect a client

You do not run the server yourself: your client starts it, and talks to it over
standard input and output. [uv](https://docs.astral.sh/uv/)'s `uvx` installs it
into a cached environment of its own, so it needs no setup. In Claude Code:

```text
claude mcp add pyeconomics -- uvx --prerelease allow --from "pyeconomics[mcp]" pyeconomics mcp
```

A client that reads a JSON configuration file, such as Claude Desktop's
`claude_desktop_config.json`, takes the same command:

```json
{
  "mcpServers": {
    "pyeconomics": {
      "command": "uvx",
      "args": ["--prerelease", "allow", "--from", "pyeconomics[mcp]", "pyeconomics", "mcp"]
    }
  }
}
```

`--prerelease allow` is needed while 1.0 is in pre-release. Restart the client
and ask it something a model answers: *"What is the present value of 100 in ten
years at 5%?"*

## See what your assistant sees

The next example plays the client's part, in memory, with the MCP SDK's own
`Client`. It lists the tools your assistant is offered:

```python
>>> import anyio
>>> from mcp import Client
>>> from pyeconomics.mcp import build_server
>>> async def tools():
...     async with Client(build_server()) as client:
...         return [tool.name for tool in (await client.list_tools()).tools]
>>> names = anyio.run(tools)
>>> [name for name in names if name in {"search_models", "describe_model", "run_model"}]
['describe_model', 'run_model', 'search_models']
>>> "foundations_time_value" in names
True
```

Five tools reach every model and source: `search_models`, `describe_model`,
`run_model`, `get_series` and `list_sources`. Sixteen widely used models also
have a tool of their own, such as `foundations_time_value`, so an assistant can
call them without reading a description first.

Now call one, as your assistant would:

```python
>>> import json
>>> async def present_value():
...     async with Client(build_server()) as client:
...         return await client.call_tool(
...             "foundations_time_value",
...             {
...                 "calculation": "present_value",
...                 "rate": 0.05,
...                 "periods": 10,
...                 "future_value": 100,
...             },
...         )
>>> answer = anyio.run(present_value)
>>> json.loads(answer.content[0].text)["outputs"]["present_value"]
61.391325354075946
```

The first block of the answer is the same canonical JSON as every other surface,
so your assistant holds the result, its inputs and its manifest. It also gets a
one-line summary to quote:

```python
>>> answer.content[1].text.startswith("Time value of money")
True
```

## What reaches your assistant

Every source declares whether its terms let its data reach a language model. The
server passes your assistant only what is allowed. FRED's terms forbid it, so
FRED data never reaches an assistant by this route: the resolver takes the next
source of the same data, or the tool answers `llm-use-forbidden`. A source whose
terms are unclear is passed over unless you opt in, in your own settings; no
tool argument can do that. `list_sources` shows each source's class.

Your keys stay out of it too. The server reads them as the library does, and no
tool takes, stores or returns one. A client starts the server with the
environment it chooses, so a key in your shell may not reach it; the keyring
always does ({doc}`data-and-keys`).

## The hosted endpoint

The public service will serve the same tools over Streamable HTTP, at
`https://pyeconomics.dev/mcp`, when 1.0.0 is released. It is not open yet. A
client will connect with no install:

```text
claude mcp add --transport http pyeconomics https://pyeconomics.dev/mcp
```

Hosted mode reads only sources whose licence allows a hosted service, and holds
each run to its model's time budget. For everything else, use the local server
above.

## Next

You have finished the track. {doc}`/mcp` is the full reference, and the
{doc}`how-to guides </how-to/index>` give recipes for particular jobs.
