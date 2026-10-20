"""TLS-only QQ SMTP adapter and bounded, non-enumerating recovery mail dispatch."""
import logging
import os
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from email.utils import formataddr
from threading import BoundedSemaphore
from auth_store import AuthError, normalize_email, validate_email

logger = logging.getLogger(__name__)


class SMTPMailer:
    def __init__(self, settings=None):
        self.settings = dict(os.environ if settings is None else settings)

    def check_config(self):
        env = self.settings
        if not all(env.get(k, '').strip() for k in ('SMTP_USER', 'SMTP_PASSWORD')):
            raise AuthError('mail_unavailable', 503)
        sender = normalize_email(env.get('SMTP_FROM') or env['SMTP_USER'])
        try:
            validate_email(sender)
        except AuthError:
            raise AuthError('mail_unavailable', 503) from None
        security = env.get('SMTP_SECURITY', 'ssl').lower()
        if security not in {'ssl', 'starttls'}:
            raise AuthError('mail_unavailable', 503)
        try:
            port = int(env.get('SMTP_PORT') or ('465' if security == 'ssl' else '587'))
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            raise AuthError('mail_unavailable', 503) from None

    def send(self, recipient, code):
        self.check_config()
        env = self.settings
        sender = normalize_email(env.get('SMTP_FROM') or env['SMTP_USER'])
        recipient = normalize_email(recipient); validate_email(recipient)
        message = EmailMessage()
        message['Subject'] = '智练 WizPractice 密码重置验证码'
        message['From'] = formataddr(('智练 WizPractice', sender))
        message['To'] = recipient
        message.set_content(f'你正在重置智练 WizPractice 账号密码。\n\n验证码：{code}\n\n验证码 10 分钟内有效，请勿转发或告诉任何人。\n如果不是你本人操作，请忽略此邮件；你的密码不会因此改变。')
        context = ssl.create_default_context()
        host = env.get('SMTP_HOST') or 'smtp.qq.com'
        security = env.get('SMTP_SECURITY', 'ssl').lower()
        port = int(env.get('SMTP_PORT') or ('465' if security == 'ssl' else '587'))
        client = smtplib.SMTP_SSL(host, port, timeout=10, context=context) if security == 'ssl' else smtplib.SMTP(host, port, timeout=10)
        with client:
            if security == 'starttls':
                client.ehlo(); client.starttls(context=context); client.ehlo()
            client.login(env['SMTP_USER'], env['SMTP_PASSWORD'])
            refused = client.send_message(message)
            if refused:
                raise RuntimeError('Recipient rejected')


class ResetService:
    def __init__(self, store, mailer=None, executor=None):
        self.store, self.mailer = store, mailer or SMTPMailer()
        self.executor = executor or ThreadPoolExecutor(max_workers=2, thread_name_prefix='reset-mail')
        self.slots = BoundedSemaphore(20)

    def request(self, email, ip):
        self.mailer.check_config()
        if self.store.secret in {b'', b'None', b'dev-secret-change-me', b'replace-with-a-long-random-secret'}:
            raise AuthError('mail_unavailable', 503)
        if not self.slots.acquire(blocking=False):
            raise AuthError('mail_unavailable', 503)
        try:
            challenge = self.store.issue_reset(email, ip)
            # Both real and unknown addresses queue a job and return the same response.
            self.executor.submit(self._deliver, challenge)
        except Exception:
            self.slots.release()
            raise
        return {'request_id': challenge['id'], 'expires_in': 600, 'retry_after': 60}

    def _deliver(self, challenge):
        try:
            if challenge['user_id']:
                self.mailer.send(challenge['email'], challenge['code'])
            self.store.delivery(challenge['id'], True)
        except Exception as exc:
            # Never print recipient addresses, SMTP secrets, OTPs or reset grants.
            logger.warning('Password reset mail delivery failed (%s)', type(exc).__name__)
            try:
                self.store.delivery(challenge['id'], False)
            except Exception:
                logger.warning('Password reset delivery state update failed')
        finally:
            self.slots.release()
