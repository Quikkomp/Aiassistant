"""Offline import regression; model responses are simulated, never sent to a service."""
import ast
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_chat_site"))
from exam_import import ExamImportError, parse_model_questions, split_numbered_questions, question_type
from document_loader import read_pdf, read_txt, read_docx


def harness():
    tree = ast.parse((ROOT / "local_chat_site/rag_agentV3_2.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RagAgent")
    names = {"_load_exam_db", "_save_exam_db", "_extract_questions_from_text", "import_past_exam_from_file"}
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = dict(os=os, json=json, tempfile=tempfile, ExamImportError=ExamImportError,
                     parse_model_questions=parse_model_questions, split_numbered_questions=split_numbered_questions,
                     question_type=question_type, read_pdf=read_pdf, read_txt=read_txt, read_docx=read_docx,
                     get_user_build_lock=lambda _: nullcontext())
    test_cls = ast.ClassDef(name="ImportHarness", bases=[], keywords=[], body=methods, decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[test_cls], type_ignores=[])), "actual_import_methods", "exec"), namespace)
    return namespace["ImportHarness"]


SAMPLE = """Instructions to candidates
1. Answer all questions.
Page 1 of 2
Question 1. Fundamentals [10 marks]
Use the supplied material for the following questions.
1.1. Explain a concept. [5 marks]
More detail on the next line.
Page 2 of 2
1.2. Select one answer. [5 marks]
A. First
B. Second
Question 2. Application [5 marks]
Explain the diagram and its labels.
"""


class ParserTests(unittest.TestCase):
    def test_json_formats_and_invalid_items(self):
        items = [{"question": "Explain OpenGL.", "question_type": "short_answer"}]
        for content in [json.dumps(items), "```json\n" + json.dumps(items) + "\n```",
                        json.dumps({"questions": items}), "Here are the questions:\n" + json.dumps(items)]:
            self.assertEqual(parse_model_questions(content), items)
        self.assertEqual(parse_model_questions('[]'), [])
        self.assertEqual(parse_model_questions('{"questions":[null, {"question":null}]}'), [])
        self.assertEqual(parse_model_questions('```json\n[{"question":"truncated"}'), [])

    def test_numbered_structure_preserves_stems_and_ignores_cover(self):
        items = split_numbered_questions(SAMPLE)
        self.assertEqual([q["meta"]["index"] for q in items], ["1.1", "1.2", "Q2"])
        self.assertIn("Use the supplied material", items[0]["question"])
        self.assertIn("More detail", items[0]["question"])
        self.assertNotIn("Page 2 of 2", items[0]["question"])
        self.assertNotIn("Answer all", items[0]["question"])
        self.assertEqual(items[1]["question_type"], "multiple_choice")
        self.assertIn("B. Second", items[1]["question"])


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = harness()()
        self.agent.EXAM_DB_PATH = self.agent.exam_db_path = str(Path(self.tmp.name) / "past_exams.json")
        self.reply = '[{"question":"Explain OpenGL.", "question_type":"short_answer"}]'
        self.error = None
        self.finish_reason = "stop"
        self.agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=self.create)))
        self.agent._ocr_pdf_to_text = lambda _: ""
        self.agent._describe_pdf_with_gpt_vision = lambda _: ""

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply), finish_reason=self.finish_reason)])

    def test_fenced_json_saves_and_reopens(self):
        self.reply = "```json\n" + self.reply + "\n```"
        added = self.agent._extract_questions_from_text(SAMPLE, source_name="paper.pdf")
        self.assertEqual(len(added), 1)
        self.assertEqual(self.agent._load_exam_db()[0]["source_file"], "paper.pdf")
        self.assertEqual(self.agent.last_exam_import["method"], "model")

    def test_model_error_and_invalid_reply_fall_back(self):
        for error, reply in [(ConnectionError("offline"), ""), (None, "not json"), (None, "[]")]:
            self.error, self.reply = error, reply
            added = self.agent._extract_questions_from_text(SAMPLE, source_name="paper.pdf")
            self.assertEqual(len(added), 3)
            self.assertEqual(self.agent.last_exam_import["method"], "numbered_text")
            self.assertTrue(self.agent.last_exam_import["warnings"])
            self.assertEqual(added[1]["index"], "1.2")

    def test_truncated_model_output_uses_complete_original(self):
        self.finish_reason = "length"
        self.assertEqual(len(self.agent._extract_questions_from_text(SAMPLE)), 3)

    def test_readable_text_and_empty_text_have_distinct_errors(self):
        self.reply = "invalid"
        with self.assertRaises(ExamImportError) as cm:
            self.agent._extract_questions_from_text("No numbered exam questions here.")
        self.assertEqual(cm.exception.stage, "questions")
        empty = Path(self.tmp.name) / "empty.txt"
        empty.touch()
        with self.assertRaises(ExamImportError) as cm:
            self.agent.import_past_exam_from_file(str(empty))
        self.assertEqual(cm.exception.stage, "text")
        with self.assertRaises(ExamImportError) as cm:
            self.agent.import_past_exam_from_file(str(empty) + ".missing")
        self.assertEqual(cm.exception.stage, "read")

    def test_storage_failure_does_not_report_success(self):
        self.agent.exam_db_path = self.tmp.name  # a directory cannot be replaced by a JSON file
        with self.assertRaises(ExamImportError) as cm:
            self.agent._extract_questions_from_text(SAMPLE)
        self.assertEqual(cm.exception.stage, "storage")

    @unittest.skipUnless(os.environ.get("EXAM_IMPORT_PDF"), "Set EXAM_IMPORT_PDF for the supplied real-paper regression")
    def test_supplied_pdf_imports_all_22_subquestions_offline(self):
        self.error = ConnectionError("simulated unavailable model")
        added = self.agent.import_past_exam_from_file(os.environ["EXAM_IMPORT_PDF"])
        self.assertEqual(len(added), 22)
        self.assertEqual([q["index"] for q in added][:3], ["1.1", "1.2", "1.3"])
        self.assertEqual(added[-1]["index"], "5.3")
        self.assertEqual(self.agent.last_exam_import["attempts"], ["pdf_text"])
        self.assertEqual(len(self.agent._load_exam_db()), 22)
        self.assertTrue(all(q["source_file"] == Path(os.environ["EXAM_IMPORT_PDF"]).name for q in added))


if __name__ == "__main__":
    unittest.main()
