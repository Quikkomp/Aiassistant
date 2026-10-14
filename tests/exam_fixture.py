"""Browser fixture: real exam routes/templates, ephemeral DBs and mock AI/account entry."""
import json
import sys
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tmp/exam-test-deps"))
sys.path.insert(0, str(ROOT / "local_chat_site"))
from flask import Flask, request, session, jsonify, render_template
from werkzeug.serving import make_server
from question_bank import BankStore
from exam_store import ExamStore
from exam_routes import make_exam_blueprint
from test_exams import FakeAI
from group_store import GroupStore
from group_routes import make_group_blueprint

sys.stdout.reconfigure(encoding="utf-8")
temporary = tempfile.TemporaryDirectory(prefix="exam-browser-")
bank_store = BankStore(str(Path(temporary.name) / "banks.sqlite3"))
exam_store = ExamStore(str(Path(temporary.name) / "exams.sqlite3"))
bank_id = bank_store.reserve("Teacher", "基础物理 · 冰点训练", {})
bank_store.finish(bank_id, "Teacher", "Q1 [fill_blank]\n在标准大气压下，水的冰点是 ____ 摄氏度。\n\nQ2 [short_answer]\n请解释什么是冰点。")
app = Flask(__name__, template_folder=str(ROOT / "local_chat_site/templates"), static_folder=str(ROOT / "local_chat_site/static"))
app.secret_key = "isolated-browser-tests-only"
app.register_blueprint(make_exam_blueprint(exam_store, bank_store, lambda: None, FakeAI()))
app.register_blueprint(make_group_blueprint(GroupStore(exam_store)))


@app.route("/")
def index():
    return render_template("index.html", auth={"authenticated": bool(session.get("auth_user_id")), "username": session.get("username")})


@app.route("/api/auth/<action>", methods=["POST"])
def auth(action):
    session.clear()
    if action == "login":
        username = request.get_json()["username"]
        session["auth_user_id"] = username
        session["username"] = username
        return jsonify(ok=True, username=username)
    return jsonify(ok=True)


@app.route("/api/question_sets")
def banks():
    return jsonify(ok=True, banks=bank_store.list(session.get("auth_user_id", "Guest")), limit=10)


@app.route("/api/question_sets/<bank_id>/progress", methods=["PUT"])
def progress(bank_id):
    data = request.get_json()
    bank_store.save_progress(bank_id, session.get("auth_user_id", "Guest"), data["progress"], data["version"])
    return jsonify(ok=True, version=data["version"] + 1)


@app.route("/api/kb_status")
def kb():
    return jsonify(ok=True, files=[], ready=False, total_files=0)


@app.route("/api/past_exam/list")
def templates():
    return jsonify(ok=True, questions=[])


if __name__ == "__main__":
    server = make_server("127.0.0.1", 0, app, threaded=True)
    print(json.dumps({"port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        temporary.cleanup()
