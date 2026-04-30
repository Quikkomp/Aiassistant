import os
import re
import sqlite3
import sys
import uuid
from typing import List
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
import rag_agentV3_2 as rag_agent_module  # ✅ 修改为你的文件名
import psycopg2
from collections import Counter


# ---------------- 基础配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
# 这里仍然把 materials 当成根目录，后面会在里面按 user_id 创建子目录
UPLOAD_FOLDER = os.path.join(BASE_DIR, "materials")
PAST_EXAM_UPLOAD_FOLDER = os.path.join(BASE_DIR, "exam_db", "past_exam_files")
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH") or os.path.join(BASE_DIR, "app_users.sqlite3")

# ---------------- 数据库配置 ----------------
DB_DSN = os.getenv("EXAM_DB_DSN")  # 从 .env 中读取

def get_db_conn():
    """
    获取一个新的 PostgreSQL 连接。
    """
    if not DB_DSN:
        raise RuntimeError("EXAM_DB_DSN is not set in environment variables")
    return psycopg2.connect(DB_DSN)


def init_db():
    """
    启动 Flask 时确保两张表已经存在。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_rounds (
                id              SERIAL PRIMARY KEY,
                user_id         TEXT NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                round_score     INTEGER,
                total_questions INTEGER,
                correct_count   INTEGER,
                partial_count   INTEGER,
                wrong_count     INTEGER
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_answers (
                id              SERIAL PRIMARY KEY,
                round_id        INTEGER NOT NULL REFERENCES user_rounds(id) ON DELETE CASCADE,
                user_id         TEXT NOT NULL,
                question_index  INTEGER,
                question_type   TEXT,
                verdict         TEXT,
                question_text   TEXT,
                student_answer  TEXT,
                evaluation      TEXT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        # ⭐ 新增：存储用户与 AI 的对话记录
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id             SERIAL PRIMARY KEY,
                user_id        TEXT NOT NULL,
                conv_type      TEXT NOT NULL,       -- 对话类型：chat / exam_qa 等
                question_index INTEGER,            -- 如与某题绑定，则存该题 index，否则为 NULL
                role           TEXT NOT NULL,      -- 'user' 或 'assistant'
                content        TEXT NOT NULL,      -- 对话内容
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id              SERIAL PRIMARY KEY,
                username        TEXT NOT NULL UNIQUE,
                email           TEXT NOT NULL UNIQUE,
                password_hash   TEXT NOT NULL,
                public_user_id  TEXT NOT NULL UNIQUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ DB init success")
    except Exception as e:
        # 不要让整个应用挂掉，先打印出来
        print("⚠️ DB init failed:", e)

def get_auth_db_conn():
    """
    Auth prefers PostgreSQL, then falls back to a local SQLite file so login/register
    still work on machines without a running PostgreSQL service.
    """
    try:
        return get_db_conn(), "postgres"
    except Exception as e:
        print(f"Auth DB fallback to SQLite: {e}")
        conn = sqlite3.connect(AUTH_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=OFF;")
        conn.execute("PRAGMA synchronous=OFF;")
        return conn, "sqlite"


def init_auth_db():
    conn, db_kind = get_auth_db_conn()
    cur = conn.cursor()
    if db_kind == "sqlite":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL UNIQUE,
                email           TEXT NOT NULL UNIQUE,
                password_hash   TEXT NOT NULL,
                public_user_id  TEXT NOT NULL UNIQUE,
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id              SERIAL PRIMARY KEY,
                username        TEXT NOT NULL UNIQUE,
                email           TEXT NOT NULL UNIQUE,
                password_hash   TEXT NOT NULL,
                public_user_id  TEXT NOT NULL UNIQUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
    conn.commit()
    cur.close()
    conn.close()


def is_unique_violation(exc):
    return isinstance(exc, psycopg2.errors.UniqueViolation) or isinstance(exc, sqlite3.IntegrityError)


app = Flask(__name__)
# 用于 Flask session（建议在服务器上用环境变量改成更安全的值）
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
init_db()
init_auth_db()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PAST_EXAM_UPLOAD_FOLDER, exist_ok=True)

# 一个进程内的缓存：每个 user_id 对应一个 RagAgent 实例






# ---------------- 用户 & Agent 工具函数 ----------------

def get_current_user_id() -> str:
    """
    基于 Flask session 给每个浏览器分配一个稳定的 user_id。
    注意：同一个浏览器 + 不清 cookie 的情况下，user_id 会保持不变。
    """
    if session.get("auth_user_id"):
        return session["auth_user_id"]
    if "user_id" not in session:
        session["user_id"] = f"user_{uuid.uuid4().hex[:8]}"
    return session["user_id"]


def current_auth_payload():
    username = session.get("username")
    if not username:
        return {"authenticated": False, "username": None}
    return {"authenticated": True, "username": username}


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_auth_payload(username: str, email: str | None, password: str):
    if not re.fullmatch(r"[a-zA-Z]{3,32}", username or ""):
        return "Username must be 3-32 characters and can only contain uppercase or lowercase letters."
    if email is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""):
        return "Please enter a valid email address."
    if len(password or "") < 6:
        return "Password must be at least 6 characters."
    return None

def save_round_to_db(user_id: str, round_score, all_items):
    """
    把「一轮测试」的数据写入数据库：
    - user_rounds：一行
    - user_answers：多行（每道题一行）
    all_items 的格式在前端构造（见下面 app.js 修改）
    """
    if not all_items:
        return

    # 统计 correct / partial / wrong 数量
    verdicts = [ (item.get("verdict") or "unknown") for item in all_items ]
    counter = Counter(verdicts)

    total = len(all_items)
    correct = counter.get("correct", 0)
    partial = counter.get("partial", 0)
    wrong = counter.get("wrong", 0)

    conn = get_db_conn()
    cur = conn.cursor()

    # 插入一条 user_rounds 记录
    cur.execute(
        """
        INSERT INTO user_rounds
            (user_id, round_score, total_questions, correct_count, partial_count, wrong_count)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (user_id, round_score, total, correct, partial, wrong)
    )
    round_id = cur.fetchone()[0]

    # 插入每一道题的记录
    for item in all_items:
        cur.execute(
            """
            INSERT INTO user_answers
                (round_id, user_id, question_index, question_type, verdict,
                 question_text, student_answer, evaluation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                round_id,
                user_id,
                item.get("index"),
                item.get("question_type"),
                item.get("verdict"),
                item.get("question") or "",
                item.get("student_answer") or "",
                item.get("evaluation") or "",
            )
        )

    conn.commit()
    cur.close()
    conn.close()

def save_chat_pair(
    user_id: str,
    conv_type: str,
    user_message: str,
    assistant_message: str,
    question_index=None,
):
    """
    把「一问一答」这一轮对话（用户 + AI 各一句）写入 chat_messages 表。
    """
    if not user_message and not assistant_message:
        return

    conn = get_db_conn()
    cur = conn.cursor()

    # 插入用户这一句
    if user_message:
        cur.execute(
            """
            INSERT INTO chat_messages
                (user_id, conv_type, question_index, role, content)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (user_id, conv_type, question_index, "user", user_message),
        )

    # 插入 AI 的这一句
    if assistant_message:
        cur.execute(
            """
            INSERT INTO chat_messages
                (user_id, conv_type, question_index, role, content)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (user_id, conv_type, question_index, "assistant", assistant_message),
        )

    conn.commit()
    cur.close()
    conn.close()

def get_user_material_folder() -> str:
    """
    当前用户专属的资料目录，例如：
    materials/user_a1b2c3d4/
    """
    user_id = get_current_user_id()
    folder = os.path.join(UPLOAD_FOLDER, user_id)
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_past_exam_folder() -> str:
    """
    当前用户专属的“过往试卷文件上传目录”，例如：
    exam_db/past_exam_files/user_a1b2c3d4/
    """
    user_id = get_current_user_id()
    folder = os.path.join(PAST_EXAM_UPLOAD_FOLDER, user_id)
    os.makedirs(folder, exist_ok=True)
    return folder


def get_user_exam_db_path() -> str:
    """
    当前用户专属的“过往试卷题库 JSON 文件路径”，例如：
    exam_db/past_exam_db/user_a1b2c3d4_past_exams.json
    """
    user_id = get_current_user_id()
    # 在 exam_db 下专门建一个 past_exam_db 存每个学生的题库
    exam_db_dir = os.path.join(BASE_DIR, "exam_db", "past_exam_db")
    os.makedirs(exam_db_dir, exist_ok=True)
    return os.path.join(exam_db_dir, f"{user_id}_past_exams.json")


def get_rag_agent_for_current_user():
    """
    不再使用进程内 _USER_AGENTS 缓存。
    每次请求都基于当前 session 的 user_id 创建一个新的 RagAgent，
    然后按该 user_id 从磁盘加载当前用户自己的向量库。
    """
    user_id = get_current_user_id()
    exam_db_path = get_user_exam_db_path()

    agent = rag_agent_module.RagAgent(
        client=rag_agent_module.client,
        db=None,  # 每次请求从空开始，随后尝试加载当前用户自己的库
        serpapi_key=rag_agent_module.serpapi_key,
        exam_db_path=exam_db_path
    )

    try:
        agent.ensure_db_loaded(user_id=user_id)
    except Exception as e:
        print(f"⚠️ ensure_db_loaded 失败（user_id={user_id}）：{e}")

    return agent



# ---------------- 工具函数 ----------------
def get_material_files() -> List[str]:
    """只返回【当前用户】的资料文件列表。"""
    folder = get_user_material_folder()
    files: List[str] = []
    for root, _, filenames in os.walk(folder):
        for name in filenames:
            files.append(os.path.join(root, name))
    return files


def call_local_model(
    query: str,
    question_type: str,
    num_questions: int,
    selected_docs: List[str] | None = None,
    selected_exam_ids: List[int] | None = None,
) -> str:
    """
    现在不再查文献，而是根据本地 materials 中上传的资料出期末复习题。
    selected_docs：前端勾选的文件名列表（如 ["Lecture3.pdf", "Lecture4.pptx"]）
    selected_exam_ids：前端在“过往试卷题库”中勾选的题目 id 列表
    """
    print(
        f"📝 [Router] Generate exam questions: "
        f"type={question_type}, num={num_questions}, "
        f"selected_docs={selected_docs}, selected_exam_ids={selected_exam_ids}"
    )
    agent = get_rag_agent_for_current_user()
    return agent.generate_questions(
        query=query,
        question_type=question_type,
        num_questions=num_questions,
        selected_docs=selected_docs or [],
        selected_exam_ids=selected_exam_ids or None,
    )





# ---------------- 路由 ----------------
@app.route("/")
def index():
    return render_template("index.html", auth=current_auth_payload())


@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    return jsonify({"ok": True, **current_auth_payload()})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(force=True) or {}
    username = normalize_username(data.get("username"))
    email = normalize_email(data.get("email"))
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    validation_error = validate_auth_payload(username, email, password)
    if validation_error:
        return jsonify({"ok": False, "msg": validation_error}), 400
    if password != confirm_password:
        return jsonify({"ok": False, "msg": "Passwords do not match."}), 400

    public_user_id = f"user_{uuid.uuid4().hex[:8]}"
    password_hash = generate_password_hash(password)

    try:
        conn, db_kind = get_auth_db_conn()
        cur = conn.cursor()
        if db_kind == "sqlite":
            cur.execute(
                """
                INSERT INTO app_users (username, email, password_hash, public_user_id)
                VALUES (?, ?, ?, ?);
                """,
                (username, email, password_hash, public_user_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO app_users (username, email, password_hash, public_user_id)
                VALUES (%s, %s, %s, %s)
                RETURNING public_user_id;
                """,
                (username, email, password_hash, public_user_id),
            )
            public_user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        if is_unique_violation(e):
            return jsonify({"ok": False, "msg": "Username or email already exists."}), 409
        return jsonify({"ok": False, "msg": str(e)}), 500

    session.clear()
    session["auth_user_id"] = public_user_id
    session["username"] = username
    return jsonify({"ok": True, "username": username})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(force=True) or {}
    username = normalize_username(data.get("username"))
    password = data.get("password") or ""

    validation_error = validate_auth_payload(username, None, password)
    if validation_error:
        return jsonify({"ok": False, "msg": validation_error}), 400

    try:
        conn, db_kind = get_auth_db_conn()
        cur = conn.cursor()
        placeholder = "?" if db_kind == "sqlite" else "%s"
        cur.execute(
            f"""
            SELECT username, password_hash, public_user_id
            FROM app_users
            WHERE username = {placeholder};
            """,
            (username,),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

    if not user or not check_password_hash(user[1], password):
        return jsonify({"ok": False, "msg": "Invalid username or password."}), 401

    session.clear()
    session["username"] = user[0]
    session["auth_user_id"] = user[2]
    return jsonify({"ok": True, "username": user[0]})


@app.route("/api/auth/guest", methods=["POST"])
def auth_guest():
    session.pop("username", None)
    session.pop("auth_user_id", None)
    session["guest_mode"] = True
    get_current_user_id()
    return jsonify({"ok": True, "guest": True})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/material_stats", methods=["GET"])
def material_stats():
    files = get_material_files()
    # 只把文件名暴露给前端，不带完整路径
    simple_files = [os.path.basename(f) for f in files]
    simple_files.sort()
    return jsonify({
        "ok": True,
        "total_files": len(simple_files),
        "files": simple_files,
    })


# @app.route("/api/upload", methods=["POST"])
# def upload():
#     if "files" not in request.files:
#         return jsonify({"ok": False, "msg": "没有收到文件"}), 400
#
#     files = request.files.getlist("files")
#     saved = []
#
#     # 当前用户的专属资料目录
#     user_folder = get_user_material_folder()
#
#     for f in files:
#         if f.filename == "":
#             continue
#         filename = secure_filename(f.filename)
#         save_path = os.path.join(user_folder, filename)
#         f.save(save_path)
#         saved.append(filename)
#
#     # ⭐ 上传完成后，只重建“当前用户”的向量数据库
#     try:
#         agent = get_rag_agent_for_current_user()
#         rebuild_msg = agent.ingest_material(user_folder)
#     except Exception as e:
#         rebuild_msg = f"知识库更新失败：{e}"
#
#     return jsonify({
#         "ok": True,
#         "saved": saved,
#         "total_files": len(get_material_files()),  # 此时已经是“当前用户”的总数
#         "msg": rebuild_msg,
#     })
@app.route("/api/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"ok": False, "msg": "没有收到文件"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"ok": False, "msg": "文件列表为空"}), 400

    saved = []
    user_folder = get_user_material_folder()

    for f in files:
        if f.filename == "":
            continue
        filename = secure_filename(f.filename)
        if not filename:
            continue
        save_path = os.path.join(user_folder, filename)
        f.save(save_path)
        saved.append(filename)

    if not saved:
        return jsonify({"ok": False, "msg": "没有有效文件被保存"}), 400

    try:
        agent = get_rag_agent_for_current_user()
        rebuild_msg = agent.ingest_material(user_folder)
    except Exception as e:
        return jsonify({
            "ok": False,
            "saved": saved,
            "total_files": len(get_material_files()),
            "msg": f"知识库更新失败：{e}",
        }), 500

    # 根据 ingest_material 的返回信息判断状态
    if rebuild_msg.startswith("⚠️ 当前用户的知识库正在构建中"):
        return jsonify({
            "ok": False,
            "saved": saved,
            "total_files": len(get_material_files()),
            "msg": rebuild_msg,
        }), 409

    if rebuild_msg.startswith("❌") or rebuild_msg.startswith("⚠️"):
        return jsonify({
            "ok": False,
            "saved": saved,
            "total_files": len(get_material_files()),
            "msg": rebuild_msg,
        }), 400

    return jsonify({
        "ok": True,
        "saved": saved,
        "total_files": len(get_material_files()),
        "msg": rebuild_msg,
    })


@app.route("/api/material/delete", methods=["POST"])
def delete_material():
    """
    删除知识库中的某一个文件：
    前端传入 { "filename": "CAN201_-_Lecture_1_v2025.pdf" }
    这里根据文件名在 materials/ 目录下找到并删除，
    然后重新统计剩余文件，并重建向量知识库。
    """
    data = request.get_json(force=True) or {}
    filename = (data.get("filename") or "").strip()
    if not filename:
        return jsonify({"ok": False, "msg": "缺少 filename"}), 400

    # 在 materials/ 下寻找同名文件
    all_files = get_material_files()
    target_paths = [f for f in all_files if os.path.basename(f) == filename]

    if not target_paths:
        return jsonify({"ok": False, "msg": f"未找到文件：{filename}"}), 404

    deleted = []
    errors = []
    for path in target_paths:
        try:
            os.remove(path)
            deleted.append(os.path.basename(path))
        except OSError as e:
            errors.append(str(e))

    # 删除后重新构建【当前用户】的向量库（如果还有剩余文件）
    try:
        remaining = get_material_files()
        user_folder = get_user_material_folder()
        if remaining:
            agent = get_rag_agent_for_current_user()
            rebuild_msg = agent.ingest_material(user_folder)
        else:
            rebuild_msg = "知识库已清空。"
            # 如果以后你实现了 clear_db()，也可以在这里调用
    except Exception as e:
        rebuild_msg = f"知识库重建失败：{e}"

    # 把最新的文件列表返回给前端
    remaining_files = [os.path.basename(f) for f in get_material_files()]
    remaining_files.sort()

    return jsonify({
        "ok": True,
        "deleted": deleted,
        "errors": errors,
        "total_files": len(remaining_files),
        "files": remaining_files,
        "msg": rebuild_msg,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    # 前端发送过来的题型 / 数量 / 勾选文献 / 勾选的过往试卷题目
    question_type = data.get("question_type", "fill_blank")
    num_questions = data.get("num_questions", 5)

    # 保证一定是 list，而不是 None
    selected_docs = data.get("selected_docs", []) or []
    selected_exam_ids = data.get("selected_past_exam_ids", []) or []

    # ⭐ 新增：如果没有勾选任何资料 + 没勾选任何过往试卷题目 → 后端直接拒绝出题
    if not selected_docs and not selected_exam_ids:
        return jsonify({
            "ok": False,
            "msg": "当前没有勾选任何资料或过往试卷题目，请先勾选后再点击“生成试题”。",
        }), 400

    reply = call_local_model(
        user_message,
        question_type=question_type,
        num_questions=num_questions,
        selected_docs=selected_docs,
        selected_exam_ids=selected_exam_ids,
    )

    # ⭐ 新增：把这次「生成试题」对话写入数据库
    try:
        user_id = get_current_user_id()
        save_chat_pair(
            user_id=user_id,
            conv_type="chat",  # 或者起名 "generate_questions"
            user_message=user_message,
            assistant_message=reply,
            question_index=None,
        )
    except Exception as e:
        print("⚠️ save_chat_pair failed in /api/chat:", e)

    return jsonify({"ok": True, "reply": reply})


@app.route("/api/qa", methods=["POST"])
def qa():
    """
    回答学生针对当前生成的试题 + 已勾选文献提出的问题。
    """
    data = request.get_json(force=True) or {}
    user_message = (data.get("message") or "").strip()
    questions = data.get("questions") or []
    current_index = data.get("current_index")
    selected_docs = data.get("selected_docs") or []

    if not user_message:
        return jsonify({"ok": False, "msg": "提问内容不能为空"}), 400

    try:
        agent = get_rag_agent_for_current_user()
        reply = agent.answer_exam_question(
            user_message=user_message,
            questions=questions,
            current_index=current_index,
            selected_docs=selected_docs,
        )

        # ⭐ 新增：记录「本题进一步提问 / 情景迁移提问」的对话
        try:
            user_id = get_current_user_id()
            save_chat_pair(
                user_id=user_id,
                conv_type="exam_qa",  # 所有 /api/qa 的对话统一归为 exam_qa
                user_message=user_message,
                assistant_message=reply,
                question_index=current_index,  # 哪一道题的问题
            )
        except Exception as e2:
            print("⚠️ save_chat_pair failed in /api/qa:", e2)

        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/grade", methods=["POST"])
def grade():
    """
    批改单道试题：
    前端传入 question（题干）、answer（学生作答）、question_type、selected_docs
    """
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    question_type = data.get("question_type", "short_answer")
    selected_docs = data.get("selected_docs", [])

    if not question or not answer:
        return jsonify({"ok": False, "msg": "题干或作答内容为空，无法批改。"}), 400

    try:
        agent = get_rag_agent_for_current_user()
        result_text = agent.grade_answer(
            question=question,
            student_answer=answer,
            question_type=question_type,
            selected_docs=selected_docs,
        )
        return jsonify({"ok": True, "result": result_text})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/explain_detailed", methods=["POST"])
def explain_detailed():
    """
    精讲模式：
    学生点击 "I don't understand" 后，针对当前试题给出更详细的知识点讲解。
    """
    data = request.get_json(force=True) or {}

    question = (data.get("question") or "").strip()
    student_answer = (data.get("answer") or "").strip()
    feedback = (data.get("feedback") or "").strip()
    question_type = data.get("question_type") or "short_answer"
    selected_docs = data.get("selected_docs") or []

    if not question:
        return jsonify({"ok": False, "msg": "题干为空，无法进入精讲模式。"}), 400

    try:
        agent = get_rag_agent_for_current_user()
        explanation = agent.explain_question_detailed(
            question=question,
            student_answer=student_answer,
            feedback=feedback,
            question_type=question_type,
            selected_docs=selected_docs,
        )
        return jsonify({"ok": True, "explanation": explanation})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/exam_feedback", methods=["POST"])
def exam_feedback():
    data = request.get_json(silent=True) or {}
    wrong_items = data.get("wrong_items") or []

    # ⭐ 新增：前端传来的本轮所有题目 & 得分
    all_items = data.get("all_items") or []
    round_score = data.get("round_score")

    # ⭐ 新增：把本轮答题记录写入数据库（异常不影响原功能）
    try:
        user_id = get_current_user_id()
        save_round_to_db(user_id=user_id, round_score=round_score, all_items=all_items)
    except Exception as e:
        print("⚠️ save_round_to_db failed:", e)

    # ✅ 保持原来的个性化反馈逻辑
    try:
        agent = get_rag_agent_for_current_user()
        feedback_text = agent.summarize_wrong_questions(wrong_items)
        return jsonify({"ok": True, "feedback": feedback_text})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/scenario_question", methods=["POST"])
def scenario_question():
    """
    基于某一道错误试题，生成一题“情景迁移”练习题。
    前端会传入：
        - question        原始题干
        - student_answer  学生原始作答
        - feedback        批改反馈（包括错误原因/参考答案等）
        - question_type   题型
        - selected_docs   前端勾选的材料文件名列表
    """
    data = request.get_json(force=True) or {}
    question = data.get("question") or ""
    student_answer = data.get("student_answer") or ""
    feedback = data.get("feedback") or ""
    question_type = data.get("question_type") or "short_answer"
    selected_docs = data.get("selected_docs") or []

    try:
        agent = get_rag_agent_for_current_user()
        new_question = agent.generate_scenario_question(
            question=question,
            student_answer=student_answer,
            feedback=feedback,
            question_type=question_type,
            selected_docs=selected_docs,
        )
        return jsonify({"ok": True, "scenario_question": new_question})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500



@app.route("/api/feedback", methods=["GET"])
def feedback():
    try:
        agent = get_rag_agent_for_current_user()
        reply = agent.summarize_learning()
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@app.route("/api/past_exam/list", methods=["GET"])
def past_exam_list():
    """
    列出当前所有“过往试卷题目”。
    """
    try:
        agent = get_rag_agent_for_current_user()
        data = agent.list_past_exam_questions()
        return jsonify({"ok": True, "questions": data})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/past_exam/upload", methods=["POST"])
def past_exam_upload():
    """
    上传任意类型的试卷文件，并自动从中抽取题目，写入 exam_db/past_exams.json。
    前端通过 FormData(files=...) 传文件。
    返回值：
    {
      "ok": true,
      "saved_files": ["xxx.pdf", "yyy.docx", ...],
      "imported_count": 10,
      "questions": [ ... 当前完整题库 ... ]
    }
    """
    if "files" not in request.files:
        return jsonify({"ok": False, "msg": "没有收到文件"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"ok": False, "msg": "文件列表为空"}), 400

    saved_files = []
    imported_questions = []

    # ★ 当前用户自己的“过往试卷文件”目录
    user_exam_folder = get_user_past_exam_folder()

    for f in files:
        if f.filename == "":
            continue

        filename = secure_filename(f.filename)
        save_path = os.path.join(user_exam_folder, filename)  # ★ 关键修改
        f.save(save_path)
        saved_files.append(filename)

        # 调 RagAgent 解析题目（内部会写入“该用户自己的 JSON 题库”）
        try:
            agent = get_rag_agent_for_current_user()
            new_items = agent.import_past_exam_from_file(save_path)
            imported_questions.extend(new_items)
        except Exception as e:
            print(f"⚠️ 从文件 {filename} 解析试卷题目失败: {e}")

    # 返回当前完整题库，方便前端覆盖本地缓存
    agent = get_rag_agent_for_current_user()
    all_questions = agent.list_past_exam_questions()
    return jsonify({
        "ok": True,
        "saved_files": saved_files,
        "imported_count": len(imported_questions),
        "questions": all_questions,
    })



@app.route("/api/past_exam/add", methods=["POST"])
def past_exam_add():
    """
    往题库中加入一道过往试卷题目。
    请求体 JSON 示例：
    {
      "question": "Explain the difference between circuit switching and packet switching.",
      "question_type": "short_answer",
      "meta": {
        "year": "2024",
        "paper": "期末卷A"
      }
    }
    """
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    question_type = (data.get("question_type") or "short_answer").strip()
    meta = data.get("meta") or {}

    if not question:
        return jsonify({"ok": False, "msg": "question 不能为空"}), 400

    try:
        agent = get_rag_agent_for_current_user()
        record = agent.add_past_exam_question(
            question_text=question,
            question_type=question_type,
            meta=meta if isinstance(meta, dict) else {},
        )
        return jsonify({"ok": True, "record": record})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/past_exam/delete", methods=["POST"])
def past_exam_delete():
    """
    删除题库中的题目。
    可以按 id 删，也可以按完整题干删，示例：

    按 id 删：
    { "id": 3 }

    按题干删：
    { "question": "Explain the difference between ..." }
    """
    data = request.get_json(force=True) or {}
    qid = data.get("id")
    question_text = data.get("question")

    if qid is None and not question_text:
        return jsonify({"ok": False, "msg": "必须提供 id 或 question"}), 400

    try:
        agent = get_rag_agent_for_current_user()
        deleted = agent.delete_past_exam_question(
            question_id=qid,
            question_text=question_text,
        )
        return jsonify({"ok": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500



@app.route("/api/kb_status", methods=["GET"])
def kb_status():
    """
    返回当前用户的 KB 状态：
    - ready: 向量库是否已经就绪，且至少有一个文本块
    - total_files: 该用户 materials 目录下的文件数量
    - files: 文件名列表（给前端渲染）
    """
    files = get_material_files()
    simple_files = [os.path.basename(f) for f in files]
    simple_files.sort()

    ready = False
    try:
        agent = get_rag_agent_for_current_user()
        db = getattr(agent, "db", None)

        if db is not None:
            # 优先用 FAISS 的 index.ntotal
            if hasattr(db, "index") and hasattr(db.index, "ntotal"):
                ready = db.index.ntotal > 0
            # 兼容旧版本：看 docstore 里有没有内容
            elif hasattr(db, "docstore") and hasattr(db.docstore, "_dict"):
                ready = len(getattr(db.docstore, "_dict", {})) > 0
    except Exception as e:
        print(f"⚠️ kb_status 检查向量库时出错: {e}")
        ready = False

    # 只有同时「有文件」且「向量库非空」才算 ready
    ready = bool(ready) and len(simple_files) > 0

    return jsonify({
        "ok": True,
        "ready": ready,
        "total_files": len(simple_files),
        "files": simple_files,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
