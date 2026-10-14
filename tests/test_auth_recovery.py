"""Real account/recovery routes and disposable DB; SMTP is always mocked."""
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tmp/exam-test-deps'))
sys.path.insert(0, str(ROOT/'local_chat_site'))
from flask import Flask, jsonify, session
from werkzeug.security import generate_password_hash
from auth_store import AuthStore, AuthError
from auth_routes import make_auth_blueprint
from mail_service import SMTPMailer, ResetService


class ImmediateExecutor:
    def submit(self, work, *args):
        work(*args)


class FakeMailer:
    def __init__(self):
        self.sent, self.enabled, self.fail = [], True, False

    def check_config(self):
        if not self.enabled:
            raise AuthError('mail_unavailable', 503)

    def send(self, email, code):
        self.sent.append({'email': email, 'code': code})
        if self.fail:
            raise RuntimeError('simulated delivery failure')


class AuthRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name)/'accounts.sqlite3')
        self.stamp = 1700000000
        self.connector = lambda: (sqlite3.connect(self.path, timeout=20), 'sqlite')
        self.store = AuthStore(self.connector, 'isolated-tests-long-secret-only', clock=lambda: self.stamp)
        self.mailer = FakeMailer()
        self.recovery = ResetService(self.store, self.mailer, ImmediateExecutor())
        self.app = Flask(__name__)
        self.app.secret_key = 'isolated-cookie-secret'
        self.app.register_blueprint(make_auth_blueprint(self.store, self.recovery))
        @self.app.route('/api/private')
        def private():
            return (jsonify(ok=True, user_id=session['auth_user_id']) if session.get('auth_user_id') else (jsonify(ok=False), 401))
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def call(self, endpoint, data=None, status=200, client=None, method='POST', **kwargs):
        response = (client or self.client).open(endpoint, method=method, json=data, **kwargs)
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        return response.get_json()

    def register(self, username='小林_2026', email='student@qq.com', password='old-password'):
        return self.call('/api/auth/register', {'username': username, 'email': email, 'password': password, 'confirm_password': password})

    def challenge(self, email='student@qq.com', client=None):
        result = self.call('/api/auth/password/request', {'email': email}, status=202, client=client)
        return {'email': email, 'request_id': result['request_id'], 'code': self.mailer.sent[-1]['code']}

    def grant(self, **kwargs):
        request = self.challenge(**kwargs)
        response = self.call('/api/auth/password/verify', request)
        return {**request, 'reset_token': response['reset_token'], 'password': 'new-password', 'confirm_password': 'new-password'}

    def test_username_rules_normalization_and_duplicates(self):
        for i, name in enumerate(['小林_2026', 'student.01', 'study-group', '12345', 'ＡＢＣ_2026']):
            self.register(name, f'user{i}@qq.com')
        for name in ['ab', 'a'*33, '_abc', 'abc-', 'abc def', 'abc@qq.com', '🙂123', 'abc/def']:
            self.call('/api/auth/register', {'username': name, 'email': 'bad@qq.com', 'password': 'password-123', 'confirm_password': 'password-123'}, status=400)
        self.call('/api/auth/register', {'username': 'ABC_2026', 'email': 'new@qq.com', 'password': 'password-123', 'confirm_password': 'password-123'}, status=409)

    def test_email_and_username_login_reach_same_account(self):
        self.register()
        original = self.call('/api/private', method='GET')['user_id']
        for data in [{'username': '小林_2026', 'password': 'old-password'}, {'account': ' STUDENT@QQ.COM ', 'password': 'old-password'}]:
            self.call('/api/auth/logout', {})
            self.assertEqual(self.call('/api/auth/login', data)['username'], '小林_2026')
            self.assertEqual(self.call('/api/private', method='GET')['user_id'], original)

    def test_legacy_short_password_and_session_remain_compatible(self):
        with self.store.db(write=True) as (cur, kind):
            cur.execute('INSERT INTO app_users(username,email,password_hash,public_user_id) VALUES(?,?,?,?)', ('legacy', 'legacy@qq.com', generate_password_hash('abc123'), 'user_old_id'))
        with self.client.session_transaction() as cookies:
            cookies.update(auth_user_id='user_old_id', username='legacy')
        self.assertEqual(self.call('/api/private', method='GET')['user_id'], 'user_old_id')
        self.call('/api/auth/logout', {})
        self.call('/api/auth/login', {'account': 'legacy@qq.com', 'password': 'abc123'})
        self.assertEqual(self.call('/api/private', method='GET')['user_id'], 'user_old_id')

    def test_login_errors_are_generic_and_unknown_accounts_are_throttled(self):
        self.register()
        known = self.call('/api/auth/login', {'account': 'student@qq.com', 'password': 'wrong'}, status=401)
        unknown = self.call('/api/auth/login', {'account': 'unknown@qq.com', 'password': 'wrong'}, status=401)
        self.assertEqual(known, unknown)
        for _ in range(14):
            self.call('/api/auth/login', {'account': 'unknown@qq.com', 'password': 'wrong'}, status=401)
        self.call('/api/auth/login', {'account': 'unknown@qq.com', 'password': 'wrong'}, status=429)

    def test_reset_requests_do_not_disclose_existence_or_code(self):
        self.register()
        known = self.call('/api/auth/password/request', {'email': 'student@qq.com'}, status=202)
        unknown = self.call('/api/auth/password/request', {'email': 'unknown@qq.com'}, status=202)
        self.assertEqual(set(known), set(unknown))
        self.assertEqual(known['msg'], unknown['msg'])
        self.assertEqual(len(self.mailer.sent), 1)
        self.assertNotIn('code', known)
        self.assertNotIn('reset_token', known)
        with self.store.db() as (cur, kind):
            cur.execute('SELECT code_hash FROM password_reset_requests WHERE id=?', (known['request_id'],))
            stored = cur.fetchone()[0]
        self.assertNotEqual(stored, self.mailer.sent[0]['code'])
        self.assertEqual(len(stored), 64)

    def test_wrong_guesses_persist_and_lock_after_five(self):
        self.register()
        req = self.challenge()
        wrong = f"{(int(req['code'])+1)%1000000:06d}"
        for _ in range(5):
            self.call('/api/auth/password/verify', {**req, 'code': wrong}, status=400)
        self.call('/api/auth/password/verify', req, status=400)
        with self.store.db() as (cur, kind):
            cur.execute('SELECT attempts,used_at FROM password_reset_requests WHERE id=?', (req['request_id'],))
            row = cur.fetchone()
        self.assertEqual(row[0], 5)
        self.assertIsNotNone(row[1])

    def test_expiry_resend_cooldown_and_old_code_invalidation(self):
        self.register()
        req = self.challenge()
        self.call('/api/auth/password/request', {'email': req['email']}, status=429)
        self.stamp += 61
        second = self.challenge()
        self.call('/api/auth/password/verify', req, status=400)
        self.stamp += 601
        self.call('/api/auth/password/verify', second, status=400)
        self.assertEqual(self.call('/api/auth/login', {'username': '小林_2026', 'password': 'old-password'})['ok'], True)

    def test_verified_code_is_single_use_and_bound_to_email(self):
        self.register()
        data = self.grant()
        self.call('/api/auth/password/verify', {k:data[k] for k in ['email','request_id','code']}, status=400)
        self.call('/api/auth/password/reset', {**data, 'email': 'other@qq.com'}, status=400)
        self.call('/api/auth/password/reset', {**data, 'confirm_password': 'mismatch'}, status=400)
        self.call('/api/auth/password/reset', data)
        self.call('/api/auth/password/reset', data, status=400)

    def test_success_revokes_other_sessions_without_automatic_login(self):
        self.register()
        user_id = self.call('/api/private', method='GET')['user_id']
        other = self.app.test_client()
        self.call('/api/auth/login', {'account':'student@qq.com','password':'old-password'}, client=other)
        data = self.grant()
        self.call('/api/auth/password/reset', data)
        self.assertFalse(self.call('/api/auth/status', method='GET')['authenticated'])
        self.call('/api/private', status=401, method='GET', client=other)
        self.call('/api/auth/login', {'account':'student@qq.com','password':'old-password'}, status=401)
        self.call('/api/auth/login', {'account':'student@qq.com','password':'new-password'})
        self.assertEqual(self.call('/api/private', method='GET')['user_id'], user_id)

    def test_reset_grant_expires_and_resend_invalidates_it(self):
        self.register()
        data = self.grant()
        self.stamp += 61
        self.challenge()
        self.call('/api/auth/password/reset', data, status=400)
        self.stamp += 61
        second = self.grant()
        self.stamp += 601
        self.call('/api/auth/password/reset', second, status=400)

    def test_parallel_reset_consumes_grant_once(self):
        self.register()
        data = self.grant()
        def reset_once():
            try:
                self.store.reset_password(data)
                return True
            except AuthError:
                return False
        with ThreadPoolExecutor(max_workers=3) as workers:
            self.assertEqual(sum(workers.map(lambda _: reset_once(), range(3))), 1)
        with self.store.db() as (cur, kind):
            cur.execute('SELECT session_version FROM auth_security')
            self.assertEqual(cur.fetchone()[0], 1)

    def test_profile_change_revokes_other_sessions_and_recovery_grants(self):
        self.register()
        other = self.app.test_client()
        self.call('/api/auth/login', {'username':'小林_2026','password':'old-password'}, client=other)
        data = self.grant()
        self.call('/api/profile/change_password', {'current_password':'old-password','new_password':'profile-password','confirm_password':'profile-password'})
        self.assertTrue(self.call('/api/auth/status', method='GET')['authenticated'])
        self.call('/api/private', status=401, method='GET', client=other)
        self.call('/api/auth/password/reset', data, status=400)

    def test_mail_unconfigured_and_failed_delivery_do_not_change_passwords(self):
        self.register()
        self.mailer.enabled = False
        for email in ['student@qq.com', 'unknown@qq.com']:
            self.call('/api/auth/password/request', {'email':email}, status=503)
        self.mailer.enabled, self.mailer.fail = True, True
        req = self.challenge()
        self.call('/api/auth/password/verify', req, status=400)
        self.call('/api/auth/login', {'account':'student@qq.com','password':'old-password'})

    def test_input_validation_origin_and_private_response_headers(self):
        self.call('/api/auth/register', [], status=400)
        self.call('/api/auth/login', {'username':{},'password':'password'}, status=401)
        self.call('/api/auth/register', {'username':'valid','email':'a@qq.com\r\nBcc:evil@qq.com','password':'password-123','confirm_password':'password-123'}, status=400)
        self.call('/api/auth/register', {'username':'valid','email':'a@qq.com','password':'short','confirm_password':'short'}, status=400)
        self.call('/api/auth/login', {'account':'student@qq.com','password':'password'}, status=403, headers={'Origin':'https://evil.example'})
        self.register()
        self.call('/api/auth/login', {'account':'student@qq.com','password':'old-password'}, headers={'Origin':'https://localhost'})
        response=self.client.post('/api/auth/password/request', json={'email':'student@qq.com'})
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        response=self.client.post('/api/auth/login', data='x'*8193, content_type='application/json')
        self.assertEqual(response.status_code, 413)

    def test_qq_smtp_uses_tls_and_authorization_code_not_plaintext_transport(self):
        settings={'SMTP_USER':'sender@qq.com','SMTP_PASSWORD':'test-only-authorization','SMTP_FROM':'sender@qq.com'}
        mailer=SMTPMailer(settings)
        with patch('mail_service.smtplib.SMTP_SSL') as smtp:
            client=smtp.return_value
            client.send_message.return_value={}
            mailer.send('student@example.com', '001234')
            self.assertEqual(smtp.call_args.args, ('smtp.qq.com',465))
            client.login.assert_called_once_with('sender@qq.com','test-only-authorization')
            message=client.send_message.call_args.args[0]
            self.assertIn('001234', message.get_content())
            self.assertEqual(message['To'], 'student@example.com')
        settings['SMTP_SECURITY']='none'
        with self.assertRaises(AuthError):
            SMTPMailer(settings).check_config()


if __name__ == '__main__':
    unittest.main()
