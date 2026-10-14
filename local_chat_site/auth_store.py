"""Account and recovery state in the existing MySQL/SQLite account database."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
import unicodedata
import uuid
from contextlib import contextmanager
from werkzeug.security import check_password_hash, generate_password_hash

MESSAGES = {
    'invalid_request': '请求格式无效。', 'username_invalid': '用户名应为 3–32 个字符，支持中文、英文、数字及 _、-、.，首尾须为中文、字母或数字。',
    'email_invalid': '请输入有效的邮箱地址。', 'password_invalid': '新密码应为 8–128 个字符。',
    'password_mismatch': '两次输入的密码不一致。', 'account_exists': '用户名或邮箱已被使用。',
    'invalid_credentials': '用户名、邮箱或密码不正确。', 'invalid_code': '验证码无效、已使用或已过期，请重新获取。',
    'invalid_reset': '重置凭据无效或已过期，请重新验证邮箱。', 'rate_limited': '操作过于频繁，请稍后再试。',
    'mail_unavailable': '验证码邮件服务尚未配置或暂不可用，请联系网站管理员。',
    'service_unavailable': '账号服务暂不可用，请稍后重试。', 'session_expired': '登录已失效，请重新登录。',
    'current_password_invalid': '当前密码不正确。',
}


class AuthError(Exception):
    def __init__(self, code, status=400, retry_after=None):
        super().__init__(MESSAGES[code])
        self.code, self.status, self.retry_after = code, status, retry_after


def value(data, key, limit=1024):
    result = data.get(key, '')
    if not isinstance(result, str) or len(result) > limit:
        raise AuthError('invalid_request')
    return result


def normalize_username(raw):
    if not isinstance(raw, str):
        raise AuthError('username_invalid')
    return unicodedata.normalize('NFKC', raw).strip().lower()


def normalize_email(raw):
    if not isinstance(raw, str):
        raise AuthError('email_invalid')
    return raw.strip().lower()


def validate_username(username):
    if not re.fullmatch(r'[a-z0-9\u3400-\u9fff][a-z0-9\u3400-\u9fff_.-]{1,30}[a-z0-9\u3400-\u9fff]', username):
        raise AuthError('username_invalid')


def validate_email(email):
    if len(email) > 254 or not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", email):
        raise AuthError('email_invalid')
    local, domain = email.split('@')
    if len(local) > 64 or local.startswith('.') or local.endswith('.') or '..' in local or any(len(label) > 63 for label in domain.split('.')):
        raise AuthError('email_invalid')


def validate_password(password, confirmation):
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise AuthError('password_invalid')
    if password != confirmation:
        raise AuthError('password_mismatch')


class AuthStore:
    def __init__(self, connector, secret, clock=time.time):
        self.connector, self.secret, self.clock = connector, str(secret).encode('utf-8'), clock
        with self.db(write=True) as (cur, kind):
            identity = 'INTEGER PRIMARY KEY AUTOINCREMENT' if kind == 'sqlite' else 'BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY'
            tail = '' if kind == 'sqlite' else ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci'
            cur.execute(f"""CREATE TABLE IF NOT EXISTS app_users (
                id {identity}, username VARCHAR(32) NOT NULL UNIQUE, email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL, public_user_id VARCHAR(64) NOT NULL UNIQUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP){tail}""")
            cur.execute(f"""CREATE TABLE IF NOT EXISTS auth_security (
                public_user_id VARCHAR(64) PRIMARY KEY, session_version INTEGER NOT NULL DEFAULT 0){tail}""")
            cur.execute(f"""CREATE TABLE IF NOT EXISTS auth_rate_limits (
                bucket_key VARCHAR(128) PRIMARY KEY, window_start BIGINT NOT NULL, request_count INTEGER NOT NULL){tail}""")
            cur.execute(f"""CREATE TABLE IF NOT EXISTS password_reset_requests (
                id VARCHAR(64) PRIMARY KEY, email VARCHAR(255) NOT NULL, public_user_id VARCHAR(64),
                code_hash VARCHAR(64) NOT NULL, created_at BIGINT NOT NULL, expires_at BIGINT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, delivery_status VARCHAR(16) NOT NULL DEFAULT 'pending',
                grant_hash VARCHAR(64), grant_expires_at BIGINT, used_at BIGINT){tail}""")
            if kind == 'sqlite':
                cur.execute('CREATE INDEX IF NOT EXISTS reset_requests_email ON password_reset_requests(email,created_at)')
        self._dummy_hash = generate_password_hash(secrets.token_urlsafe(32))

    @contextmanager
    def db(self, write=False):
        conn, kind = self.connector()
        cur = None
        try:
            if write and kind == 'sqlite':
                conn.execute('BEGIN IMMEDIATE')
            cur = conn.cursor()
            yield cur, kind
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if cur is not None:
                cur.close()
            conn.close()

    @staticmethod
    def execute(cur, kind, sql, params=()):
        cur.execute(sql.replace('?', '%s') if kind == 'mysql' else sql, params)

    def digest(self, purpose, content):
        return hmac.new(self.secret, (purpose+'\0'+content).encode('utf-8'), hashlib.sha256).hexdigest()

    def limit(self, cur, kind, scope, identity, maximum, duration):
        now = int(self.clock())
        key = scope+':'+self.digest('rate', identity)
        insert = 'INSERT OR IGNORE' if kind == 'sqlite' else 'INSERT IGNORE'
        self.execute(cur, kind, insert+' INTO auth_rate_limits VALUES(?,?,0)', (key, now))
        self.execute(cur, kind, 'SELECT window_start,request_count FROM auth_rate_limits WHERE bucket_key=?'+(' FOR UPDATE' if kind == 'mysql' else ''), (key,))
        start, count = cur.fetchone()
        if now-start >= duration:
            start, count = now, 0
        if count >= maximum:
            raise AuthError('rate_limited', 429, max(1, duration-(now-start)))
        self.execute(cur, kind, 'UPDATE auth_rate_limits SET window_start=?,request_count=? WHERE bucket_key=?', (start, count+1, key))

    def rate(self, scope, identity, maximum, duration):
        with self.db(write=True) as (cur, kind):
            self.limit(cur, kind, scope, identity, maximum, duration)

    def register(self, data, ip):
        username = normalize_username(value(data, 'username', 64))
        email = normalize_email(value(data, 'email', 254))
        password, confirmation = value(data, 'password', 128), value(data, 'confirm_password', 128)
        validate_username(username); validate_email(email); validate_password(password, confirmation)
        self.rate('register-ip', ip, 15, 3600)
        user_id = 'user_'+uuid.uuid4().hex
        password_hash = generate_password_hash(password)
        try:
            with self.db(write=True) as (cur, kind):
                self.execute(cur, kind, 'INSERT INTO app_users(username,email,password_hash,public_user_id) VALUES(?,?,?,?)', (username, email, password_hash, user_id))
        except Exception as exc:
            if isinstance(exc, sqlite3.IntegrityError) or getattr(exc, 'errno', None) == 1062:
                raise AuthError('account_exists', 409) from None
            raise
        return {'username': username, 'user_id': user_id, 'version': 0}

    def login(self, data, ip):
        raw = data.get('account', data.get('username', ''))
        if not isinstance(raw, str) or not 1 <= len(raw.strip()) <= 254:
            raise AuthError('invalid_credentials', 401)
        account = normalize_email(raw) if '@' in raw else normalize_username(raw)
        password = value(data, 'password')
        self.rate('login-ip', ip, 100, 900)
        self.rate('login-account', account, 15, 900)
        column = 'email' if '@' in account else 'username'
        with self.db() as (cur, kind):
            self.execute(cur, kind, f"""SELECT u.username,u.password_hash,u.public_user_id,COALESCE(s.session_version,0)
                FROM app_users u LEFT JOIN auth_security s ON s.public_user_id=u.public_user_id WHERE u.{column}=?""", (account,))
            row = cur.fetchone()
        # Same expensive hash check for nonexistent accounts avoids a cheap timing oracle.
        password_hash = row[1] if row else self.dummy_hash
        if not check_password_hash(password_hash, password) or not row:
            raise AuthError('invalid_credentials', 401)
        with self.db(write=True) as (cur, kind):
            self.execute(cur, kind, 'DELETE FROM auth_rate_limits WHERE bucket_key=?', ('login-account:'+self.digest('rate', account),))
        return {'username': row[0], 'user_id': row[2], 'version': row[3]}

    @property
    def dummy_hash(self):
        if not hasattr(self, '_dummy_hash'):
            self._dummy_hash = generate_password_hash(secrets.token_urlsafe(32))
        return self._dummy_hash

    def session_version(self, user_id):
        with self.db() as (cur, kind):
            self.execute(cur, kind, 'SELECT COALESCE(s.session_version,0) FROM app_users u LEFT JOIN auth_security s ON s.public_user_id=u.public_user_id WHERE u.public_user_id=?', (user_id,))
            row = cur.fetchone()
        return row[0] if row else None

    def change_password(self, user_id, data):
        password, confirmation = value(data, 'new_password', 128), value(data, 'confirm_password', 128)
        validate_password(password, confirmation)
        current = value(data, 'current_password')
        with self.db(write=True) as (cur, kind):
            self.execute(cur, kind, 'SELECT password_hash FROM app_users WHERE public_user_id=?'+(' FOR UPDATE' if kind == 'mysql' else ''), (user_id,))
            row = cur.fetchone()
            if not row or not check_password_hash(row[0], current):
                raise AuthError('current_password_invalid', 401)
            version = self.update_password(cur, kind, user_id, generate_password_hash(password))
        return version

    def update_password(self, cur, kind, user_id, password_hash):
        self.execute(cur, kind, 'UPDATE app_users SET password_hash=? WHERE public_user_id=?', (password_hash, user_id))
        insert = 'INSERT OR IGNORE' if kind == 'sqlite' else 'INSERT IGNORE'
        self.execute(cur, kind, insert+' INTO auth_security VALUES(?,0)', (user_id,))
        self.execute(cur, kind, 'UPDATE auth_security SET session_version=session_version+1 WHERE public_user_id=?', (user_id,))
        self.execute(cur, kind, 'UPDATE password_reset_requests SET used_at=? WHERE public_user_id=? AND used_at IS NULL', (int(self.clock()), user_id))
        self.execute(cur, kind, 'SELECT session_version FROM auth_security WHERE public_user_id=?', (user_id,))
        return cur.fetchone()[0]

    def issue_reset(self, email, ip):
        email = normalize_email(email); validate_email(email)
        stamp = int(self.clock())
        request_id, code = secrets.token_hex(16), f'{secrets.randbelow(1000000):06d}'
        with self.db(write=True) as (cur, kind):
            self.limit(cur, kind, 'reset-send-ip', ip, 30, 3600)
            self.limit(cur, kind, 'reset-send-email', email, 5, 3600)
            self.limit(cur, kind, 'reset-send-cooldown', email, 1, 60)
            self.execute(cur, kind, 'SELECT public_user_id FROM app_users WHERE email=?', (email,))
            row = cur.fetchone()
            user_id = row[0] if row else None
            self.execute(cur, kind, 'UPDATE password_reset_requests SET used_at=? WHERE email=? AND used_at IS NULL', (stamp, email))
            code_hash = self.digest('code', request_id+'\0'+email+'\0'+code)
            self.execute(cur, kind, 'INSERT INTO password_reset_requests(id,email,public_user_id,code_hash,created_at,expires_at) VALUES(?,?,?,?,?,?)', (request_id, email, user_id, code_hash, stamp, stamp+600))
            self.execute(cur, kind, 'DELETE FROM password_reset_requests WHERE created_at<?', (stamp-86400,))
            self.execute(cur, kind, 'DELETE FROM auth_rate_limits WHERE window_start<?', (stamp-86400,))
        return {'id': request_id, 'email': email, 'code': code, 'user_id': user_id}

    def delivery(self, request_id, success):
        with self.db(write=True) as (cur, kind):
            self.execute(cur, kind, 'UPDATE password_reset_requests SET delivery_status=?,used_at=CASE WHEN ? THEN used_at ELSE ? END WHERE id=?', ('sent' if success else 'failed', int(success), int(self.clock()), request_id))

    def verify_reset(self, data, ip):
        email = normalize_email(value(data, 'email', 254)); validate_email(email)
        request_id, code = value(data, 'request_id', 64), value(data, 'code', 6)
        if not re.fullmatch('[a-f0-9]{32}', request_id) or not re.fullmatch('[0-9]{6}', code):
            raise AuthError('invalid_code')
        self.rate('reset-verify-ip', ip, 60, 900)
        stamp, grant = int(self.clock()), secrets.token_urlsafe(32)
        valid = False
        with self.db(write=True) as (cur, kind):
            self.execute(cur, kind, 'SELECT code_hash,expires_at,attempts,used_at,public_user_id,delivery_status,grant_hash FROM password_reset_requests WHERE id=? AND email=?'+(' FOR UPDATE' if kind == 'mysql' else ''), (request_id, email))
            row = cur.fetchone()
            if row and row[3] is None and row[1] > stamp and row[2] < 5 and row[6] is None:
                valid = bool(row[4] and row[5] == 'sent' and hmac.compare_digest(row[0], self.digest('code', request_id+'\0'+email+'\0'+code)))
                if valid:
                    self.execute(cur, kind, 'UPDATE password_reset_requests SET grant_hash=?,grant_expires_at=? WHERE id=?', (self.digest('grant', grant), stamp+600, request_id))
                else:
                    self.execute(cur, kind, 'UPDATE password_reset_requests SET attempts=?,used_at=? WHERE id=?', (row[2]+1, stamp if row[2]+1 >= 5 else None, request_id))
        # Raise after committing: incorrect guesses must persist and exhaust the limit.
        if not valid:
            raise AuthError('invalid_code')
        return {'reset_token': grant, 'expires_in': 600}

    def reset_password(self, data):
        email = normalize_email(value(data, 'email', 254)); validate_email(email)
        request_id, grant = value(data, 'request_id', 64), value(data, 'reset_token', 128)
        validate_password(value(data, 'password', 128), value(data, 'confirm_password', 128))
        if not re.fullmatch('[a-f0-9]{32}', request_id) or not 32 <= len(grant) <= 128:
            raise AuthError('invalid_reset')
        password_hash, stamp = generate_password_hash(data['password']), int(self.clock())
        with self.db(write=True) as (cur, kind):
            self.execute(cur, kind, 'SELECT public_user_id,grant_hash,grant_expires_at,used_at FROM password_reset_requests WHERE id=? AND email=?'+(' FOR UPDATE' if kind == 'mysql' else ''), (request_id, email))
            row = cur.fetchone()
            if not row or row[3] is not None or not row[0] or not row[1] or row[2] <= stamp or not hmac.compare_digest(row[1], self.digest('grant', grant)):
                raise AuthError('invalid_reset')
            self.update_password(cur, kind, row[0], password_hash)
