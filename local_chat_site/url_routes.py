"""URL materials use the same per-user folder and ingest pipeline as uploads."""
import json
import os
import re
import uuid
from flask import Blueprint, jsonify, request, session
from auth_store import AuthError
from url_material import fetch_material, URLImportError


def make_url_blueprint(folder_for_user, ingest, list_files, limiter, fetcher=fetch_material):
    bp = Blueprint('url_materials', __name__)

    @bp.route('/api/material/import_url', methods=['POST'])
    def import_url():
        if not session.get('auth_user_id'):
            return jsonify(ok=False, msg='登录后才可导入 URL 资料。'), 401
        origin = request.headers.get('Origin')
        allowed = {request.host_url.rstrip('/'), 'https://'+request.host, os.getenv('PUBLIC_BASE_URL', '').rstrip('/')}
        if origin and origin.rstrip('/') not in allowed:
            return jsonify(ok=False, msg='请求来源无效。'), 403
        saved = []
        try:
            if not request.is_json:
                raise URLImportError('请求格式无效。')
            raw = request.stream.read(4097)
            if len(raw) > 4096:
                raise URLImportError('请求过长。')
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                raise URLImportError('请求格式无效。') from None
            if not isinstance(data, dict) or not isinstance(data.get('url'), str):
                raise URLImportError('请输入完整的公开资料链接。')
            limiter.rate('url-import-user', session['auth_user_id'], 10, 3600)
            material = fetcher(data['url'].strip())
            filename = 'url_'+re.sub('[^a-zA-Z0-9_-]', '_', material['host'])[:45]+'_'+uuid.uuid4().hex[:12]+material['suffix']
            folder = folder_for_user()
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, filename), 'xb') as output:
                output.write(material['data'])
            saved.append(filename)
            message = ingest(folder)
            if message.startswith(('⚠️', '❌')):
                return jsonify(ok=False, saved=saved, msg=message), 409 if '正在构建' in message else 400
            return jsonify(ok=True, saved=saved, total_files=len(list_files()), msg='链接内容已导入，可在参考资料中选择后出题。')
        except AuthError as exc:
            return jsonify(ok=False, msg=str(exc), retry_after=exc.retry_after), exc.status
        except URLImportError as exc:
            return jsonify(ok=False, msg=str(exc)), 400
        except Exception:
            return jsonify(ok=False, saved=saved, msg='资料导入或知识库更新失败，请稍后重试。'), 503

    @bp.after_request
    def private(response):
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    return bp
