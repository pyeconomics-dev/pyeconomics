# .semgrep/tests/secret-reveal.py
# Test cases for .semgrep/rules/secret-reveal.yaml (semgrep --test).
# Deliberately unsafe code: excluded from the bandit and semgrep hooks.
import logging

from pyeconomics.data import Secret, resolve_key

logger = logging.getLogger(__name__)


def send(url, headers):
    return url, headers


def cases(provider, held: Secret, sources):
    # ruleid: secret-reveal
    value = held.reveal()
    # ruleid: secret-reveal
    send("https://api.example.org/v1", {"Authorization": resolve_key(provider).reveal()})
    # ruleid: secret-reveal
    parts = [source.reveal() for source in sources]
    # ruleid: secret-reveal
    logger.debug("checked %d characters", len(held.reveal()))

    # ok: secret-reveal
    send("https://api.example.org/v1", {"Accept": "application/json"})
    # ok: secret-reveal
    key = resolve_key(provider)
    # ok: secret-reveal
    logger.debug("resolved %r", key)
    # ok: secret-reveal
    revealed = held.provider
    # ok: secret-reveal
    reveal = sources.reveal
    return value, parts, revealed, reveal
