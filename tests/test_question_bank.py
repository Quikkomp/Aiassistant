import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_chat_site"))
from question_bank import BankStore, split_questions

REPLY = "Q1 [fill_blank]\nWater freezes at ____.\n\nQ2 [short_answer]\nExplain freezing."


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BankStore(str(Path(self.tmp.name) / "bank.sqlite3"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_persistence_and_isolation(self):
        bank_id = self.store.reserve("alice", "课程练习", {"selected_docs": ["lecture.txt"]})
        self.store.finish(bank_id, "alice", REPLY)
        self.assertTrue(self.store.save_progress(bank_id, "alice", {"questionAnswers": ["0°C", ""]}, 0))
        self.assertFalse(self.store.save_progress(bank_id, "alice", {}, 0))
        self.assertFalse(self.store.save_progress(bank_id, "bob", {}, 1))
        self.assertFalse(self.store.delete(bank_id, "bob"))
        self.assertEqual(self.store.list("bob"), [])
        reopened = BankStore(self.store.path).list("alice")[0]
        self.assertEqual(reopened["progress"]["questionAnswers"][0], "0°C")
        self.assertEqual(len(reopened["questions"]), 2)

    def test_atomic_limit_including_parallel_generations(self):
        def create(_):
            try:
                return self.store.reserve("alice", "练习", {})
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=12) as pool:
            ids = [value for value in pool.map(create, range(16)) if value]
        self.assertEqual(len(ids), 10)
        self.store.delete(ids[0], "alice")
        self.assertIsNotNone(self.store.reserve("alice", "replacement", {}))

    def test_parser_rejects_error_and_preserves_multiline_options(self):
        for reply in ["", "⚠️ failed", "❌ failed", "no questions"]:
            with self.assertRaises(ValueError):
                split_questions(reply)
        parts = split_questions("**Q1 [multiple_choice]**\nA. First\nB. Second\nQ2 [short_answer]\nExplain.")
        self.assertEqual(len(parts), 2)
        self.assertIn("B. Second", parts[0])


class RouteTests(StoreTests):
    def setUp(self):
        super().setUp()
        self.body = {}
        self.user = "alice"
        self.calls = []
        fake_app = SimpleNamespace(route=lambda *a, **k: lambda f: f)
        request = SimpleNamespace(get_json=lambda **kwargs: self.body)
        def generate(*args, **kwargs):
            self.calls.append((args, kwargs))
            return REPLY
        self.scope = dict(app=fake_app, request=request, jsonify=lambda value: value,
                          get_current_user_id=lambda: self.user, bank_store=self.store,
                          call_local_model=generate, save_chat_pair=lambda **k: None)
        tree = ast.parse((ROOT / "local_chat_site/app.py").read_text(encoding="utf-8"))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in
                     {"chat", "question_sets_list", "question_sets_delete", "question_sets_progress"}]
        exec(compile(ast.Module(body=functions, type_ignores=[]), "routes-under-test", "exec"), self.scope)

    def test_generate_saves_and_reopens_without_materials(self):
        self.body = {"message": "生成两道基础题", "save_to_bank": True, "bank_title": "基础练习"}
        result = self.scope["chat"]()
        self.assertTrue(result["ok"])
        bank_id = result["bank"]["id"]
        self.assertEqual(self.scope["question_sets_list"]()["banks"][0]["title"], "基础练习")
        self.body = {"progress": {"questionAnswers": ["0"]}, "version": 0}
        self.assertTrue(self.scope["question_sets_progress"](bank_id)["ok"])
        self.user = "bob"
        self.assertEqual(self.scope["question_sets_list"]()["banks"], [])
        self.assertEqual(self.scope["question_sets_delete"](bank_id)[1], 404)

    def test_capacity_rejects_before_model_call(self):
        for _ in range(10):
            self.store.reserve("alice", "reserved", {})
        self.body = {"message": "生成两道题", "save_to_bank": True}
        self.assertEqual(self.scope["chat"]()[1], 400)
        self.assertEqual(self.calls, [])

    def test_generation_error_releases_reservation(self):
        self.body = {"message": "出题", "save_to_bank": True}
        self.scope["call_local_model"] = lambda *a, **k: "❌ service unavailable"
        self.assertEqual(self.scope["chat"]()[1], 400)
        for _ in range(10):
            self.store.reserve("alice", "new", {})


class GenerationTests(unittest.TestCase):
    def test_written_requirements_and_selected_source_reach_model(self):
        tree = ast.parse((ROOT / "local_chat_site/rag_agentV3_2.py").read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RagAgent")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "generate_questions")
        scope = {"os": os}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "generation-under-test", "exec"), scope)
        calls = []
        def complete(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=REPLY))])
        doc = SimpleNamespace(metadata={"source": "lecture.txt"}, page_content="KNOWLEDGE_ONLY: water freezes at zero Celsius.")
        agent = SimpleNamespace(db=SimpleNamespace(similarity_search_with_score=lambda *a, **k: [(doc, 0.1)]),
            client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete))),
            _load_exam_db=lambda: [{"id": 1, "question_type": "short_answer", "question": "TEMPLATE_ONLY: Explain astronomy."}],
            log_question=lambda *args: None)
        instruction = "生成两道高难度简答题"
        self.assertEqual(scope["generate_questions"](agent, instruction, "fill_blank", selected_docs=["lecture.txt"], selected_exam_ids=[1], style_template_only=True), REPLY)
        prompt = calls[0]["messages"][1]["content"]
        self.assertIn(instruction, prompt)
        self.assertIn("override these defaults", prompt)
        source_part = prompt.split("[Source materials]", 1)[1]
        self.assertIn("KNOWLEDGE_ONLY", source_part)
        self.assertNotIn("TEMPLATE_ONLY", source_part)
        self.assertEqual(scope["generate_questions"](agent, "Generate 2 math questions", "fill_blank"), REPLY)


if __name__ == "__main__":
    unittest.main()
