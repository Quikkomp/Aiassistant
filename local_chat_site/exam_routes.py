"""Isolated examination API; the existing personal-practice API remains unchanged."""
import os
from io import BytesIO
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, session, render_template, send_file, current_app
from exam_store import ExamStore, ExamError, text
from exam_ai import ExamAI
from account_access import is_teacher, require_teacher


def make_exam_blueprint(store, bank_store, agent_factory, ai=None):
    bp = Blueprint("exams", __name__)
    ai = ai or ExamAI(agent_factory)

    def user():
        return session["auth_user_id"]

    def body():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ExamError("请求格式无效。")
        return data

    def share_url(exam):
        base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/") or request.url_root.rstrip("/")
        if urlparse(base).scheme not in {"http", "https"}:
            raise ExamError("请配置正确的 PUBLIC_BASE_URL。", 500)
        return base + "/exam/" + exam["token"]

    def teacher_packet(exam):
        result = {k: exam[k] for k in ("id", "title", "description", "status", "questions", "version")}
        if exam["token"]:
            result["share_url"] = share_url(exam)
        return result

    @bp.before_request
    def protect():
        if request.endpoint == "exams.page":
            return None
        if not session.get("auth_user_id"):
            return jsonify(ok=False, msg="请先登录账号，考试不支持游客作答。"), 401
        if request.endpoint in {'exams.create', 'exams.draft', 'exams.prepare', 'exams.publish',
                                'exams.close', 'exams.submissions', 'exams.analytics', 'exams.qr', 'exams.review'}:
            require_teacher()
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("Origin")
            allowed = {request.host_url.rstrip("/"), os.getenv("PUBLIC_BASE_URL", "").rstrip("/")}
            if origin and origin.rstrip("/") not in allowed:
                return jsonify(ok=False, msg="请求来源无效。"), 403

    @bp.errorhandler(ExamError)
    def error(exc):
        return jsonify(ok=False, msg=str(exc)), exc.status

    @bp.after_request
    def private(response):
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    @bp.route("/exam/<token>")
    def page(token):
        return render_template("index.html", auth={"authenticated": bool(session.get("auth_user_id")), "username": session.get("username"), 'role': session.get('auth_role')})

    @bp.route("/api/exams")
    def catalog():
        catalog = store.catalog(user())
        if not is_teacher():
            catalog['owned'] = []
        return jsonify(ok=True, role=session.get('auth_role'), **catalog)

    @bp.route('/api/exams/<exam_id>/submissions/<attempt_id>')
    def review(exam_id, attempt_id):
        return jsonify(ok=True, review=store.review(exam_id, user(), attempt_id))

    @bp.route("/api/exams", methods=["POST"])
    def create():
        bank_id = body().get("bank_id")
        bank = next((b for b in bank_store.list(user()) if b["id"] == bank_id), None)
        if not bank:
            raise ExamError("题库不存在或无权访问。", 404)
        return jsonify(ok=True, exam=teacher_packet(store.create(user(), session.get("username", ""), bank)))

    @bp.route("/api/exams/<exam_id>", methods=["GET", "PUT"])
    def draft(exam_id):
        exam = store.save(exam_id, user(), body()) if request.method == "PUT" else store.owned(exam_id, user())
        return jsonify(ok=True, exam=teacher_packet(exam))

    @bp.route("/api/exams/<exam_id>/prepare", methods=["POST"])
    def prepare(exam_id):
        data = body()
        exam = store.owned(exam_id, user())
        idx = data.get("index")
        if exam["status"] != "draft" or data.get("version") != exam["version"]:
            raise ExamError("草稿已更新或已发布，请重新打开。", 409)
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(exam["questions"]):
            raise ExamError("题号无效。")
        try:
            values = ai.prepare(exam["questions"][idx], exam["settings"].get("selected_docs", []))
        except ExamError:
            raise
        except Exception:
            current_app.logger.exception("Exam reference preparation failed")
            raise ExamError("答案生成失败，请重试或手动填写。", 502)
        exam["questions"][idx].update(values)
        return jsonify(ok=True, exam=teacher_packet(store.save(exam_id, user(), exam)))

    @bp.route("/api/exams/<exam_id>/publish", methods=["POST"])
    def publish(exam_id):
        data = body()
        if data.get("reviewed") is not True:
            raise ExamError("请确认已审核答案与解析。")
        return jsonify(ok=True, exam=teacher_packet(store.publish(exam_id, user(), data.get("version"))))

    @bp.route("/api/exams/<exam_id>/close", methods=["POST"])
    def close(exam_id):
        return jsonify(ok=True, exam=teacher_packet(store.close(exam_id, user())))

    @bp.route("/api/exams/<exam_id>/submissions")
    def submissions(exam_id):
        return jsonify(ok=True, submissions=store.submissions(exam_id, user()))

    @bp.route("/api/exams/<exam_id>/analytics")
    def analytics(exam_id):
        return jsonify(ok=True, analytics=store.analytics(exam_id, user()))

    @bp.route("/api/exams/<exam_id>/qr")
    def qr(exam_id):
        exam = store.owned(exam_id, user())
        if not exam["token"]:
            raise ExamError("请先发布考试。")
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderSVG
        code = QrCodeWidget(share_url(exam))
        bounds = code.getBounds()
        size = bounds[2] - bounds[0]
        drawing = Drawing(240, 240, transform=[240 / size, 0, 0, 240 / size, 0, 0])
        drawing.add(code)
        response = send_file(BytesIO(renderSVG.drawToString(drawing).encode("utf-8")), mimetype="image/svg+xml")
        response.headers["Cache-Control"] = "private, no-store"
        return response

    @bp.route("/api/exams/shared/<token>")
    def overview(token):
        return jsonify(ok=True, exam=store.overview(token, user()))

    @bp.route("/api/exams/shared/<token>/start", methods=["POST"])
    def start(token):
        return jsonify(ok=True, attempt=store.start(token, user(), session.get("username", "")))

    @bp.route("/api/exam_attempts/<attempt_id>")
    def packet(attempt_id):
        return jsonify(ok=True, attempt=store.packet(attempt_id, user()))

    @bp.route("/api/exam_attempts/<attempt_id>/answer", methods=["POST"])
    def answer(attempt_id):
        data = body()
        idx, answer_text = data.get("index"), data.get("answer")
        claim, question = store.claim_answer(attempt_id, user(), idx, answer_text)
        if claim:
            try:
                ratio, feedback = ai.grade(question, answer_text)
                store.finish_grade(attempt_id, idx, claim, ratio, feedback)
            except Exception:
                store.fail_grade(attempt_id, idx, claim)
                current_app.logger.exception("Exam grading failed; answer remains locked")
                raise ExamError("答案已锁定，但批改暂时失败。请点击重试批改，不能修改原答案。", 502)
        return jsonify(ok=True, attempt=store.packet(attempt_id, user()))

    @bp.route("/api/exam_attempts/<attempt_id>/complete", methods=["POST"])
    def complete(attempt_id):
        result = store.complete(attempt_id, user())
        return jsonify(ok=True, attempt=result)

    @bp.route("/api/exam_attempts/<attempt_id>/report", methods=["POST"])
    def report(attempt_id):
        attempt, exam, answers = store.attempt(attempt_id, user())
        if attempt["status"] != "completed":
            raise ExamError("请先完成考试。", 409)
        if not attempt["report"]:
            try:
                report_text = ai.report(exam["questions"], answers)
                store.report(attempt_id, user(), report_text)
            except Exception:
                current_app.logger.exception("Exam weakness report failed")
                raise ExamError("成绩已保存，薄弱点讲解生成失败，可稍后重试。", 502)
        return jsonify(ok=True, attempt=store.packet(attempt_id, user()))

    @bp.route("/api/exam_attempts/<attempt_id>/support", methods=["POST"])
    def support(attempt_id):
        data = body()
        idx, kind = data.get("index"), data.get("kind")
        _, exam, answers = store.attempt(attempt_id, user())
        submitted = next((a for a in answers if a["idx"] == idx and a["status"] == "graded"), None)
        if isinstance(idx, bool) or not isinstance(idx, int) or not submitted:
            raise ExamError("请先完成当前题的提交与批改。")
        if kind == "understanding":
            store.understand(attempt_id, user(), idx, data.get("value"))
            return jsonify(ok=True)
        if kind not in {"explain", "ask", "similar"}:
            raise ExamError("操作无效。")
        message = text(data.get("message", ""), 2000, kind == "ask")
        try:
            result = ai.support(exam["questions"][idx], submitted["answer"], submitted["feedback"], kind, message, store.support_history(attempt_id, idx))
            store.save_support(attempt_id, idx, kind, message, result)
        except Exception:
            raise ExamError("学习辅导生成失败，请重试。", 502)
        return jsonify(ok=True, text=result)

    return bp
