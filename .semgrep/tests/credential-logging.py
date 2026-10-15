# .semgrep/tests/credential-logging.py
# Test cases for .semgrep/rules/credential-logging.yaml (semgrep --test).
# Deliberately unsafe code: excluded from the bandit and semgrep hooks.
import logging
import os

from pyeconomics.data import resolve_key

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, api_key, settings):
        self._api_key = api_key
        self.settings = settings
        self._log = logger

    def cases(
        self, api_key, token, user_secret, password, passwd, credentials, fred, held
    ):
        # ruleid: credential-logging
        logger.debug("FRED key: %s", api_key)
        # ruleid: credential-logging
        logger.debug(f"Using key {api_key} for FRED")
        # ruleid: credential-logging
        logger.info(f"auth={token[:4]}...")
        # ruleid: credential-logging
        logging.warning("secret is %s", user_secret)
        # ruleid: credential-logging
        logger.error("login failed for %s", password)
        # ruleid: credential-logging
        logger.exception("bad passwd %r", passwd)
        # ruleid: credential-logging
        logger.critical("creds: %s", credentials)
        # ruleid: credential-logging
        logger.log(logging.INFO, "key=%s", self._api_key)
        # ruleid: credential-logging
        self._log.info("settings key %s", self.settings.FRED_API_KEY)
        # ruleid: credential-logging
        logger.info("payload", extra={"auth": token})
        # ruleid: credential-logging
        print(api_key)
        # ruleid: credential-logging
        print(f"token: {token}")
        # ruleid: credential-logging
        print("fred", os.environ["FRED_API_KEY"])
        # ruleid: credential-logging
        print(os.getenv("OPENAI_API_KEY"))
        # ruleid: credential-logging
        logger.debug("FRED %s", fred.reveal())
        # ruleid: credential-logging
        print(f"bls={resolve_key('bls').reveal()}")
        # ruleid: credential-logging
        logger.info("request", extra={"auth": held.reveal()})

        # ok: credential-logging
        logger.debug("FRED key loaded from the keyring")
        # ok: credential-logging
        logger.info("Using key ****%s", "redacted")
        # ok: credential-logging
        print("Enter your password:")
        # ok: credential-logging
        logger.info("series %s fetched", self.settings.series_id)
        # ok: credential-logging
        print(os.environ["HOME"])
        # ok: credential-logging
        logger.getChild("token-cache")
        # ok: credential-logging
        logger.info("loaded %d rows", len(self.settings.rows))
        # ok: credential-logging
        logger.debug("resolved %r", fred)
