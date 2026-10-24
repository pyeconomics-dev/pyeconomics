# Keys and configuration

A few data sources ask for a free API key. pyeconomics reads a key only
through its key chain, holds it in memory as a `Secret`, and never logs,
prints, caches or exports it. This page covers where to get each key, where
to put it, the settings file, what stays private, and what to do if a key
leaks.

The data providers that use these keys arrive during the 1.0 alpha. The key
chain, the settings and the redaction they rely on are available now in
`pyeconomics.data`.

## Where to register

| Source | Environment variable | Where to get a key |
|--------|----------------------|--------------------|
| FRED and ALFRED (St. Louis Fed) | `FRED_API_KEY` | Sign in at [fredaccount.stlouisfed.org](https://fredaccount.stlouisfed.org/apikeys) and request a key ([how](https://fred.stlouisfed.org/docs/api/api_key.html)) |
| BLS (Bureau of Labor Statistics) | `BLS_API_KEY` | [BLS API registration](https://data.bls.gov/registrationEngine/); optional: without it pyeconomics reads BLS's keyless API v1 at its lower limits |
| BEA (Bureau of Economic Analysis) | `BEA_API_KEY` | [BEA API sign-up](https://apps.bea.gov/API/signup/); BEA calls the key a UserID |
| US Census Bureau | `CENSUS_API_KEY` | [Census API key request](https://api.census.gov/data/key_signup.html); required on every query since May 2026 |
| OpenFIGI | `OPENFIGI_API_KEY` | Optional, for higher rate limits: sign up as the [OpenFIGI documentation](https://www.openfigi.com/api/documentation) describes |

Every variable is the provider's id in capitals followed by `_API_KEY`:

```python
>>> from pyeconomics.data import key_variable
>>> key_variable("fred")
'FRED_API_KEY'
```

## How pyeconomics finds a key

For each provider, pyeconomics takes the first key it finds, in this order:

1. **An argument** you pass to a function that fetches data.
2. **The environment variable**, such as `FRED_API_KEY`.
3. **The `.env` file** in your pyeconomics configuration directory. A
   variable set in the real environment always wins over the file, and the
   file is never loaded into the environment.
4. **The OS keyring**: service `pyeconomics`, user name the provider id,
   when the `keyring` extra is installed.

An empty value counts as unset. If no source has a key, the error names the
provider, its variable, the keyring command and this page, never a value.

To check for a key without reading it, use `has_key`. It returns only
`True` or `False`:

```python
>>> from pyeconomics.data import has_key
>>> has_key("fred")  # True once a key is set
False
```

## Setting a key

Replace `<key>` below with the key the source issued you.

### The OS keyring (recommended)

The keyring keeps the key out of files and shell history. Install the extra,
then store each key. `pyeconomics keys set` asks for the key without showing
it, checks it and stores it (the [command line](../cli.md) guide has the
details, including `--stdin` for a key piped from a secrets manager):

```console
pip install "pyeconomics[keyring]"
pyeconomics keys set fred
```

`keyring set pyeconomics fred`, the keyring package's own command, stores the
same entry. `pyeconomics keys list` shows where each key would be read from,
never its value.

The user name is the provider id: `fred`, `bls`, `bea`, `census` or
`openfigi`. macOS uses the Keychain, Windows the Credential Manager, and
Linux the Secret Service (GNOME Keyring or KWallet). If the keyring cannot
be read, pyeconomics skips it with a `keyring_backend_failed` warning that
names the backend.

### An environment variable

On macOS and Linux:

```console
export FRED_API_KEY='<key>'
```

In Windows PowerShell:

```console
$env:FRED_API_KEY = '<key>'
```

### The `.env` file

Put one `NAME=VALUE` per line in the `.env` file in your configuration
directory:

```text
# pyeconomics keys
FRED_API_KEY=<key>
BLS_API_KEY='<key>'
```

| System | File |
|--------|------|
| Linux | `~/.config/pyeconomics/.env` (or `$XDG_CONFIG_HOME/pyeconomics/.env`) |
| macOS | `~/Library/Application Support/pyeconomics/.env` |
| Windows | `%LOCALAPPDATA%\pyeconomics\.env` |

`PYECONOMICS_CONFIG_DIR` moves the directory. pyeconomics never reads a
`.env` file anywhere else, including your project or working directory.

The parser is strict, and nothing in the file is ever executed or expanded:

- A value is taken literally. `$HOME`, `${HOME}` and backslashes stay as
  written.
- Quote a value with single or double quotes on one line. A bare value has
  no spaces, quotes or `#`.
- Lines starting with `#` are comments, as is a `#` after a space at the end
  of a line.
- `export` and multi-line values are errors, as is a name set twice. An
  error names the line number, never the line.

On macOS and Linux, make the file readable by you alone:

```console
chmod 600 ~/.config/pyeconomics/.env
```

Otherwise pyeconomics warns with `credentials_file_permissions`.

## Settings: `pyeconomics.toml`

Settings come from three layers. Each one overrides the one before it, key
by key:

1. `pyeconomics.toml` in your configuration directory (the `.env` table
   above shows where);
2. `pyeconomics.toml` in the working directory;
3. `PYECONOMICS_*` environment variables.

```toml
mode = "library"
offline = false
sec_contact = "Ada Analyst ada.analyst@example.org"

[ttl]
bls = 86400
```

| Setting | Variable | Meaning |
|---------|----------|---------|
| `mode` | `PYECONOMICS_MODE` | `library` (the default), or `hosted`, which serves only sources whose licence allows a hosted service |
| `offline` | `PYECONOMICS_OFFLINE` | Serve only cached data and send no request: `1`, `true`, `yes` or `on` |
| `cache_dir` | `PYECONOMICS_CACHE_DIR` | Where the cache lives, as an absolute path |
| `sec_contact` | `PYECONOMICS_SEC_CONTACT` | The name and email address SEC EDGAR requires in each request |
| `[ttl]` *provider* | `PYECONOMICS_TTL_<PROVIDER>` | How long the cache serves a provider's open data, in seconds; `0` turns that provider's cache off ([the cache](cache.md)) |
| | `PYECONOMICS_CONFIG_DIR` | Where `pyeconomics.toml` and `.env` are read from |

The cache directory defaults to `~/.cache/pyeconomics` on Linux,
`~/Library/Caches/pyeconomics` on macOS and
`%LOCALAPPDATA%\pyeconomics\Cache` on Windows. The files and variables are
read once per process. `configure` overrides settings from Python for the
rest of the process, in every thread, so a server configures once at start
and never per request:

```python
>>> from pyeconomics.data import configure, settings
>>> configure(offline=True).offline
True
>>> settings().mode
'library'
```

`pyeconomics.toml` holds settings only. Any key whose name suggests a
credential (`key`, `token`, `secret`, `password`, `credential` or `auth`) is
refused with a `ConfigError` that names the key, never its value. Keys go in
the keyring, an environment variable or the `.env` file.

## What is never logged or stored

- A key is a `Secret` from the moment it is read. It prints as
  `<Secret fred: redacted>`, and pickling and JSON refuse it.
- Once read, a key is scrubbed from every log record of every logger, URL
  encoded or not. That includes the request lines urllib3 writes at DEBUG,
  which carry FRED's key in the query string. It is also scrubbed from
  pyeconomics' own warnings and error messages.
- The query parameters that carry keys (`api_key`, `registrationkey`,
  `UserID`, `key`, `token`) are removed from any URL before a message or a
  log line holds it, and the `Authorization`, `Cookie` and key headers are
  dropped.
- Errors name a provider, a variable, a setting or a line number. They never
  name a value or a file path, and a failed request is reported without the
  original exception attached.
- Manifests, results and their exports (JSON, pandas, Parquet) carry no key,
  no SEC contact, no path and no environment value.
- The SEC contact is sent only in EDGAR's User-Agent header. It prints as
  asterisks and is scrubbed like a key everywhere else.
- FRED and ALFRED data are never written to disk, as FRED's terms require, and
  neither is any source or series whose terms forbid storage. What the cache does
  store is canonical JSON of data, never a key, and the file is readable by your
  user only ([the cache](cache.md)).

## If a key leaks

Treat a key that reached a log, a notebook, a commit, a chat or a shared
file as public:

1. **Replace it at the source.** Request a new key, and delete the old one
   where the source allows it: FRED's
   [API keys page](https://fredaccount.stlouisfed.org/apikeys), or a new
   registration with BLS, BEA, the Census Bureau or OpenFIGI.
2. **Update where you keep it.** Run `pyeconomics keys set <provider>`
   again, or edit the environment variable or the `.env` file. Run
   `pyeconomics keys delete <provider>` to remove a stored key.
3. **Remove the copies.** Check shell history, notebook outputs, CI logs and
   commit history. A key pushed to a repository stays in its history until
   the history is rewritten, so replacing the key is what matters.
4. **If pyeconomics leaked it**, through a log line, an error or an export,
   report it privately through the
   [security policy](https://github.com/pyeconomics-dev/pyeconomics/security/policy).
   The maintainers ship a patched release and publish an advisory.
