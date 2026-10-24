# src/pyeconomics/data/credentials/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Credentials: the secret type, the key chain and the ``.env`` parser.

ADR-0011 decision 12. A provider's key is read only through the chain
(:func:`resolve_key`), held only as a :class:`Secret` and revealed only in this
package and the transport. :func:`has_key` checks for a key without reading
it into a secret, and :func:`key_source` names the kind of source that holds
it. :func:`store_key` and :func:`delete_key` write the OS keyring for
``pyeconomics keys``. The "Keys and configuration" guide
(``docs/data/keys.md``) tells users where each key goes.

Examples
--------
>>> from pyeconomics.data.credentials import key_variable
>>> key_variable("census")
'CENSUS_API_KEY'

"""

from pyeconomics.data.credentials.chain import (
    KEYRING_SERVICE,
    KeySource,
    delete_key,
    has_key,
    key_source,
    key_variable,
    resolve_key,
    store_key,
    withheld,
)
from pyeconomics.data.credentials.dotenv import parse_dotenv
from pyeconomics.data.credentials.secret import (
    MAX_KEY_LENGTH,
    MIN_KEY_LENGTH,
    Secret,
    key_problem,
)

__all__ = [
    "KEYRING_SERVICE",
    "MAX_KEY_LENGTH",
    "MIN_KEY_LENGTH",
    "KeySource",
    "Secret",
    "delete_key",
    "has_key",
    "key_problem",
    "key_source",
    "key_variable",
    "parse_dotenv",
    "resolve_key",
    "store_key",
    "withheld",
]
