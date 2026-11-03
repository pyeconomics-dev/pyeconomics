# Run the web app on your own machine

The local app is the site at pyeconomics.dev, served by your own machine: every
model page, every calculator and the data explorer. Use it for what the public
site cannot serve you: sources whose licence keeps them on your machine, and the
whole data catalog, on your own keys.

## Start it

```text
pip install "pyeconomics[app]"
pyeconomics serve
```

While 1.0 is in pre-release, add `--pre` to the install command. Then open
<http://127.0.0.1:8000>.

The `app` extra brings the REST API's requirements and the `pyeconomics-app`
wheel, which holds the built site at the same version. Without it, `serve` logs
one line saying how to install it and serves the API alone. The API keeps its
routes beside the site: `/v1`, `/mcp`, `/docs` and the rest
({doc}`/tutorials/rest-api`).

## Give it your keys

The server reads keys as the library does, so store them once, with a hidden
prompt, before you start it. No page asks for a key, and no route accepts one.

```text
pip install "pyeconomics[keyring]"
pyeconomics keys set fred
```

`keys list` shows where each key would be read from, and never its value
({doc}`/data/keys`). Until you store one, a key's source is `none`:

```console
$ pyeconomics keys list
Provider    Variable            Required  Source
fred        FRED_API_KEY        yes       none
```

## What changes from the public site

The pages ask the server which mode it runs in, and offer more in local mode:

```console
$ curl http://127.0.0.1:8000/version
..."mode":"local"...
```

| | pyeconomics.dev | Your machine |
|---|---|---|
| **Live data in a calculator** | Sources whose licence allows a hosted service | Every source your installation reaches, `library-only` ones included, on your keys |
| **The data explorer** | The concepts the daily snapshot holds | The whole catalog |
| **Time limit on a run** | By the model's cost class | None |
| **Analytics and error tracking** | Yes | None |
| **Search engines** | Indexed | Never indexed |

A `library-only` source's terms keep its data with you, under your own key. Keep
its attribution and notice with anything you copy out of the app, and do not pass
the data on where its terms forbid that. `pyeconomics data sources` lists each
source's class, and {doc}`/reference/sources` its terms.

## Reach it from another machine

`pyeconomics serve` listens on `127.0.0.1`, and refuses any other address. To
serve another machine, pass `--allow-remote`:

```text
pyeconomics serve --host 0.0.0.0 --allow-remote
```

```{warning}
`--allow-remote` exposes every source your machine can access, with your keys, to
whoever can reach it, with no login. The server logs a warning saying so. Use it
only on a network you trust, and never on the public internet.
```

The site's security policy upgrades insecure requests. Browsers exempt loopback
addresses from that, but a browser on another machine needs the site behind HTTPS.
