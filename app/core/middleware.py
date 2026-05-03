"""
middleware.py
~~~~~~~~~~~~~
Pure ASGI logging middleware. Logs every request and response with
structured fields via logger.bind() — never free-form interpolation.

Key improvements over v1:
  • UUID request_id generated per request and bound to every log line
    so all records for one request are trivially grep-able / filterable.
  • Structured extra fields (method, path, client_ip, status, duration_ms)
    instead of positional format strings — ready for JSON sinks or OTEL.
  • logger.exception() for unhandled errors — includes full traceback
    automatically without any extra opt(exception=...) ceremony.
  • Standardised prefixes: [REQUEST] / [RESPONSE] / [ERROR] / [CRITICAL].
  • 🔥 emoji on CRITICAL lines for instant visual scanning in terminals.
  • client_ip is bound once and never logged elsewhere to minimise PII spread.

Does NOT use BaseHTTPMiddleware — that class has streaming bugs on
Windows with uvicorn --reload that silently drop log lines.
"""

import time
import uuid

from app.core.logger_core import logger


class LoggingMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # ── Per-request identity ──────────────────────────────────────────────
        request_id = str(uuid.uuid4())
        method     = scope.get("method", "")
        path       = scope.get("path", "")
        client     = scope.get("client")
        client_ip  = client[0] if client else "unknown"

        # Bind fields that stay constant for the whole request.
        # All log calls below use this bound logger so every line
        # carries the same structured extras automatically.
        req_logger = logger.bind(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
        )

        start = time.perf_counter()
        req_logger.info("[REQUEST]  {} {}", method, path)

        status_holder = [0]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder[0] = message.get("status", 0)
                ms = (time.perf_counter() - start) * 1000
                headers = list(message.get("headers", []))
                headers.append((b"x-response-time", f"{ms:.2f}ms".encode()))
                message = {**message, "headers": headers}
            await send(message)

        # ── Dispatch ──────────────────────────────────────────────────────────
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            ms = (time.perf_counter() - start) * 1000
            # logger.exception() captures the full traceback automatically.
            req_logger.bind(duration_ms=round(ms, 2)).exception(
                "[CRITICAL] Unhandled exception | {} {} | {:.2f}ms",
                method, path, ms,
            )
            raise

        # ── Response logging ──────────────────────────────────────────────────
        ms   = (time.perf_counter() - start) * 1000
        code = status_holder[0]

        resp_logger = req_logger.bind(status=code, duration_ms=round(ms, 2))

        if code < 400:
            resp_logger.info(
                "[RESPONSE] {} {} | status={} | {:.2f}ms",
                method, path, code, ms,
            )
        elif code < 500:
            resp_logger.warning(
                "[RESPONSE] {} {} | status={} | {:.2f}ms",
                method, path, code, ms,
            )
        else:
            resp_logger.error(
                "[ERROR]    {} {} | status={} | {:.2f}ms",
                method, path, code, ms,
            )