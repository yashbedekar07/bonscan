"""Tests for the scan limit, secret redaction in logs, and hiding the user's token."""

import logging

import pytest
from fastapi import HTTPException
from postgrest.exceptions import APIError

from app.auth import CurrentUser
from app.config import ConfigError
from app.logging_setup import RedactSecretsFilter, redact
from app.receipts import _register_scan

# ---------- Daily scan limit ----------


class FakeRpc:
    """Stands in for db.rpc(...).execute() and records the call."""

    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return self

    def execute(self):
        if self.error:
            raise self.error
        return type("Response", (), {"data": self.result})()


def test_scan_allowed_under_limit():
    db = FakeRpc(result=[{"allowed": True, "used": 3}])
    _register_scan(db)  # no exception
    assert db.calls[0][0] == "register_scan"
    assert db.calls[0][1]["daily_limit"] >= 1


def test_scan_refused_with_friendly_429_when_limit_reached():
    db = FakeRpc(result=[{"allowed": False, "used": 15}])
    with pytest.raises(HTTPException) as caught:
        _register_scan(db)
    assert caught.value.status_code == 429
    assert "Daily scan limit reached" in caught.value.detail
    assert "Try again tomorrow" in caught.value.detail


def test_missing_database_function_gives_setup_hint():
    error = APIError({"code": "PGRST202", "message": "Could not find the function", "details": None, "hint": None})
    with pytest.raises(ConfigError, match="schema.sql"):
        _register_scan(FakeRpc(error=error))


# ---------- No secrets in logs ----------

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlLXNpZ25hdHVyZQ"


@pytest.mark.parametrize(
    "secret",
    [JWT, "sb_secret_abc123XYZ", "sb_publishable_abc123XYZ", "AIzaSyA1234567890abcdefghijklmnop"],
)
def test_redact_masks_secrets(secret):
    text = redact(f"request failed with key {secret} at step 2")
    assert secret not in text
    assert "[REDACTED]" in text


def test_redact_masks_bearer_tokens_but_keeps_the_word():
    assert redact("Authorization: Bearer abc.def.ghi") == "Authorization: Bearer [REDACTED]"


def test_redact_leaves_normal_text_alone():
    assert redact("Saved receipt 3f2a for REWE, 12,49 €") == "Saved receipt 3f2a for REWE, 12,49 €"


def test_log_filter_cleans_messages_args_and_tracebacks():
    try:
        raise RuntimeError(f"upstream said: token {JWT}")
    except RuntimeError:
        import sys

        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "Call failed for %s", (JWT,), sys.exc_info())
    RedactSecretsFilter().filter(record)
    assert JWT not in record.getMessage()
    assert JWT not in record.exc_text
    assert "[REDACTED]" in record.exc_text


def test_log_filter_keeps_argument_structure_for_uvicorn_access_log():
    # uvicorn's access formatter unpacks record.args, so they must stay a tuple.
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s"', ("1.2.3.4", "GET", f"/x?t={JWT}"), None)
    RedactSecretsFilter().filter(record)
    assert isinstance(record.args, tuple) and len(record.args) == 3
    assert JWT not in record.getMessage()


# ---------- The user's token never leaks through the user object ----------


def test_current_user_hides_access_token():
    user = CurrentUser(id="u1", email="a@example.com", access_token=JWT)
    assert JWT not in repr(user)
    assert "access_token" not in user.model_dump()
    assert user.access_token == JWT  # still usable by the code that needs it
