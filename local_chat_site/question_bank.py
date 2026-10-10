"""Per-user saved question sets, with transactional capacity reservations."""

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager


LIMIT = 10


def split_questions(reply):
    text = str(reply or "").strip()
    if not text or text.startswith(("⚠", "❌")):
        raise ValueError(text or "没有生成有效题目，请重试。")
    starts = list(re.finditer(r"(?m)^\s*(?:\*{0,2})Q\d+\b", text))
    if not starts:
        raise ValueError("生成结果缺少题号，请重新生成。")
    return [text[start.start(): starts[i + 1].start() if i + 1 < len(starts) else len(text)].strip()
            for i, start in enumerate(starts)]


class BankStore:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS question_sets (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, reply TEXT NOT NULL DEFAULT '',
                questions TEXT NOT NULL DEFAULT '[]', settings TEXT NOT NULL DEFAULT '{}',
                progress TEXT NOT NULL DEFAULT '{}', version INTEGER NOT NULL DEFAULT 0
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS question_sets_user ON question_sets(user_id, created_at)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self, user_id):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM question_sets WHERE user_id=? AND status='ready' ORDER BY created_at DESC", (user_id,)).fetchall()
        return [self.decode(row) for row in rows]

    @staticmethod
    def decode(row):
        result = dict(row)
        for key in ("questions", "settings", "progress"):
            result[key] = json.loads(result[key])
        result.pop("user_id", None)
        return result

    def reserve(self, user_id, title, settings):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Abandoned generation reservations expire without removing any saved sets.
            db.execute("DELETE FROM question_sets WHERE user_id=? AND status='pending' AND julianday(created_at)<julianday('now','-1 hour')", (user_id,))
            count = db.execute("SELECT COUNT(*) FROM question_sets WHERE user_id=?", (user_id,)).fetchone()[0]
            if count >= LIMIT:
                raise ValueError("题库最多保存 10 组题目，请先删除一组后再创建。")
            bank_id = uuid.uuid4().hex
            db.execute("INSERT INTO question_sets(id,user_id,title,status,created_at,settings) VALUES(?,?,?,'pending',?,?)",
                       (bank_id, user_id, title[:100], datetime.now(timezone.utc).isoformat(), json.dumps(settings, ensure_ascii=False)))
        return bank_id

    def finish(self, bank_id, user_id, reply):
        questions = split_questions(reply)
        if len(questions) > 50:
            raise ValueError("单组最多 50 道题，请缩小数量后重新生成。")
        with self.connect() as db:
            db.execute("UPDATE question_sets SET status='ready',reply=?,questions=? WHERE id=? AND user_id=? AND status='pending'",
                       (reply, json.dumps(questions, ensure_ascii=False), bank_id, user_id))
            row = db.execute("SELECT * FROM question_sets WHERE id=? AND user_id=?", (bank_id, user_id)).fetchone()
        if row is None:
            raise ValueError("题组保存失败，请重试。")
        return self.decode(row)

    def delete(self, bank_id, user_id):
        with self.connect() as db:
            return db.execute("DELETE FROM question_sets WHERE id=? AND user_id=?", (bank_id, user_id)).rowcount > 0

    def save_progress(self, bank_id, user_id, progress, version):
        with self.connect() as db:
            updated = db.execute("UPDATE question_sets SET progress=?,version=version+1 WHERE id=? AND user_id=? AND status='ready' AND version=?",
                                 (json.dumps(progress, ensure_ascii=False), bank_id, user_id, version)).rowcount
        return bool(updated)
