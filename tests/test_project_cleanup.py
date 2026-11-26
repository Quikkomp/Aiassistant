"""Source/asset regressions for legacy cleanup. No real SDK, DB or network."""
import ast
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import os
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "local_chat_site"
sys.path.insert(0, str(SITE))


class ProjectCleanupTests(unittest.TestCase):
    def test_current_agent_imports_and_constructs_without_legacy_search_or_cli(self):
        calls = []
        fake_client = SimpleNamespace()
        def create_client(**kwargs):
            calls.append(kwargs)
            return fake_client
        modules = {
            "openai": SimpleNamespace(OpenAI=create_client),
            "dotenv": SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
            "document_loader": SimpleNamespace(load_documents=None, read_txt=None, read_pdf=None, read_docx=None),
            "langchain_text_splitters": SimpleNamespace(RecursiveCharacterTextSplitter=None),
            "langchain_community": SimpleNamespace(),
            "langchain_community.vectorstores": SimpleNamespace(FAISS=None),
            "langchain_openai": SimpleNamespace(OpenAIEmbeddings=None),
            "langchain_core": SimpleNamespace(),
            "langchain_core.documents": SimpleNamespace(Document=None),
            "pytesseract": SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="")),
            "pdf2image": SimpleNamespace(convert_from_path=None),
        }
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                with patch.dict(sys.modules, modules), patch.dict(os.environ, {"OPENAI_API_KEY": "offline-test-key"}, clear=True), redirect_stdout(StringIO()):
                    spec = importlib.util.spec_from_file_location("cleaned_agent_smoke", SITE / "rag_agent.py")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    agent = module.RagAgent(module.client, None, exam_db_path="per-user-exams.json")
                    # Exercise the actual web entry, not a rewritten app fixture.
                    # Redirect every app-owned path to a disposable directory and
                    # forbid MySQL calls. The model and dotenv remain mocked.
                    tree = ast.parse((SITE / "app.py").read_text(encoding="utf-8-sig"))
                    for node in tree.body:
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BASE_DIR" for t in node.targets):
                            node.value = ast.Constant(temporary)
                    connector = SimpleNamespace(connect=Mock(side_effect=AssertionError("No real MySQL")))
                    web = ModuleType("cleaned_app_smoke")
                    web.__file__ = str(Path(temporary) / "app.py")
                    with patch.dict(sys.modules, {"rag_agent": module, "mysql": SimpleNamespace(connector=connector),
                                                  "mysql.connector": connector, "cleaned_app_smoke": web}):
                        exec(compile(ast.fix_missing_locations(tree), "isolated_actual_app", "exec"), web.__dict__)
                        with web.app.test_request_context("/"):
                            request_agent = web.get_rag_agent_for_current_user()
                        self.assertIsInstance(request_agent, module.RagAgent)
                        self.assertTrue(request_agent.exam_db_path.startswith(temporary))
                        self.assertTrue(web.bank_store.path.startswith(temporary))
                        self.assertTrue(web.exam_store.path.startswith(temporary))
                        self.assertEqual(web.app.test_client().get("/api/auth/status").status_code, 200)
                        connector.connect.assert_not_called()
                self.assertEqual(calls, [{"api_key": "offline-test-key"}])
                self.assertIs(agent.client, fake_client)
                self.assertEqual(agent.exam_db_path, "per-user-exams.json")
                for name in ("generate_questions", "grade_answer", "generate_scenario_question",
                             "answer_exam_question", "explain_question_detailed", "ingest_material",
                             "summarize_wrong_questions", "analyze_full_round", "import_past_exam_from_file"):
                    self.assertTrue(callable(getattr(agent, name)), name)
                for name in ("plan", "answer", "extract_keywords", "search_and_summarize",
                             "summarize_learning", "add_past_exam_question"):
                    self.assertFalse(hasattr(agent, name), name)
                self.assertFalse(hasattr(module, "SYSTEM_PROMPT"))
                self.assertFalse(hasattr(module, "chat_with_agent"))
            finally:
                os.chdir(previous)

    def test_app_uses_current_module_and_no_retired_routes(self):
        tree = ast.parse((SITE / "app.py").read_text(encoding="utf-8-sig"))
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertIn("rag_agent", imports)
        self.assertNotIn("rag_agentV3_2", imports)
        routes = {node.args[0].value for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == "route" and node.args and isinstance(node.args[0], ast.Constant)}
        for name in ("/api/chat", "/api/upload", "/api/past_exam/upload", "/api/export_questions_pdf", "/api/round_analysis"):
            self.assertIn(name, routes)
        self.assertNotIn("/api/feedback", routes)
        self.assertNotIn("/api/past_exam/add", routes)
        self.assertFalse((SITE / "rag_agentV3_2.py").exists())

    def test_template_and_stylesheet_assets_all_exist(self):
        for template in (SITE / "templates").glob("*.html"):
            for asset in re.findall(r"url_for\('static', filename='([^']+)'\)", template.read_text(encoding="utf-8-sig")):
                self.assertTrue((SITE / "static" / asset).is_file(), (template.name, asset))
        for css in (SITE / "static").rglob("*.css"):
            for asset in re.findall(r"url\([\"']?([^\)\"']+)[\"']?\)", css.read_text(encoding="utf-8-sig")):
                if asset.startswith(("data:", "http:", "https:", "#")):
                    continue
                asset = asset.split("?", 1)[0].split("#", 1)[0]
                path = SITE / asset.lstrip("/") if asset.startswith("/static/") else css.parent / asset
                self.assertTrue(path.is_file(), (str(css), asset))

    def test_superseded_assets_and_dead_handlers_stay_removed(self):
        for asset in ("auth-ai-tutor-bg.png", "heritage-auth-bg.png", "metathink-logo.png",
                      "role-student-anime-v1.png", "role-teacher-anime-v1.png"):
            self.assertFalse((SITE / "static" / asset).exists(), asset)
        source = (SITE / "static/app.js").read_text(encoding="utf-8-sig")
        for handler in ("mapFeedbackToScore", "appendMessage", "renderTextWithLinks", "addPastExamQuestionFromForm"):
            self.assertNotRegex(source, r"\bfunction\s+" + handler + r"\b")
        self.assertIn('className = "learning-tools-row"', source)
        self.assertNotIn("SERPAPI_KEY", (ROOT / ".env.example").read_text(encoding="utf-8-sig"))

    def test_runtime_dependencies_do_not_include_unrelated_app_frameworks(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8-sig")
        packages = {line.split("==")[0].lower() for line in requirements.splitlines()
                    if line and not line.startswith(("#", "-"))}
        for unrelated in ("streamlit", "fastapi", "pygame", "nipype", "nibabel", "locust", "fitz", "app", "docx"):
            self.assertNotIn(unrelated, packages)
        for required in ("flask", "openai", "langchain-community", "faiss-cpu", "python-docx", "python-pptx"):
            self.assertIn(required, packages)
        self.assertIn("-r requirements-pdf.txt", requirements)


if __name__ == "__main__":
    unittest.main()
