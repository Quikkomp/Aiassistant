"""Account entry, email recovery and server-side session revocation."""
import json
import os
import uuid
from flask import Blueprint, jsonify, request, session, current_app
from auth_store import AuthError, value


def make_auth_blueprint(store, recovery):
    bp = Blueprint('auth', __name__)

    def payload():
        if not request.is_json:
            raise AuthError('invalid_request')
        raw = request.stream.read(8193)
        if len(raw) > 8192:
            raise AuthError('invalid_request', 413)
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise AuthError('invalid_request') from None
        if not isinstance(data, dict):
            raise AuthError('invalid_request')
        return data

    def signin(user):
        session.clear()
        session.update(username=user['username'], auth_user_id=user['user_id'], auth_version=user['version'], auth_role=user['role'])
        return jsonify(ok=True, username=user['username'], role=user['role'])

    @bp.before_app_request
    def check_session():
        if request.endpoint == 'static' or not session.get('auth_user_id'):
            return
        try:
            version = store.session_version(session['auth_user_id'])
            role = store.role(session['auth_user_id'])
        except Exception:
            return jsonify(ok=False, code='service_unavailable', msg='账号服务暂不可用，请稍后重试。'), 503
        if version is None or session.get('auth_version', 0) != version:
            session.clear()
            if request.path.startswith('/api/') and not request.path.startswith('/api/auth/'):
                return jsonify(ok=False, code='session_expired', msg='登录已失效，请重新登录。'), 401
        else:
            session['auth_role'] = role

    @bp.before_request
    def protect_origin():
        if request.method == 'POST':
            origin = request.headers.get('Origin')
            # HTTPS frontends commonly reverse-proxy to HTTP Gunicorn. Only the
            # same host is allowed as an HTTPS variant; never trust arbitrary XFF.
            allowed = {request.host_url.rstrip('/'), 'https://'+request.host, os.getenv('PUBLIC_BASE_URL', '').rstrip('/')}
            if origin and origin.rstrip('/') not in allowed:
                raise AuthError('invalid_request', 403)

    @bp.errorhandler(AuthError)
    def known_error(exc):
        body = {'ok': False, 'code': exc.code, 'msg': str(exc)}
        if exc.retry_after is not None:
            body['retry_after'] = exc.retry_after
        response = jsonify(body)
        response.status_code = exc.status
        if exc.retry_after is not None:
            response.headers['Retry-After'] = str(exc.retry_after)
        return response

    @bp.errorhandler(Exception)
    def unknown_error(exc):
        current_app.logger.error('Account service request failed (%s)', type(exc).__name__)
        return jsonify(ok=False, code='service_unavailable', msg='账号服务暂不可用，请稍后重试。'), 503

    @bp.after_request
    def private(response):
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    @bp.route('/api/auth/status')
    def status():
        return jsonify(ok=True, authenticated=bool(session.get('auth_user_id')), username=session.get('username'), role=session.get('auth_role'))

    @bp.route('/api/auth/register', methods=['POST'])
    def register():
        return signin(store.register(payload(), request.remote_addr or 'unknown'))

    @bp.route('/api/auth/login', methods=['POST'])
    def login():
        return signin(store.login(payload(), request.remote_addr or 'unknown'))

    @bp.route('/api/auth/logout', methods=['POST'])
    def logout():
        session.clear()
        return jsonify(ok=True)

    @bp.route('/api/auth/guest', methods=['POST'])
    def guest():
        session.clear()
        session.update(guest_mode=True, user_id='user_'+uuid.uuid4().hex[:8])
        return jsonify(ok=True, guest=True)

    @bp.route('/api/auth/password/request', methods=['POST'])
    def request_code():
        data = payload()
        result = recovery.request(value(data, 'email', 254), request.remote_addr or 'unknown')
        return jsonify(ok=True, **result, msg='如果该邮箱已注册，验证码将发送至该邮箱，请检查收件箱和垃圾邮件。'), 202

    @bp.route('/api/auth/password/verify', methods=['POST'])
    def verify():
        return jsonify(ok=True, **store.verify_reset(payload(), request.remote_addr or 'unknown'))

    @bp.route('/api/auth/password/reset', methods=['POST'])
    def reset():
        store.rate('reset-final-ip', request.remote_addr or 'unknown', 30, 900)
        store.reset_password(payload())
        session.clear()
        return jsonify(ok=True, msg='密码已重置，请使用新密码重新登录。')

    @bp.route('/api/profile/change_password', methods=['POST'])
    def change():
        if not session.get('auth_user_id'):
            raise AuthError('session_expired', 401)
        store.rate('password-change-user', session['auth_user_id'], 10, 900)
        session['auth_version'] = store.change_password(session['auth_user_id'], payload())
        return jsonify(ok=True)

    return bp
