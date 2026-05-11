"""
Email Notification Service for CrackPi
Sends email alerts for job completion, client status changes, etc.
"""

import smtplib
import logging
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

logger = logging.getLogger(__name__)


def get_smtp_settings():
    """Load SMTP settings from database"""
    try:
        from models import Settings
        settings = {}
        for s in Settings.query.filter(Settings.key.like('smtp_%')).all():
            settings[s.key] = s.value
        return settings
    except Exception as e:
        logger.error(f"Error loading SMTP settings: {e}")
        return {}


def send_email_async(to_addr, subject, html_body, text_body=None, attachment=None, attachment_name=None):
    """Send email in background thread"""
    thread = threading.Thread(
        target=_send_email,
        args=(to_addr, subject, html_body, text_body, attachment, attachment_name),
        daemon=True
    )
    thread.start()


def _send_email(to_addr, subject, html_body, text_body=None, attachment=None, attachment_name=None):
    """Actually send the email"""
    settings = get_smtp_settings()

    smtp_host = settings.get('smtp_host', '')
    smtp_port = int(settings.get('smtp_port', 587))
    smtp_user = settings.get('smtp_username', '')
    smtp_pass = settings.get('smtp_password', '')
    smtp_from = settings.get('smtp_from', smtp_user)
    smtp_tls = settings.get('smtp_tls', 'true').lower() == 'true'

    if not smtp_host or not to_addr:
        logger.debug("SMTP not configured or no recipient, skipping email")
        return

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_from
        msg['To'] = to_addr
        msg['Subject'] = subject
        msg['X-Mailer'] = 'CrackPi Notification System'

        # Plain text fallback
        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))

        # HTML body
        msg.attach(MIMEText(html_body, 'html'))

        # Optional attachment
        if attachment and attachment_name:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment_name}"')
            msg.attach(part)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, to_addr, msg)

        logger.info(f"Email sent to {to_addr}: {subject}")

    except Exception as e:
        logger.error(f"Failed to send email to {to_addr}: {e}")


def notify_job_completed(job, cracked_count: int, total_count: int, user_email: str):
    """Send job completion notification"""
    if not user_email:
        return

    crack_rate = round(cracked_count / total_count * 100, 1) if total_count > 0 else 0
    duration_str = ''
    if job.started_at and job.completed_at:
        delta = job.completed_at - job.started_at
        secs = int(delta.total_seconds())
        if secs < 60:
            duration_str = f"{secs}s"
        elif secs < 3600:
            duration_str = f"{secs//60}m {secs%60}s"
        else:
            duration_str = f"{secs//3600}h {(secs%3600)//60}m"

    subject = f"[CrackPi] Job '{job.name}' Completed — {crack_rate}% cracked"

    html = f"""
    <html><body style="font-family: Arial, sans-serif; background:#1a1a2e; color:#e0e0e0; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#16213e; border-radius:12px; padding:30px; border:1px solid #0f3460;">
        <h2 style="color:#00d4ff; margin-top:0;">&#x2714; Job Completed</h2>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="padding:8px 0; color:#a0a0a0;">Job Name</td><td style="padding:8px 0; font-weight:bold;">{job.name}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Hash Type</td><td style="padding:8px 0;">{job.hash_type.name if job.hash_type else 'Unknown'}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Total Hashes</td><td style="padding:8px 0;">{total_count:,}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Cracked</td><td style="padding:8px 0; color:#00e676; font-weight:bold;">{cracked_count:,} ({crack_rate}%)</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Duration</td><td style="padding:8px 0;">{duration_str or 'N/A'}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Completed At</td><td style="padding:8px 0;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
        </table>
        <p style="color:#666; font-size:12px; margin-top:20px;">This is an automated notification from CrackPi.</p>
    </div>
    </body></html>
    """

    text = f"Job '{job.name}' completed. Cracked: {cracked_count}/{total_count} ({crack_rate}%). Duration: {duration_str}"
    send_email_async(user_email, subject, html, text)


