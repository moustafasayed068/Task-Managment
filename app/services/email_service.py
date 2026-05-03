"""
email_service.py
~~~~~~~~~~~~~~~~
Sends HTML alert emails via SMTP.

Two send modes:
  • _send()          — blocking, runs in the calling thread.
  • _fire()          — spawns a daemon-free thread so the HTTP response
                       is not delayed.  Used by the public alert helpers.
  • send_email_sync()— forces a *synchronous* send and returns True/False.
                       Used by the /test-email diagnostic endpoint and by
                       the alert helpers when you want guaranteed delivery
                       before the HTTP response.

Why synchronous by default now:
  Background threads can silently swallow errors, making it impossible to
  tell whether the email was actually sent.  For security alerts we WANT
  the caller to know if it failed.
"""

import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config_core import settings
from app.core.logger_core import logger


# ─────────────────────────────────────────────────────────────────────────────
# Configuration check
# ─────────────────────────────────────────────────────────────────────────────

def _configured() -> bool:
    ok = all([
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_username,
        settings.smtp_password,
        settings.alert_email_from,
        settings.alert_email_to,
    ])
    if not ok:
        logger.warning(
            "EMAIL CONFIG MISSING | smtp_host={} smtp_port={} "
            "smtp_username={} smtp_password={} "
            "alert_email_from={} alert_email_to={}",
            settings.smtp_host,
            settings.smtp_port,
            bool(settings.smtp_username),
            "***" if settings.smtp_password else "<empty>",
            settings.alert_email_from,
            settings.alert_email_to,
        )
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Low-level send
# ─────────────────────────────────────────────────────────────────────────────

def _send(subject: str, html: str) -> bool:
    """
    Blocking SMTP send.  Returns True on success, False on failure.
    All errors are logged — never raises.
    """
    if not _configured():
        logger.error("EMAIL SKIPPED | SMTP not fully configured — check .env")
        return False

    # Strip stray spaces from the app-password (common copy-paste issue)
    password = settings.smtp_password.strip().replace(" ", "")

    logger.info(
        "EMAIL ATTEMPT | host={}:{} tls={} | from={} to={} | subject={!r}",
        settings.smtp_host, settings.smtp_port, settings.smtp_use_tls,
        settings.alert_email_from, settings.alert_email_to, subject,
    )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.alert_email_from
        msg["To"]      = settings.alert_email_to
        msg.attach(MIMEText(html, "html"))

        # Create an SSL context that works on Windows
        ctx = ssl.create_default_context()

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as srv:
            srv.set_debuglevel(0)         # set to 1 for wire-level debugging
            srv.ehlo()
            if settings.smtp_use_tls:
                srv.starttls(context=ctx)
                srv.ehlo()
            srv.login(settings.smtp_username, password)
            srv.sendmail(
                settings.alert_email_from,
                [settings.alert_email_to],
                msg.as_string(),
            )

        logger.success(
            "EMAIL SENT | to={} | subject={!r}",
            settings.alert_email_to, subject,
        )
        return True

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "EMAIL FAILED | SMTPAuthenticationError — "
            "check SMTP_USERNAME / SMTP_PASSWORD (use a Gmail App Password, "
            "not your real password) | {}",
            exc,
        )
    except smtplib.SMTPConnectError as exc:
        logger.error(
            "EMAIL FAILED | SMTPConnectError — cannot reach {}:{} | {}",
            settings.smtp_host, settings.smtp_port, exc,
        )
    except smtplib.SMTPException as exc:
        logger.error("EMAIL FAILED | SMTPException | {}", exc)
    except OSError as exc:
        logger.error(
            "EMAIL FAILED | Network/OS error (DNS? firewall?) | {}: {}",
            type(exc).__name__, exc,
        )
    except Exception as exc:
        logger.error("EMAIL FAILED | Unexpected {} | {}", type(exc).__name__, exc)

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Public send modes
# ─────────────────────────────────────────────────────────────────────────────

def send_email_sync(subject: str, html: str) -> bool:
    """Synchronous send — blocks until done. Returns True/False."""
    return _send(subject, html)


