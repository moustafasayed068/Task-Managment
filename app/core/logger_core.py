"""
logger_core.py
~~~~~~~~~~~~~~
Loguru configuration — colourful real-time terminal output + file sinks.

Design:
  • Console sink on sys.stderr  — synchronous, never buffered.
  • Intercept stdlib logging (uvicorn, sqlalchemy, etc.) so that ALL
    output flows through Loguru with the same colourful format.
  • Two file sinks: app.log (INFO+) and errors.log (WARNING+).
  • Structured logging via logger.bind() — all key fields are named,
    never interpolated into free-form strings.
  • CRITICAL level has a custom colour (bold white on red).
  • diagnose=True is disabled in production to prevent data leakage.

Security:
  • Never log passwords, tokens, secrets, or PII.
  • SENSITIVE_FIELDS is a registry of known-bad key names — callers
    should strip these before passing kwargs to logger.bind().
"""

import logging
import os
import sys
from pathlib import Path

from loguru import logger

# ── Environment ───────────────────────────────────────────────────────────────
# Set APP_ENV=production (or PRODUCTION=1) in your deployment environment.
_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = _ENV == "production"

# ── Sensitive field registry ──────────────────────────────────────────────────
# Any key in this set must never appear in a log record's extra fields.
# strip_sensitive() is provided for callers who build dicts dynamically.
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "password", "passwd", "secret", "token", "api_key", "apikey",
        "authorization", "auth", "credit_card", "card_number", "cvv",
        "ssn", "national_id", "dob", "date_of_birth", "email", "phone",
        "ip_address",           # only if your privacy policy requires it
    }
)


def strip_sensitive(data: dict) -> dict:
    """Return a copy of *data* with all sensitive keys replaced by '[REDACTED]'."""
    return {
        k: ("[REDACTED]" if k.lower() in SENSITIVE_FIELDS else v)
        for k, v in data.items()
    }


# ── Ensure logs/ directory exists ────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)

# ── Remove Loguru's default handler ──────────────────────────────────────────
logger.remove()

# ── Filter out KeyboardInterrupt from file sinks ─────────────────────────────
def filter_keyboard_interrupt(record):
    """Filter out KeyboardInterrupt exceptions so they don't hit file sinks."""
    if record["exception"] is not None:
        exc_type, _, _ = record["exception"]
        if exc_type is KeyboardInterrupt:
            return False
    return True

# ── Custom CRITICAL level — bold white text on red background ─────────────────
# Loguru lets you override an existing level's colour without re-registering.
logger.level("CRITICAL", color="<bold><white><RED>")

# ── Console format ───────────────────────────────────────────────────────────
# Uses named extra fields injected by logger.bind() in middleware.
# Falls back gracefully when fields are absent (e.g. non-HTTP log sites).
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "<bold>|</bold> "
    "<level>{level: <8}</level> "
    "<bold>|</bold> "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "<bold>|</bold> "
    "<dim>req={extra[request_id]}</dim> "
    "<bold>-</bold> "
    "<level>{message}</level>"
)

# ── Console sink ─────────────────────────────────────────────────────────────
logger.add(
    sys.stderr,
    format=CONSOLE_FORMAT,
    level="DEBUG",
    colorize=True,
    enqueue=False,          # synchronous — always visible immediately
    backtrace=True,
    diagnose=not IS_PRODUCTION,   # suppress variable values in production
)

# ── File sink: all INFO+ messages ─────────────────────────────────────────────
logger.add(
    "logs/app.log",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | "
        "req={extra[request_id]} | {message}"
    ),
    level="INFO",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=not IS_PRODUCTION,
    filter=filter_keyboard_interrupt,
)

# ── File sink: WARNING+ only (errors.log) ─────────────────────────────────────
logger.add(
    "logs/errors.log",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | "
        "req={extra[request_id]} | {message}"
    ),
    level="WARNING",
    rotation="5 MB",
    retention="60 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=not IS_PRODUCTION,
    filter=filter_keyboard_interrupt,
)

# ── Default extras — prevent KeyError when request_id is not bound ────────────
# Every sink references {extra[request_id]}, so we seed it globally.
logger.configure(extra={"request_id": "-"})


# ── Intercept stdlib logging → Loguru ────────────────────────────────────────
class _InterceptHandler(logging.Handler):
    """
    Redirect stdlib log records into Loguru.

    Patches the Loguru record with the original stdlib logger name,
    function and line so {name}/{function}/{line} stay meaningful
    (avoids ugly 'logging:callHandlers:1737' source lines).
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.patch(
            lambda r: r.update(
                name=record.name,
                function=record.funcName or "",
                line=record.lineno or 0,
            )
        ).opt(
            exception=record.exc_info,
        ).log(level, "{}", record.getMessage())


def intercept_stdlib_loggers() -> None:
    """
    Call once at startup to route uvicorn / sqlalchemy / root stdlib logs
    through Loguru so they share format, sinks, and request_id binding.
    """
    intercept = _InterceptHandler()

    for name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy.engine",
    ):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers = [intercept]
        lib_logger.propagate = False

    root = logging.getLogger()
    root.handlers = [intercept]
    root.setLevel(logging.DEBUG)


logger.info(
    "[STARTUP] Loguru configured | env={} | diagnose={}",
    _ENV,
    not IS_PRODUCTION,
)

__all__ = ["logger", "intercept_stdlib_loggers", "strip_sensitive", "SENSITIVE_FIELDS"]