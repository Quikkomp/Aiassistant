"""Browser-only fixture: real auth + temporary accounts; fake SMTP never sends mail."""
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tmp/exam-test-deps'))
sys.path.insert(0, str(ROOT/'local_chat_site'))
from flask import Flask, jsonify, request, session, render_template
from werkzeug.serving import make_server
from auth_store import AuthStore
from auth_routes import make_auth_blueprint
from mail_service import ResetService
from question_bank import BankStore
from exam_store import ExamStore
from exam_routes import make_exam_blueprint
from group_store import GroupStore
from group_routes import make_group_blueprint
from test_auth_recovery import FakeMailer, ImmediateExecutor
from test_exams import FakeAI

sys.stdout.reconfigure(encoding='utf-8')
temporary = tempfile.TemporaryDirectory(prefix='auth-browser-')
account_path = str(Path(temporary.name)/'accounts.sqlite3')
clock_offset = 0
app = Flask(__name__, template_folder=str(ROOT/'local_chat_site/templates'), static_folder=str(ROOT/'local_chat_site/static'))
app.secret_key = 'isolated-browser-cookie-secret-only'
store = AuthStore(lambda:(sqlite3.connect(account_path, timeout=20), 'sqlite'), app.secret_key, clock=lambda:time.time()+clock_offset)
mailer = FakeMailer()
app.register_blueprint(make_auth_blueprint(store, ResetService(store, mailer, ImmediateExecutor())))
banks = BankStore(str(Path(temporary.name)/'banks.sqlite3'))
exams = ExamStore(str(Path(temporary.name)/'exams.sqlite3'))
app.register_blueprint(make_exam_blueprint(exams, banks, lambda:None, FakeAI()))
app.register_blueprint(make_group_blueprint(GroupStore(exams)))


@app.route('/')
def index():
    return render_template('index.html', auth={'authenticated': bool(session.get('auth_user_id')), 'username': session.get('username')})


@app.route('/api/question_sets')
def sets():
    return jsonify(ok=True, banks=banks.list(session.get('auth_user_id','guest')), limit=10)


@app.route('/api/kb_status')
def kb():
    return jsonify(ok=True, files=[], ready=False, total_files=0)


@app.route('/api/past_exam/list')
def templates():
    return jsonify(ok=True, questions=[])


@app.route('/api/private')
def private():
    if not session.get('auth_user_id'):
        return jsonify(ok=False), 401
    return jsonify(ok=True, user_id=session['auth_user_id'])


# These test-only controls are not imported or registered by production app.py.
@app.route('/_test/mailbox')
def mailbox():
    email = request.args.get('email')
    return jsonify(messages=[m for m in mailer.sent if m['email']==email])


@app.route('/_test/control', methods=['POST'])
def control():
    global clock_offset
    data=request.get_json()
    clock_offset += data.get('advance',0)
    mailer.enabled = data.get('enabled', mailer.enabled)
    mailer.fail = data.get('fail', mailer.fail)
    return jsonify(ok=True)


if __name__ == '__main__':
    server=make_server('127.0.0.1',0,app,threaded=True)
    print(json.dumps({'port': server.server_port}),flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        temporary.cleanup()