def notify_job_failed(job, error_msg: str, user_email: str):
    """Send job failure notification"""
    if not user_email:
        return

    subject = f"[CrackPi] Job '{job.name}' Failed"
    html = f"""
    <html><body style="font-family: Arial, sans-serif; background:#1a1a2e; color:#e0e0e0; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#16213e; border-radius:12px; padding:30px; border:1px solid #c62828;">
        <h2 style="color:#ff5252; margin-top:0;">&#x2718; Job Failed</h2>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="padding:8px 0; color:#a0a0a0;">Job Name</td><td style="padding:8px 0; font-weight:bold;">{job.name}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Error</td><td style="padding:8px 0; color:#ff5252;">{error_msg}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Time</td><td style="padding:8px 0;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
        </table>
        <p style="color:#666; font-size:12px; margin-top:20px;">This is an automated notification from CrackPi.</p>
    </div>
    </body></html>
    """
    text = f"Job '{job.name}' failed. Error: {error_msg}"
    send_email_async(user_email, subject, html, text)


def notify_client_offline(client, user_email: str):
    """Send client offline notification"""
    if not user_email:
        return

    subject = f"[CrackPi] Client '{client.hostname or client.client_id[:8]}' Went Offline"
    html = f"""
    <html><body style="font-family: Arial, sans-serif; background:#1a1a2e; color:#e0e0e0; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#16213e; border-radius:12px; padding:30px; border:1px solid #f57f17;">
        <h2 style="color:#ffab40; margin-top:0;">&#x26A0; Client Offline</h2>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="padding:8px 0; color:#a0a0a0;">Client</td><td style="padding:8px 0; font-weight:bold;">{client.hostname or client.client_id[:8]}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">IP Address</td><td style="padding:8px 0;">{client.ip_address or 'Unknown'}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Last Seen</td><td style="padding:8px 0;">{client.last_seen.strftime('%Y-%m-%d %H:%M UTC') if client.last_seen else 'Unknown'}</td></tr>
        </table>
        <p style="color:#666; font-size:12px; margin-top:20px;">This is an automated notification from CrackPi.</p>
    </div>
    </body></html>
    """
    text = f"Client '{client.hostname or client.client_id[:8]}' went offline at {client.last_seen}"
    send_email_async(user_email, subject, html, text)


def notify_client_online(client, user_email: str):
    """Send client online notification"""
    if not user_email:
        return

    subject = f"[CrackPi] Client '{client.hostname or client.client_id[:8]}' Came Online"
    html = f"""
    <html><body style="font-family: Arial, sans-serif; background:#1a1a2e; color:#e0e0e0; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#16213e; border-radius:12px; padding:30px; border:1px solid #1b5e20;">
        <h2 style="color:#00e676; margin-top:0;">&#x2714; Client Online</h2>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="padding:8px 0; color:#a0a0a0;">Client</td><td style="padding:8px 0; font-weight:bold;">{client.hostname or client.client_id[:8]}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">IP Address</td><td style="padding:8px 0;">{client.ip_address or 'Unknown'}</td></tr>
            <tr><td style="padding:8px 0; color:#a0a0a0;">Time</td><td style="padding:8px 0;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
        </table>
        <p style="color:#666; font-size:12px; margin-top:20px;">This is an automated notification from CrackPi.</p>
    </div>
    </body></html>
    """
    text = f"Client '{client.hostname or client.client_id[:8]}' came online at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    send_email_async(user_email, subject, html, text)


def send_test_email(to_addr: str) -> tuple:
    """Send a test email, returns (success, message)"""
    settings = get_smtp_settings()
    smtp_host = settings.get('smtp_host', '')
    if not smtp_host:
        return False, "SMTP host not configured"

    try:
        html = """
        <html><body style="font-family: Arial, sans-serif; padding:20px; background:#1a1a2e; color:#e0e0e0;">
        <div style="max-width:600px; margin:0 auto; background:#16213e; border-radius:12px; padding:30px; border:1px solid #0f3460;">
            <h2 style="color:#00d4ff;">&#x2714; CrackPi Test Email</h2>
            <p>Your email notifications are working correctly!</p>
            <p style="color:#666; font-size:12px;">Sent from CrackPi Notification System</p>
        </div>
        </body></html>
        """
        _send_email(to_addr, "[CrackPi] Test Notification", html, "CrackPi email test — notifications are working!")
        return True, "Test email sent successfully"
    except Exception as e:
        return False, str(e)
