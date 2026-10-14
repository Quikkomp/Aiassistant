"""Published training exams: immutable snapshots and server-owned single attempts."""
import json
import math
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


class ExamError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ExamError("内容为空或超过长度限制。")
    return value.strip()


def clean_questions(items):
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        raise ExamError("考试应包含 1–50 道题。")
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise ExamError("题目格式无效。")
        points = item.get("points", 1)
        if isinstance(points, bool) or not isinstance(points, (int, float)) or not math.isfinite(points) or not 0 < points <= 100:
            raise ExamError("每题分值应大于 0 且不超过 100。")
        kind = item.get("type", "short_answer")
        if kind not in {"fill_blank", "multiple_choice", "short_answer"}:
            raise ExamError("题型无效。")
        result.append({"text": text(item.get("text"), 16000, True), "type": kind,
                       "points": float(points), "answer": text(item.get("answer", ""), 8000),
                       "explanation": text(item.get("explanation", ""), 12000),
                       "rubric": text(item.get("rubric", ""), 8000),
                       "knowledge": text(item.get("knowledge", ""), 500)})
    return result


class ExamStore:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS exams (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, owner_name TEXT NOT NULL,
                    bank_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft', questions TEXT NOT NULL, settings TEXT NOT NULL,
                    token TEXT UNIQUE, version INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS exams_owner ON exams(owner, created_at);
                CREATE TABLE IF NOT EXISTS exam_attempts (
                    id TEXT PRIMARY KEY, exam_id TEXT NOT NULL, user_id TEXT NOT NULL, username TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active', report TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL, completed_at TEXT, UNIQUE(exam_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS exam_answers (
                    attempt_id TEXT NOT NULL, idx INTEGER NOT NULL, answer TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending', ratio REAL, feedback TEXT,
                    claim TEXT, claimed_at TEXT, understanding TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(attempt_id, idx)
                );
                CREATE TABLE IF NOT EXISTS exam_support (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id TEXT NOT NULL,
                    idx INTEGER NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL, response TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS study_groups (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, owner_name TEXT NOT NULL,
                    name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                    token TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id TEXT NOT NULL, user_id TEXT NOT NULL, username TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active', joined_at TEXT NOT NULL,
                    PRIMARY KEY(group_id,user_id)
                );
                CREATE TABLE IF NOT EXISTS group_exams (
                    group_id TEXT NOT NULL, exam_id TEXT NOT NULL, published_at TEXT NOT NULL,
                    PRIMARY KEY(group_id,exam_id)
                );
                CREATE TABLE IF NOT EXISTS exam_assignments (
                    group_id TEXT NOT NULL, exam_id TEXT NOT NULL, user_id TEXT NOT NULL,
                    assigned_at TEXT NOT NULL, PRIMARY KEY(group_id,exam_id,user_id)
                );
                CREATE INDEX IF NOT EXISTS assignments_user ON exam_assignments(user_id,assigned_at);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            raise ExamError("考试不存在或无权访问。", 404)
        obj = dict(row)
        obj["questions"] = json.loads(obj["questions"])
        obj["settings"] = json.loads(obj["settings"])
        return obj

    def owned(self, exam_id, user):
        with self.connect() as db:
            return self.decode(db.execute("SELECT * FROM exams WHERE id=? AND owner=?", (exam_id, user)).fetchone())

    def create(self, user, username, bank):
        import re
        questions = []
        for i, raw in enumerate(bank["questions"]):
            match = re.search(r"\[(fill_blank|multiple_choice|short_answer)\]", raw)
            questions.append({"text": raw, "type": match.group(1) if match else "short_answer",
                              "points": round(100 / len(bank["questions"]), 2) if i < len(bank["questions"]) - 1 else round(100 - round(100 / len(bank["questions"]), 2) * i, 2),
                              "answer": "", "explanation": "", "rubric": "", "knowledge": ""})
        questions = clean_questions(questions)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT id FROM exams WHERE owner=? AND bank_id=? AND status='draft'", (user, bank["id"])).fetchone()
            if existing:
                exam_id = existing["id"]
            else:
                exam_id = secrets.token_hex(16)
                db.execute("INSERT INTO exams(id,owner,owner_name,bank_id,title,questions,settings,created_at) VALUES(?,?,?,?,?,?,?,?)",
                           (exam_id, user, username, bank["id"], bank["title"], json.dumps(questions, ensure_ascii=False),
                            json.dumps(bank.get("settings", {}), ensure_ascii=False), now()))
        return self.owned(exam_id, user)

    def save(self, exam_id, user, data):
        questions = clean_questions(data.get("questions"))
        title = text(data.get("title"), 100, True)
        description = text(data.get("description", ""), 2000)
        exam = self.owned(exam_id, user)
        if exam["status"] != "draft":
            raise ExamError("已发布的试卷不可修改，请从题库新建一场考试。", 409)
        with self.connect() as db:
            updated = db.execute("UPDATE exams SET title=?,description=?,questions=?,version=version+1 WHERE id=? AND owner=? AND status='draft' AND version=?",
                                 (title, description, json.dumps(questions, ensure_ascii=False), exam_id, user, data.get("version"))).rowcount
        if not updated:
            raise ExamError("草稿已更新，请重新打开后编辑。", 409)
        return self.owned(exam_id, user)

    def publish(self, exam_id, user, version):
        exam = self.owned(exam_id, user)
        if exam["status"] != "draft":
            return exam
        if any(not q["answer"] or not q["explanation"] or not q["rubric"] for q in exam["questions"]):
            raise ExamError("请审核并填写每题的参考答案、解析和评分要点后发布。")
        with self.connect() as db:
            changed = db.execute("UPDATE exams SET status='published',token=?,version=version+1 WHERE id=? AND owner=? AND status='draft' AND version=?",
                                 (secrets.token_hex(24), exam_id, user, version)).rowcount
        if not changed:
            raise ExamError("草稿发生变化，请重新审核后发布。", 409)
        return self.owned(exam_id, user)

    def close(self, exam_id, user):
        self.owned(exam_id, user)
        with self.connect() as db:
            db.execute("UPDATE exams SET status='closed' WHERE id=? AND owner=? AND status='published'", (exam_id, user))
        return self.owned(exam_id, user)

    def catalog(self, user):
        from collections import defaultdict
        with self.connect() as db:
            db.execute("BEGIN")
            owned = [dict(r) for r in db.execute("SELECT id,title,status,token,created_at,questions FROM exams WHERE owner=? ORDER BY created_at DESC LIMIT 200", (user,))]
            attempts = db.execute("SELECT id,exam_id,status FROM exam_attempts WHERE exam_id IN (SELECT id FROM exams WHERE owner=? ORDER BY created_at DESC LIMIT 200)", (user,)).fetchall()
            answers = db.execute("SELECT s.attempt_id,s.idx,s.ratio FROM exam_answers s JOIN exam_attempts a ON a.id=s.attempt_id WHERE s.status='graded' AND a.exam_id IN (SELECT id FROM exams WHERE owner=? ORDER BY created_at DESC LIMIT 200)", (user,)).fetchall()
            joined = db.execute("SELECT a.id,a.status,e.title,e.token,e.owner_name FROM exam_attempts a JOIN exams e ON a.exam_id=e.id WHERE a.user_id=? ORDER BY a.started_at DESC LIMIT 200", (user,)).fetchall()
            assigned = db.execute("""SELECT e.id,e.title,e.token,e.owner_name,e.status AS exam_status,
                g.name AS group_name,x.assigned_at FROM exam_assignments x
                JOIN exams e ON e.id=x.exam_id JOIN study_groups g ON g.id=x.group_id
                JOIN group_members m ON m.group_id=x.group_id AND m.user_id=x.user_id AND m.status='active'
                WHERE x.user_id=? AND NOT EXISTS (
                    SELECT 1 FROM exam_attempts a WHERE a.exam_id=x.exam_id AND a.user_id=x.user_id
                ) ORDER BY x.assigned_at DESC""", (user,)).fetchall()
        by_exam, by_attempt = defaultdict(list), defaultdict(list)
        for attempt in attempts:
            by_exam[attempt["exam_id"]].append(attempt)
        for answer in answers:
            by_attempt[answer["attempt_id"]].append(answer)
        for exam in owned:
            questions = json.loads(exam.pop("questions"))
            total = sum(q["points"] for q in questions)
            participants = by_exam[exam["id"]]
            scores = [round(sum(a["ratio"] * questions[a["idx"]]["points"] for a in by_attempt[p["id"]]) / total * 100, 6) for p in participants if p["status"] == "completed"]
            exam.update(question_count=len(questions), started=len(participants), completed=len(scores),
                        graded_count=sum(len(by_attempt[p["id"]]) for p in participants),
                        average=round(sum(scores) / len(scores), 1) if scores else None)
        pending = {}
        for row in assigned:
            if row['id'] not in pending:
                pending[row['id']] = {**dict(row), 'status': 'assigned', 'group_names': []}
            if row['group_name'] not in pending[row['id']]['group_names']:
                pending[row['id']]['group_names'].append(row['group_name'])
        return {"owned": owned, "joined": list(pending.values()) + [dict(r) for r in joined]}

    def shared(self, token):
        with self.connect() as db:
            return self.decode(db.execute("SELECT * FROM exams WHERE token=? AND status IN ('published','closed')", (token,)).fetchone())

    def overview(self, token, user):
        exam = self.shared(token)
        with self.connect() as db:
            attempt = db.execute("SELECT id,status FROM exam_attempts WHERE exam_id=? AND user_id=?", (exam["id"], user)).fetchone()
        return {"title": exam["title"], "description": exam["description"], "teacher": exam["owner_name"],
                "count": len(exam["questions"]), "total": sum(q["points"] for q in exam["questions"]),
                "status": exam["status"], "attempt": dict(attempt) if attempt else None}

    def start(self, token, user, username):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            exam = self.decode(db.execute("SELECT * FROM exams WHERE token=?", (token,)).fetchone())
            attempt = db.execute("SELECT id FROM exam_attempts WHERE exam_id=? AND user_id=?", (exam["id"], user)).fetchone()
            if attempt:
                attempt_id = attempt["id"]
            elif exam["status"] == "published":
                attempt_id = secrets.token_hex(16)
                db.execute("INSERT INTO exam_attempts(id,exam_id,user_id,username,started_at) VALUES(?,?,?,?,?)", (attempt_id, exam["id"], user, username, now()))
            else:
                raise ExamError("考试已关闭，不能再开始新的作答。", 409)
        return self.packet(attempt_id, user)

    def attempt(self, attempt_id, user):
        with self.connect() as db:
            row = db.execute("SELECT * FROM exam_attempts WHERE id=? AND user_id=?", (attempt_id, user)).fetchone()
            if row is None:
                raise ExamError("作答记录不存在或无权访问。", 404)
            exam = self.decode(db.execute("SELECT * FROM exams WHERE id=?", (row["exam_id"],)).fetchone())
            answers = [dict(r) for r in db.execute("SELECT * FROM exam_answers WHERE attempt_id=? ORDER BY idx", (attempt_id,))]
        return dict(row), exam, answers

    def packet(self, attempt_id, user):
        attempt, exam, answers = self.attempt(attempt_id, user)
        by_index = {a["idx"]: a for a in answers}
        questions = []
        for i, q in enumerate(exam["questions"]):
            public = {k: q[k] for k in ("text", "type", "points")}
            a = by_index.get(i)
            if a:
                public["submission"] = {k: a[k] for k in ("answer", "status", "ratio", "feedback", "understanding")}
                if a["status"] == "graded":
                    public.update({k: q[k] for k in ("answer", "explanation", "knowledge")})
                    public["support"] = self.support_history(attempt_id, i)
            questions.append(public)
        score = round(sum((a["ratio"] or 0) * exam["questions"][a["idx"]]["points"] for a in answers), 2)
        return {"id": attempt_id, "title": exam["title"], "status": attempt["status"], "questions": questions,
                "score": score if attempt["status"] == "completed" else None,
                "total": sum(q["points"] for q in exam["questions"]), "report": attempt["report"]}

    def claim_answer(self, attempt_id, user, idx, answer):
        attempt, exam, _ = self.attempt(attempt_id, user)
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(exam["questions"]):
            raise ExamError("题号无效。")
        answer = text(answer, 10000, True)
        claim = secrets.token_hex(16)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            status = db.execute("SELECT status FROM exam_attempts WHERE id=? AND user_id=?", (attempt_id, user)).fetchone()["status"]
            if status != "active":
                raise ExamError("本次考试已完成，不能再次作答。", 409)
            db.execute("INSERT OR IGNORE INTO exam_answers(attempt_id,idx,answer) VALUES(?,?,?)", (attempt_id, idx, answer))
            row = db.execute("SELECT * FROM exam_answers WHERE attempt_id=? AND idx=?", (attempt_id, idx)).fetchone()
            if row["answer"] != answer:
                raise ExamError("这道题已提交，不能修改答案。", 409)
            if row["status"] == "graded":
                return None, exam["questions"][idx]
            updated = db.execute("UPDATE exam_answers SET status='pending',claim=?,claimed_at=? WHERE attempt_id=? AND idx=? AND (claim IS NULL OR julianday(claimed_at)<julianday('now','-2 minutes'))", (claim, now(), attempt_id, idx)).rowcount
            if not updated:
                raise ExamError("正在批改，请稍后刷新查看结果。", 409)
        return claim, exam["questions"][idx]

    def finish_grade(self, attempt_id, idx, claim, ratio, feedback):
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or not 0 <= ratio <= 1:
            raise ExamError("AI 评分格式无效，请重试批改。", 502)
        feedback = text(feedback, 12000, True)
        with self.connect() as db:
            updated = db.execute("UPDATE exam_answers SET status='graded',ratio=?,feedback=?,claim=NULL WHERE attempt_id=? AND idx=? AND claim=?", (ratio, feedback, attempt_id, idx, claim)).rowcount
        if not updated:
            raise ExamError("批改状态已更新，请刷新查看。", 409)

    def fail_grade(self, attempt_id, idx, claim):
        with self.connect() as db:
            db.execute("UPDATE exam_answers SET status='error',claim=NULL WHERE attempt_id=? AND idx=? AND claim=?", (attempt_id, idx, claim))

    def complete(self, attempt_id, user):
        attempt, exam, answers = self.attempt(attempt_id, user)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM exam_answers WHERE attempt_id=? AND status='graded'", (attempt_id,)).fetchone()[0]
            if count != len(exam["questions"]):
                raise ExamError("请完成每道题并等待批改，再查看总成绩。", 409)
            db.execute("UPDATE exam_attempts SET status='completed',completed_at=? WHERE id=? AND user_id=? AND status='active'", (now(), attempt_id, user))
        return self.packet(attempt_id, user)

    def report(self, attempt_id, user, report):
        report = text(report, 16000, True)
        with self.connect() as db:
            db.execute("UPDATE exam_attempts SET report=? WHERE id=? AND user_id=? AND status='completed'", (report, attempt_id, user))

    def understand(self, attempt_id, user, idx, value):
        _, _, answers = self.attempt(attempt_id, user)
        if value not in {"understood", "unclear"} or not any(a["idx"] == idx and a["status"] == "graded" for a in answers):
            raise ExamError("请先完成当前题的批改。")
        with self.connect() as db:
            db.execute("UPDATE exam_answers SET understanding=? WHERE attempt_id=? AND idx=?", (value, attempt_id, idx))

    def submissions(self, exam_id, user):
        exam = self.owned(exam_id, user)
        with self.connect() as db:
            rows = [dict(r) for r in db.execute("SELECT id,username,status,started_at,completed_at FROM exam_attempts WHERE exam_id=? ORDER BY started_at DESC LIMIT 200", (exam_id,))]
            for row in rows:
                answers = db.execute("SELECT idx,ratio FROM exam_answers WHERE attempt_id=? AND status='graded'", (row["id"],)).fetchall()
                row["done"] = len(answers)
                row["score"] = round(sum(a["ratio"] * exam["questions"][a["idx"]]["points"] for a in answers), 2) if row["status"] == "completed" else None
        return rows

    def support_history(self, attempt_id, idx):
        with self.connect() as db:
            rows = db.execute("SELECT kind,message,response FROM exam_support WHERE attempt_id=? AND idx=? ORDER BY id DESC LIMIT 6", (attempt_id, idx)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def analytics(self, exam_id, user, user_ids=None):
        from collections import defaultdict
        from statistics import median
        exam = self.owned(exam_id, user)
        with self.connect() as db:
            attempts = [dict(r) for r in db.execute("SELECT id,user_id,username,status,started_at,completed_at FROM exam_attempts WHERE exam_id=? ORDER BY started_at DESC", (exam_id,))]
            answers = [dict(r) for r in db.execute("SELECT s.attempt_id,s.idx,s.ratio FROM exam_answers s JOIN exam_attempts a ON s.attempt_id=a.id WHERE a.exam_id=? AND s.status='graded'", (exam_id,))]
        if user_ids is not None:
            allowed = set(user_ids)
            attempts = [a for a in attempts if a['user_id'] in allowed]
            attempt_ids = {a['id'] for a in attempts}
            answers = [a for a in answers if a['attempt_id'] in attempt_ids]
        by_attempt = defaultdict(list)
        for answer in answers:
            by_attempt[answer["attempt_id"]].append(answer)
        total = sum(q["points"] for q in exam["questions"])
        scores = []
        per_question = [[] for _ in exam["questions"]]
        groups = defaultdict(list)
        for attempt in attempts:
            graded = by_attempt[attempt["id"]]
            attempt["done"] = len(graded)
            attempt["score"] = None
            if attempt["status"] == "completed":
                score = sum(a["ratio"] * exam["questions"][a["idx"]]["points"] for a in graded)
                attempt["score"] = round(score, 2)
                scores.append(round(score / total * 100, 6))
                for a in graded:
                    per_question[a["idx"]].append(a["ratio"])
                    key = exam["questions"][a["idx"]]["knowledge"] or f"Q{a['idx'] + 1}"
                    groups[key].append(a["ratio"])
        completed, started = len(scores), len(attempts)
        ranges = [(0, 60, "0–59"), (60, 70, "60–69"), (70, 80, "70–79"), (80, 90, "80–89"), (90, 101, "90–100")]
        questions = []
        for i, ratios in enumerate(per_question):
            questions.append({"index": i, "knowledge": exam["questions"][i]["knowledge"], "count": len(ratios),
                              "correct": sum(r == 1 for r in ratios), "partial": sum(0 < r < 1 for r in ratios), "wrong": sum(r == 0 for r in ratios),
                              "correct_rate": round(sum(r == 1 for r in ratios) / len(ratios) * 100, 1) if ratios else None})
        return {"started": started, "completed": completed, "active": started - completed, "total": total, "graded_count": len(answers),
                "completion_rate": round(completed / started * 100, 1) if started else None,
                "average": round(sum(scores) / completed, 1) if completed else None,
                "median": round(median(scores), 1) if completed else None,
                "highest": round(max(scores), 1) if completed else None,
                "lowest": round(min(scores), 1) if completed else None,
                "pass_rate": round(sum(s >= 60 for s in scores) / completed * 100, 1) if completed else None,
                "distribution": [{"label": label, "count": sum(low <= s < high for s in scores)} for low, high, label in ranges],
                "questions": questions,
                "weaknesses": sorted([{"knowledge": name, "mastery": round(sum(ratios) / len(ratios) * 100, 1), "count": len(ratios)} for name, ratios in groups.items() if sum(ratios) / len(ratios) < .8], key=lambda item: item["mastery"]),
                "students": attempts[:200], "roster_limit": 200}

    def save_support(self, attempt_id, idx, kind, message, response):
        response = text(response, 16000, True)
        with self.connect() as db:
            db.execute("INSERT INTO exam_support(attempt_id,idx,kind,message,response) VALUES(?,?,?,?,?)", (attempt_id, idx, kind, message, response))
            db.execute("DELETE FROM exam_support WHERE attempt_id=? AND idx=? AND id NOT IN (SELECT id FROM exam_support WHERE attempt_id=? AND idx=? ORDER BY id DESC LIMIT 12)", (attempt_id, idx, attempt_id, idx))
