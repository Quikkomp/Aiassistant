"""Offline PDF export regression; no real app startup, accounts or AI requests."""
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_chat_site"))
import pdf_fonts


def actual_builder():
    tree = ast.parse((ROOT / "local_chat_site/app.py").read_text(encoding="utf-8-sig"))
    names = {"_infer_export_question_type", "_format_export_question_type", "_build_questions_pdf"}
    methods = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    # There must be no dependency on Windows paths, system fonts or cwd.
    def no_system_font_search(*args):
        raise AssertionError("PDF export must use its bundled font, not search the host OS")
    namespace = {"Counter": Counter, "re": re, "os": SimpleNamespace(path=SimpleNamespace(exists=no_system_font_search))}
    exec(compile(ast.Module(body=methods, type_ignores=[]), "actual_pdf_export", "exec"), namespace)
    return namespace["_build_questions_pdf"]


@unittest.skipUnless(importlib.util.find_spec("reportlab"), "reportlab is optional in minimal test runtimes")
class PDFExportTests(unittest.TestCase):
    def test_bundled_font_covers_chinese_punctuation_and_common_symbols(self):
        from reportlab.pdfbase import pdfmetrics
        font = pdfmetrics.getFont(pdf_fonts.get_pdf_font_name())
        for char in "中文试卷简答选择题填空題繁體學生，。！？（）π×²":
            self.assertIn(ord(char), font.face.charToGlyph, char)

    def test_pdf_embeds_cjk_font_and_preserves_chinese_without_system_fonts(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                self.skipTest("A PDF reader is needed to verify embedded fonts")
        title = "中文试卷：半圆面积练习"
        body = "计算半圆面积，并解释你的解题步骤。\nA. 圆面积的一半\nB. 完整圆面积"
        result = actual_builder()([{"question": body, "question_type": "multiple_choice"}], title=title)
        pdf = PdfReader(result)
        text = "\n".join(page.extract_text() for page in pdf.pages)
        for phrase in (title, "计算半圆面积", "圆面积的一半", "选择题"):
            self.assertIn(phrase, text)
        self.assertNotIn("\u25a0", text)
        embedded = []
        for page in pdf.pages:
            for ref in page["/Resources"]["/Font"].get_object().values():
                font = ref.get_object()
                if "NotoSansSC" in str(font.get("/BaseFont", "")):
                    descriptor = font["/FontDescriptor"].get_object()
                    self.assertGreater(len(descriptor["/FontFile2"].get_object().get_data()), 1000)
                    self.assertIn("/ToUnicode", font)
                    embedded.append(font)
        self.assertTrue(embedded, "The exported PDF must carry its own Chinese glyphs")

    def test_font_path_does_not_depend_on_working_directory(self):
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertTrue(pdf_fonts.FONT_PATH.is_absolute())
                self.assertTrue(actual_builder()(["在物理学中，力的单位是____。"], title="填空练习").getvalue().startswith(b"%PDF-"))
            finally:
                os.chdir(previous)

    def test_missing_font_reports_error_instead_of_exporting_black_boxes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pdf_fonts, "FONT_PATH", Path(directory) / "missing.ttf"):
            with self.assertRaisesRegex(RuntimeError, "字体缺失"):
                actual_builder()(["中文题目"])

    def test_invalid_font_reports_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.ttf"
            invalid.write_bytes(b"not a font")
            with patch.object(pdf_fonts, "FONT_PATH", invalid), patch.object(pdf_fonts, "FONT_NAME", "WizPracticePDFInvalidTest"):
                with self.assertRaisesRegex(RuntimeError, "字体加载失败"):
                    actual_builder()(["中文题目"])

    def test_concurrent_calls_register_font_once(self):
        from reportlab.pdfbase import pdfmetrics
        with patch.object(pdf_fonts, "FONT_NAME", "WizPracticePDFConcurrentTest"), patch.object(pdfmetrics, "registerFont", wraps=pdfmetrics.registerFont) as register:
            with ThreadPoolExecutor(max_workers=4) as pool:
                names = list(pool.map(lambda _: pdf_fonts.get_pdf_font_name(), range(8)))
            self.assertEqual(names, ["WizPracticePDFConcurrentTest"] * 8)
            self.assertEqual(register.call_count, 1)


if __name__ == "__main__":
    unittest.main()
