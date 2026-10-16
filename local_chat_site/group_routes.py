"""Authenticated group administration; students never receive peers' scores or keys."""
import os
from io import BytesIO
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, session, render_template, send_file
from exam_store import ExamError
from account_access import require_teacher


def make_group_blueprint(store):
    bp = Blueprint('groups', __name__)

    def user():
        return session['auth_user_id']

    def body():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ExamError('请求格式无效。')
        return data

    def packet(group):
        if group['role'] == 'owner':
            base = os.getenv('PUBLIC_BASE_URL', '').rstrip('/') or request.url_root.rstrip('/')
            if urlparse(base).scheme not in {'http', 'https'}:
                raise ExamError('请配置正确的 PUBLIC_BASE_URL。', 500)
            group['invite_url'] = base + '/group/' + group.pop('token')
        return group

    @bp.before_request
    def protect():
        if request.endpoint == 'groups.page':
            return
        if not session.get('auth_user_id'):
            return jsonify(ok=False, msg='请先登录账号，游客不能加入学习小组。'), 401
        if (request.endpoint in {'groups.rotate', 'groups.qr', 'groups.publish', 'groups.results'}
                or (request.endpoint == 'groups.catalog' and request.method == 'POST')
                or (request.endpoint in {'groups.detail', 'groups.member'} and request.method == 'PUT')):
            require_teacher()
        if request.method not in {'GET', 'HEAD'}:
            origin = request.headers.get('Origin')
            allowed = {request.host_url.rstrip('/'), os.getenv('PUBLIC_BASE_URL', '').rstrip('/')}
            if origin and origin.rstrip('/') not in allowed:
                return jsonify(ok=False, msg='请求来源无效。'), 403

    @bp.errorhandler(ExamError)
    def error(exc):
        return jsonify(ok=False, msg=str(exc)), exc.status

    @bp.after_request
    def private_response(response):
        if request.path.startswith('/api/groups'):
            response.headers['Cache-Control'] = 'private, no-store'
        return response

    @bp.route('/group/<token>')
    def page(token):
        return render_template('index.html', auth={'authenticated': bool(session.get('auth_user_id')), 'username': session.get('username'), 'role': session.get('auth_role')})

    @bp.route('/api/groups', methods=['GET', 'POST'])
    def catalog():
        if request.method == 'POST':
            return jsonify(ok=True, group=packet(store.create(user(), session.get('username', ''), body())))
        return jsonify(ok=True, groups=store.catalog(user()))

    @bp.route('/api/groups/<group_id>', methods=['GET', 'PUT'])
    def detail(group_id):
        group = store.update(group_id, user(), body()) if request.method == 'PUT' else store.detail(group_id, user())
        return jsonify(ok=True, group=packet(group))

    @bp.route('/api/groups/shared/<token>')
    def preview(token):
        return jsonify(ok=True, group=store.preview(token, user()))

    @bp.route('/api/groups/shared/<token>/join', methods=['POST'])
    def join(token):
        return jsonify(ok=True, group=packet(store.join(token, user(), session.get('username', ''))))

    @bp.route('/api/groups/<group_id>/invite', methods=['POST'])
    def rotate(group_id):
        return jsonify(ok=True, group=packet(store.rotate(group_id, user())))

    @bp.route('/api/groups/<group_id>/qr')
    def qr(group_id):
        group = store.detail(group_id, user())
        if group['role'] != 'owner':
            raise ExamError('只有群主可以获取邀请二维码。', 404)
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderSVG
        code = QrCodeWidget(packet(group)['invite_url'])
        bounds = code.getBounds()
        scale = 240/(bounds[2]-bounds[0])
        drawing = Drawing(240, 240, transform=[scale, 0, 0, scale, 0, 0])
        drawing.add(code)
        response = send_file(BytesIO(renderSVG.drawToString(drawing).encode('utf-8')), mimetype='image/svg+xml')
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    @bp.route('/api/groups/<group_id>/members/<target>', methods=['GET', 'PUT'])
    def member(group_id, target):
        if request.method == 'PUT':
            return jsonify(ok=True, group=packet(store.member(group_id, user(), target, body().get('status'))))
        return jsonify(ok=True, member=store.member_info(group_id, user(), target))

    @bp.route('/api/groups/<group_id>/exams', methods=['POST'])
    def publish(group_id):
        data = body()
        result = store.publish(group_id, user(), data.get('exam_id'), data.get('version'), data.get('reviewed'))
        result['group'] = packet(result['group'])
        return jsonify(ok=True, **result)

    @bp.route('/api/groups/<group_id>/exams/<exam_id>/results')
    def results(group_id, exam_id):
        return jsonify(ok=True, analytics=store.results(group_id, user(), exam_id))

    return bp