def _fire(subject: str, html: str) -> None:
    """Spawn a non-daemon thread to send the email without blocking."""
    t = threading.Thread(target=_send, args=(subject, html), daemon=False)
    t.start()


# ─────────────────────────────────────────────────────────────────────────────
# Public alert functions — SYNCHRONOUS by default so failure is visible
# ─────────────────────────────────────────────────────────────────────────────

def send_login_failure_alert(
    username: str,
    ip_address: str,
    role: str | None,
    reason: str,
) -> bool:
    """Send a 'Failed Login' security alert email.  Returns True on success."""
    try:
        role_display = role or "N/A (user not found)"
        subject = "Security Alert: Failed Login Attempt"
        html = f"""\
        <html><body style="font-family:Arial,sans-serif;padding:20px;color:#333">
          <h2 style="color:#c0392b">Failed Login Attempt</h2>
          <table style="border-collapse:collapse;width:60%">
            <tr style="background:#f2f2f2">
              <td style="padding:10px;font-weight:bold;border:1px solid #ddd">Username</td>
              <td style="padding:10px;border:1px solid #ddd">{username}</td>
            </tr>
            <tr>
              <td style="padding:10px;font-weight:bold;border:1px solid #ddd">Role</td>
              <td style="padding:10px;border:1px solid #ddd">{role_display}</td>
            </tr>
            <tr style="background:#f2f2f2">
              <td style="padding:10px;font-weight:bold;border:1px solid #ddd">IP Address</td>
              <td style="padding:10px;border:1px solid #ddd">{ip_address}</td>
            </tr>
            <tr>
              <td style="padding:10px;font-weight:bold;border:1px solid #ddd">Reason</td>
              <td style="padding:10px;border:1px solid #ddd">{reason}</td>
            </tr>
          </table>
          <p style="margin-top:20px;color:#555">Review logs and block this IP if suspicious.</p>
          <p style="font-size:11px;color:#aaa">Automated alert — Task Management System</p>
        </body></html>
        """
        return _send(subject, html)
    except Exception as exc:
        logger.exception("Background task send_login_failure_alert failed unexpectedly | {}", exc)
        return False


def send_unauthorized_access_alert(
    username: str,
    ip_address: str,
    role: str,
    endpoint: str,
) -> bool:
    """Send an 'Unauthorized Access' security alert email.  Returns True on success."""
    subject = "Security Alert: Unauthorized Access Attempt"
    html = f"""\
    <html><body style="font-family:Arial,sans-serif;padding:20px;color:#333">
      <h2 style="color:#e67e22">Unauthorized Access Attempt</h2>
      <table style="border-collapse:collapse;width:60%">
        <tr style="background:#f2f2f2">
          <td style="padding:10px;font-weight:bold;border:1px solid #ddd">Username</td>
          <td style="padding:10px;border:1px solid #ddd">{username}</td>
        </tr>
        <tr>
          <td style="padding:10px;font-weight:bold;border:1px solid #ddd">Role</td>
          <td style="padding:10px;border:1px solid #ddd">{role}</td>
        </tr>
        <tr style="background:#f2f2f2">
          <td style="padding:10px;font-weight:bold;border:1px solid #ddd">IP Address</td>
          <td style="padding:10px;border:1px solid #ddd">{ip_address}</td>
        </tr>
        <tr>
          <td style="padding:10px;font-weight:bold;border:1px solid #ddd">Endpoint</td>
          <td style="padding:10px;border:1px solid #ddd">{endpoint}</td>
        </tr>
      </table>
      <p style="margin-top:20px;color:#555">This may be a privilege-escalation attempt.</p>
      <p style="font-size:11px;color:#aaa">Automated alert — Task Management System</p>
    </body></html>
    """
    return _send(subject, html)


# Backward-compat alias
def send_unauthorized_admin_alert(
    attempted_username: str,
    ip_address: str,
    reason: str = "Unauthorized admin login attempt",
) -> bool:
    return send_login_failure_alert(
        username=attempted_username,
        ip_address=ip_address,
        role="admin",
        reason=reason,
    )