"""Logging that never writes secrets.

Our code never logs tokens or keys on purpose. This is a safety net in case a
library error message or traceback ever contains one: every log line (and
traceback) passes through a filter that masks anything that looks like a
secret before it reaches the console / Render's log viewer.
"""

import logging
import re

# What we mask: bearer tokens, JWTs (Supabase access tokens, legacy keys),
# new-style Supabase keys and Google API keys.
_SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"),
    re.compile(r"sb_(?:secret|publishable)_[A-Za-z0-9_-]+"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
]


def redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "[REDACTED]", text)
    return text


def _redact_value(value):
    return redact(value) if isinstance(value, str) else value


class RedactSecretsFilter(logging.Filter):
    """Masks secrets in the message, its arguments and exception tracebacks.

    The message and its arguments are cleaned separately (not merged), because
    some formatters, like uvicorn's access log, need the original arguments.
    """

    _formatter = logging.Formatter()

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact_value(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_redact_value(arg) for arg in record.args)
        elif isinstance(record.args, dict):
            record.args = {key: _redact_value(arg) for key, arg in record.args.items()}
        if record.exc_info and not record.exc_text:
            record.exc_text = redact(self._formatter.formatException(record.exc_info))
        elif record.exc_text:
            record.exc_text = redact(record.exc_text)
        return True


def setup_logging() -> None:
    """Log INFO and above, and attach the redaction filter to every handler (ours and uvicorn's)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # The HTTP client logs every request URL at INFO, including search terms and
    # receipt ids. Not secret, but personal data doesn't belong in server logs.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    secret_filter = RedactSecretsFilter()
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access"):
        for handler in logging.getLogger(name).handlers:
            handler.addFilter(secret_filter)
