import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from ..config import Config

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, content: str, is_html: bool = False):
    """
    Send an email using SMTP settings from Config.
    Supports both SSL (port 465) and STARTTLS (port 587).
    """
    if not Config.SMTP_HOST or not Config.SMTP_USER:
        logger.warning("SMTP not configured. Skipping email send.")
        return False

    msg = MIMEMultipart()
    # 163等邮箱要求From必须与登录用户一致
    msg['From'] = Config.SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    if is_html:
        msg.attach(MIMEText(content, 'html', 'utf-8'))
    else:
        msg.attach(MIMEText(content, 'plain', 'utf-8'))

    try:
        port = Config.SMTP_PORT
        logger.info(f"Connecting to SMTP server: {Config.SMTP_HOST}:{port}")
        
        if port == 465:
            logger.info("Using SMTP_SSL for port 465")
            server = smtplib.SMTP_SSL(Config.SMTP_HOST, port, timeout=30)
        else:
            logger.info(f"Using SMTP with STARTTLS for port {port}")
            server = smtplib.SMTP(Config.SMTP_HOST, port, timeout=30)
            server.starttls()
        
        logger.info(f"Logging in as: {Config.SMTP_USER}")
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        
        logger.info(f"Sending email to: {to_email}")
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP connection failed: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
