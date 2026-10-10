"""Real Flask routes + SQLite with deterministic AI; no live model or account database."""
import sys
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "tmp/exam-test-deps").exists():
    sys.path.insert(0, str(ROOT / "tmp/exam-test-deps"))
sys.path.insert(0, str(ROOT / "local_chat_site"))
from flask import Flask
from question_bank import BankStore
from exam_store import ExamStore, ExamError
from exam_routes import make_exam_blueprint


class FakeAI:
    fail_grade = False
    fail_report = False
    calls = 0

    def prepare(self, q, docs):
        return {"answer": "0°C", "explanation": "标准大气压下，水的冰点为零摄氏度。", "rubric": "答出零摄氏度得满分。", "knowledge": "冰点"}

    def grade(self, q, answer):
        self.calls += 1
        if self.fail_grade:
            raise RuntimeError("model temporarily unavailable")
        return (1 if "0" in answer else 0), "对照参考答案复习冰点。"

    def report(self, questions, answers):
        if self.fail_report:
            raise RuntimeError("report unavailable")
        return "薄弱点：冰点。请区分温度与物态变化。"

    def support(self, q, answer, feedback, kind, message, history=None):
        return "同类巩固：请描述水结冰时的温度。"


class ExamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bank = BankStore(str(Path(self.temp.name) / "banks.sqlite3"))
        self.store = ExamStore(str(Path(self.temp.name) / "exams.sqlite3"))
        self.ai = FakeAI()
        self.app = Flask(__name__, template_folder=str(ROOT / "local_chat_site/templates"))
        self.app.secret_key = "isolated-tests"
        self.app.testing = True
        self.app.register_blueprint(make_exam_blueprint(self.store, self.bank, lambda: None, self.ai))
        self.teacher = self.client("teacher")
        self.student = self.client("student")
        self.other = self.client("other")
        ident = self.bank.reserve("teacher", "冰点考试", {"selected_docs": ["private-course.pdf"]})
        self.bank.finish(ident, "teacher", "Q1 [fill_blank]\n水的冰点是 ____ 摄氏度。\n\nQ2 [short_answer]\n请说明冰点。")
        self.bank_id = ident

    def tearDown(self):
        self.temp.cleanup()

    def client(self, user):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["auth_user_id"] = user
            session["username"] = user.title()
        return client

    def call(self, client, method, path, data=None, status=200):
        response = client.open(path, method=method, json=data)
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        return response.get_json()

    def draft(self):
        return self.call(self.teacher, "POST", "/api/exams", {"bank_id": self.bank_id})["exam"]

    def publish(self):
        draft = self.draft()
        for idx in range(2):
            draft = self.call(self.teacher, "POST", f"/api/exams/{draft['id']}/prepare", {"index": idx, "version": draft["version"]})["exam"]
        exam = self.call(self.teacher, "POST", f"/api/exams/{draft['id']}/publish", {"version": draft["version"], "reviewed": True})["exam"]
        return exam, exam["share_url"].rsplit("/", 1)[1]

    def start(self, token):
        return self.call(self.student, "POST", f"/api/exams/shared/{token}/start", {})["attempt"]

    def test_auth_owner_and_origin(self):
        self.call(self.app.test_client(), "GET", "/api/exams", status=401)
        self.call(self.student, "POST", "/api/exams", {"bank_id": self.bank_id}, status=404)
        draft = self.draft()
        self.call(self.student, "GET", f"/api/exams/{draft['id']}", status=404)
        response = self.teacher.post("/api/exams", json={"bank_id": self.bank_id}, headers={"Origin": "https://malicious.invalid"})
        self.assertEqual(response.status_code, 403)

    def test_validation_review_and_version(self):
        draft = self.draft()
        self.call(self.teacher, "POST", f"/api/exams/{draft['id']}/publish", {"version": 0}, status=400)
        self.call(self.teacher, "POST", f"/api/exams/{draft['id']}/publish", {"version": 0, "reviewed": True}, status=400)
        bad = dict(draft)
        bad["questions"][0]["points"] = -1
        self.call(self.teacher, "PUT", f"/api/exams/{draft['id']}", bad, status=400)
        draft = self.draft()
        self.call(self.teacher, "PUT", f"/api/exams/{draft['id']}", draft)
        self.call(self.teacher, "PUT", f"/api/exams/{draft['id']}", draft, status=409)

    def test_snapshot_independent_and_hidden_keys(self):
        exam, token = self.publish()
        self.call(self.teacher, "PUT", f"/api/exams/{exam['id']}", exam, status=409)
        self.bank.delete(self.bank_id, "teacher")
        preview = self.call(self.student, "GET", f"/api/exams/shared/{token}")["exam"]
        self.assertNotIn("questions", preview)
        packet = self.start(token)
        self.assertEqual(packet["total"], 100)
        self.assertEqual(len(packet["questions"]), 2)
        for q in packet["questions"]:
            self.assertNotIn("answer", q)
            self.assertNotIn("explanation", q)
            self.assertNotIn("rubric", q)
        self.assertNotIn("private-course", str(packet))
        response = self.teacher.get(f"/api/exams/{exam['id']}/qr")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<svg", response.data)
        self.assertEqual(response.mimetype, "image/svg+xml")

    def test_single_attempt_locked_grading_and_server_score(self):
        _, token = self.publish()
        packet = self.start(token)
        self.assertEqual(self.start(token)["id"], packet["id"])
        path = f"/api/exam_attempts/{packet['id']}"
        self.call(self.other, "GET", path, status=404)
        self.call(self.student, "POST", path + "/complete", {"score": 100}, status=409)
        self.call(self.student, "POST", path + "/support", {"index": 0, "kind": "explain"}, status=400)
        self.call(self.student, "POST", path + "/answer", {"index": True, "answer": "0"}, status=400)
        graded = self.call(self.student, "POST", path + "/answer", {"index": 0, "answer": "0°C", "ratio": 0})["attempt"]
        self.assertEqual(graded["questions"][0]["submission"]["ratio"], 1)
        self.assertEqual(graded["questions"][0]["answer"], "0°C")
        self.assertNotIn("answer", graded["questions"][1])
        self.call(self.student, "POST", path + "/answer", {"index": 0, "answer": "100°C"}, status=409)
        self.call(self.student, "POST", path + "/answer", {"index": 0, "answer": "0°C"})
        self.assertEqual(self.ai.calls, 1)
        self.call(self.student, "POST", path + "/answer", {"index": 1, "answer": "99°C", "ratio": 1})
        completed = self.call(self.student, "POST", path + "/complete", {"score": 100})["attempt"]
        self.assertEqual(completed["score"], 50)
        self.call(self.student, "POST", path + "/answer", {"index": 1, "answer": "0°C"}, status=409)
        self.assertEqual(self.start(token)["status"], "completed")
        self.call(self.student, "POST", path + "/support", {"index": 0, "kind": "understanding", "value": "unclear"})
        self.call(self.student, "POST", path + "/support", {"index": 0, "kind": "similar"})
        self.assertEqual(self.call(self.student, "GET", path)["attempt"]["score"], 50)

    def test_model_failure_preserves_answer_and_report_retry(self):
        _, token = self.publish()
        path = f"/api/exam_attempts/{self.start(token)['id']}"
        self.ai.fail_grade = True
        self.call(self.student, "POST", path + "/answer", {"index": 0, "answer": "0"}, status=502)
        q = self.call(self.student, "GET", path)["attempt"]["questions"][0]
        self.assertEqual(q["submission"]["status"], "error")
        self.assertNotIn("answer", q)
        self.call(self.student, "POST", path + "/answer", {"index": 0, "answer": "changed"}, status=409)
        self.ai.fail_grade = False
        for idx in range(2):
            self.call(self.student, "POST", path + "/answer", {"index": idx, "answer": "0"})
        self.call(self.student, "POST", path + "/complete", {})
        self.ai.fail_report = True
        self.call(self.student, "POST", path + "/report", {}, status=502)
        self.assertEqual(self.call(self.student, "GET", path)["attempt"]["score"], 100)
        self.ai.fail_report = False
        self.assertIn("薄弱点", self.call(self.student, "POST", path + "/report", {})["attempt"]["report"])

    def test_close_blocks_new_students_not_resumption(self):
        exam, token = self.publish()
        packet = self.start(token)
        self.call(self.teacher, "POST", f"/api/exams/{exam['id']}/close", {})
        self.assertEqual(self.start(token)["id"], packet["id"])
        self.call(self.other, "POST", f"/api/exams/shared/{token}/start", {}, status=409)
        self.call(self.student, "GET", f"/api/exams/{exam['id']}/submissions", status=404)
        rows = self.call(self.teacher, "GET", f"/api/exams/{exam['id']}/submissions")["submissions"]
        self.assertEqual(len(rows), 1)

    def test_parallel_start_and_grading_claims(self):
        _, token = self.publish()
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _: self.store.start(token, "parallel", "Parallel")["id"], range(8)))
        self.assertEqual(len(set(ids)), 1)
        claim, _ = self.store.claim_answer(ids[0], "parallel", 0, "0")
        with self.assertRaises(ExamError):
            self.store.claim_answer(ids[0], "parallel", 0, "0")
        self.store.finish_grade(ids[0], 0, claim, 1, "Correct")
        self.assertIsNone(self.store.claim_answer(ids[0], "parallel", 0, "0")[0])
        with self.assertRaises(ExamError):
            self.store.finish_grade(ids[0], 0, claim, float("nan"), "Bad")

    def test_owner_analytics_excludes_incomplete_and_counts_distribution(self):
        exam, token = self.publish()
        for name, ratios in (("student", (1, 0)), ("other", (1, 1))):
            attempt = self.store.start(token, name, name.title())
            for idx, ratio in enumerate(ratios):
                claim, _ = self.store.claim_answer(attempt["id"], name, idx, "answer")
                self.store.finish_grade(attempt["id"], idx, claim, ratio, "Feedback")
            self.store.complete(attempt["id"], name)
        self.store.start(token, "incomplete", "Incomplete")
        path = f"/api/exams/{exam['id']}/analytics"
        self.call(self.student, "GET", path, status=404)
        stats = self.call(self.teacher, "GET", path)["analytics"]
        self.assertEqual(stats["started"], 3)
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["average"], 75)
        self.assertEqual(stats["median"], 75)
        self.assertEqual(stats["highest"], 100)
        self.assertEqual(stats["lowest"], 50)
        self.assertEqual(stats["pass_rate"], 50)
        self.assertEqual(stats["completion_rate"], 66.7)
        self.assertEqual([d["count"] for d in stats["distribution"]], [1, 0, 0, 0, 1])
        self.assertEqual([q["correct_rate"] for q in stats["questions"]], [100, 50])
        self.assertEqual(stats["weaknesses"][0]["mastery"], 75)
        owned = self.call(self.teacher, "GET", "/api/exams")["owned"][0]
        self.assertEqual(owned["started"], 3)
        self.assertEqual(owned["completed"], 2)
        self.assertEqual(owned["graded_count"], 4)
        self.assertEqual(owned["average"], stats["average"])
        self.assertEqual(owned["question_count"], 2)
        self.assertNotIn("questions", owned)
        self.assertNotIn("students", owned)
        self.assertEqual(self.call(self.student, "GET", "/api/exams")["owned"], [])

    def test_catalog_draft_has_zero_metrics_and_active_scores_are_excluded(self):
        draft = self.draft()
        row = self.call(self.teacher, "GET", "/api/exams")["owned"][0]
        self.assertEqual((row["started"], row["completed"], row["graded_count"], row["average"]), (0, 0, 0, None))
        self.assertEqual(row["id"], draft["id"])
        exam, token = self.publish()
        attempt = self.start(token)
        self.call(self.student, "POST", f"/api/exam_attempts/{attempt['id']}/answer", {"index": 0, "answer": "0"})
        row = self.call(self.teacher, "GET", "/api/exams")["owned"][0]
        self.assertEqual(row["id"], exam["id"])
        self.assertEqual((row["started"], row["completed"], row["graded_count"], row["average"]), (1, 0, 1, None))

    def test_catalog_normalizes_custom_marks_and_keeps_exam_totals_separate(self):
        draft = self.draft()
        for idx, q in enumerate(draft["questions"]):
            q.update(points=5 if idx == 0 else 15, answer="0", explanation="Explanation", rubric="Criteria")
        draft = self.call(self.teacher, "PUT", f"/api/exams/{draft['id']}", draft)["exam"]
        exam = self.call(self.teacher, "POST", f"/api/exams/{draft['id']}/publish", {"version": draft["version"], "reviewed": True})["exam"]
        token = exam["share_url"].rsplit("/", 1)[1]
        attempt = self.start(token)
        for idx, answer in enumerate(("0", "wrong")):
            self.call(self.student, "POST", f"/api/exam_attempts/{attempt['id']}/answer", {"index": idx, "answer": answer})
        self.call(self.student, "POST", f"/api/exam_attempts/{attempt['id']}/complete", {})
        empty = self.draft()
        rows = {row["id"]: row for row in self.call(self.teacher, "GET", "/api/exams")["owned"]}
        self.assertEqual(rows[exam["id"]]["average"], 25)
        self.assertEqual(rows[exam["id"]]["graded_count"], 2)
        self.assertEqual(rows[empty["id"]]["started"], 0)
        self.assertIsNone(rows[empty["id"]]["average"])


if __name__ == "__main__":
    unittest.main()
