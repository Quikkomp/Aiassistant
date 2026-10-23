"""Offline PDF math regression, including the reported calculus examples."""
import ast
import copy
from io import BytesIO
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_chat_site"))
from pdf_math import MathParagraphRenderer, math_segments
from test_pdf_export import actual_builder


SAMPLE_QUESTIONS = [
    {"question_type": "multiple_choice", "question": r"""Q1 [multiple_choice]
考虑函数 \(f(x)=x^3-3x+2\)。在区间 \([-2,2]\) 内，\(f(x)\) 的最大值和最小值分别为：
A) 最大值 3，最小值 -5
B) 最大值 2，最小值 -4
C) 最大值 4，最小值 0
D) 最大值 5，最小值 -1"""},
    {"question_type": "multiple_choice", "question": r"""Q2 [multiple_choice]
若函数 \(g(x)=e^{2x}\sin(x)\)，则其一阶导数 \(g'(x)\) 为：
A) \(2e^{2x}\sin(x)+e^{2x}\cos(x)\)
B) \(2e^{2x}\cos(x)+e^{2x}\sin(x)\)
C) \(e^{2x}(2\sin(x)-\cos(x))\)
D) \(e^{2x}(2\cos(x)+\sin(x))\)"""},
    {"question_type": "multiple_choice", "question": r"""Q3 [multiple_choice]
设 \(h(x)=\ln(x^2+1)\)，则 \(h'(1)\) 的值为：
A) 0
B) 1
C) 2
D) \(\frac{1}{2}\)"""},
    {"question_type": "multiple_choice", "question": r"""Q4 [multiple_choice]
在计算不定积分 \(\int(4x^3-2x+1)\,dx\) 时，结果为：
A) \(x^4-x^2+x+C\)
B) \(x^4-x^2+C\)
C) \(x^4-x^2+x^2+C\)
D) \(4x^4-\frac{2}{2}x^2+x+C\)"""},
    {"question_type": "short_answer", "question": r"""Q5 [short_answer]
计算下列极限与定积分，写出推导步骤：
\[\lim_{x\to0}\frac{\sin x}{x}\]
$$\int_0^1\frac{x^2}{\sqrt{1+x^2}}\,dx$$
参考恒等式：\(\frac{d}{dx}\ln x=\frac{1}{x}\)，并说明适用条件。
中文符号测试：\(S_{\text{面积}}=\frac{1}{4}\pi r^2\)。"""},
]

ENGLISH_BLANK = (
    "Q1 [fill_blank]\n"
    r"If the function \(f(x)=ax^2+bx+c\) has its vertex at the point "
    r"\((h,k)\), then \(h\) can be expressed as \(h=\frac{-b}{\_\_\_\_}\)."
)
# 16 words put the formula exactly across an A4 content-line boundary in
# ReportLab 4.2.5: its CJK breaker previously raised ord('') -> TypeError.
INLINE_WRAP_REPRO = (
    "word " * 16 + r"\(h=\frac{-b}{\_\_\_\_}\)"
    + " words following the equation " * 3
)


class MathSegmentsTests(unittest.TestCase):
    def test_delimiters_code_currency_and_literal_markup(self):
        text = r"价格 $10 and $20；`$not_math$`；<img src='http://invalid'>；$x^2$；\(\pi\)；\[x_1\]；$$\sqrt{x}$$"
        tokens = list(math_segments(text))
        self.assertEqual([source for kind, source, _ in tokens if kind == "math"],
                         ["x^2", r"\pi", "x_1", r"\sqrt{x}"])
        self.assertTrue(any("$10 and $20" in source for kind, source, _ in tokens if kind == "plain"))

    def test_aligned_equations_are_not_concatenated(self):
        tokens = list(math_segments(r"\begin{aligned}a&=b+c\\d&=e-f\end{aligned}"))
        self.assertEqual(tokens, [("math", "a=b+c", True), ("math", "d=e-f", True)])


@unittest.skipUnless(importlib.util.find_spec("matplotlib") and importlib.util.find_spec("reportlab"),
                     "Install requirements-pdf.txt to test PDF math")
class MathPDFTests(unittest.TestCase):
    def test_english_inline_images_crossing_line_boundary_do_not_use_cjk_breaker(self):
        from reportlab.lib.styles import ParagraphStyle
        from pdf_fonts import get_pdf_font_name
        style = ParagraphStyle("CJKImageRepro", fontName=get_pdf_font_name(), fontSize=10.5,
                               leading=16, autoLeading="max", wordWrap="CJK")
        renderer = MathParagraphRenderer()
        for width in (477.228, 400, 200):
            for length in (1, 12, 15, 16, 17, 20, 30, 50):
                texts = [
                    "word " * length + r"\(h=\frac{-b}{\_\_\_\_}\)" + " following words " * 10,
                    r"\(x^2+bx+c\)" + "word " * length + r"\(\frac{-b}{2a}\)",
                    "a" * length + r"\(\frac{-b}{2a}\)" + "a" * 60,
                    "这是一个中英文混排的分式填空题，" * length + r"\(h=\frac{-b}{\_\_\_\_}\)" + "说明理由。",
                ]
                for text in texts:
                    with self.subTest(width=width, length=length, prefix=text[:20]):
                        paragraph = renderer.paragraph(text, style, width)
                        _, height = paragraph.wrap(width, 700)
                        self.assertGreater(height, 0)
                        self.assertEqual(paragraph.style.wordWrap, "LTR")
                        self.assertEqual(style.wordWrap, "CJK", "Do not mutate the caller's style")
        plain = renderer.paragraph("纯中文题目，没有公式。", style, 400)
        self.assertIs(plain.style, style)

    def test_ten_english_fill_blank_questions_export_and_paginate(self):
        from pypdf import PdfReader
        questions = [ENGLISH_BLANK, INLINE_WRAP_REPRO] * 5
        original = list(questions)
        reader = PdfReader(actual_builder()(questions, title="English fill-in-the-blank regression"))
        text = "\n".join(page.extract_text() for page in reader.pages)
        self.assertGreater(len(reader.pages), 1)
        self.assertIn("Total: 10 questions", text)
        self.assertIn("vertex at the point", text)
        self.assertIn("Q10", text)
        self.assertNotIn(r"\frac", text)
        self.assertEqual(questions, original)

    def test_calculus_pdf_contains_images_instead_of_raw_latex_and_preserves_input(self):
        from pypdf import PdfReader
        original = copy.deepcopy(SAMPLE_QUESTIONS)
        result = actual_builder()(SAMPLE_QUESTIONS, title="微积分练习试卷：公式导出验证")
        reader = PdfReader(result)
        text = "\n".join(page.extract_text() for page in reader.pages)
        self.assertIn("微积分练习试卷", text)
        self.assertIn("在计算不定积分", text)
        for raw in (r"\(", r"\frac", r"\int", r"\sin", "$$", "■"):
            self.assertNotIn(raw, text)
        images = sum(1 for page in reader.pages
                     for obj in page["/Resources"].get("/XObject", {}).get_object().values()
                     if obj.get_object().get("/Subtype") == "/Image")
        self.assertGreater(images, 20)
        self.assertEqual(SAMPLE_QUESTIONS, original)

    def test_tall_fractions_and_long_papers_split_across_pages(self):
        from pypdf import PdfReader
        text = ("请逐行计算：" + r"\[\frac{\frac{x^2+1}{x-1}}{\sqrt{x^2+2}}\]" + "\n") * 35
        reader = PdfReader(actual_builder()([text, "最后一题：说明答案。"], title="分页测试"))
        self.assertGreater(len(reader.pages), 2)
        self.assertIn("最后一题", reader.pages[-1].extract_text())

    def test_formula_failures_are_explicit_not_silently_raw_source(self):
        for text in (r"错误 \(\frac{1}{\)", r"未配对 \(x^2", r"\(\begin{matrix}1&2\end{matrix}\)",
                     r"\(\includegraphics{/etc/passwd}\)", r"\(\href{https://example.com}{x}\)"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "第 1 题"):
                actual_builder()([text])

    def test_escape_user_markup_and_do_not_load_external_resources(self):
        from pypdf import PdfReader
        literal = '<img src="https://example.com/private.png"> <script>alert(1)</script>'
        result = actual_builder()([literal + r" \(x^2\)"])
        self.assertIn(literal, PdfReader(result).pages[0].extract_text())

    def test_per_document_cache_and_limits(self):
        from reportlab.lib.styles import ParagraphStyle
        from pdf_fonts import get_pdf_font_name
        import pdf_math
        style = ParagraphStyle("test", fontName=get_pdf_font_name(), fontSize=10.5)
        renderer = MathParagraphRenderer()
        with patch.object(pdf_math, "_formula_image", wraps=pdf_math._formula_image) as render:
            renderer.paragraph(r"\(x^2\) 和 \(x^2\)", style, 400)
            self.assertEqual(render.call_count, 1)
        with patch.object(pdf_math, "MAX_FORMULAS", 1), self.assertRaisesRegex(ValueError, "公式过多"):
            MathParagraphRenderer().paragraph(r"\(x\) \(y\)", style, 400)
        with self.assertRaisesRegex(ValueError, "嵌套过深"):
            actual_builder()([r"\(" + "{" * 41 + "x" + "}" * 41 + r"\)"])
        with self.assertRaisesRegex(ValueError, "过长"):
            actual_builder()([r"\(" + "x+" * 1200 + r"1\)"])
        with self.assertRaises(ValueError):
            actual_builder()(["题目"] * 51)

    def test_renderer_is_safe_for_parallel_exports(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: actual_builder()([r"求 \(\int_0^1x^2\,dx\)。"]).getvalue(), range(6)))
        self.assertTrue(all(result.startswith(b"%PDF-") for result in results))

    def test_real_export_endpoint_returns_pdf_and_actionable_formula_error(self):
        from flask import Flask, jsonify, request, send_file
        app = Flask(__name__)
        tree = ast.parse((ROOT / "local_chat_site/app.py").read_text(encoding="utf-8-sig"))
        route = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "export_questions_pdf")
        namespace = dict(app=app, jsonify=jsonify, request=request, send_file=send_file,
                         _build_questions_pdf=actual_builder())
        exec(compile(ast.Module(body=[route], type_ignores=[]), "actual_pdf_route", "exec"), namespace)
        client = app.test_client()
        response = client.post("/api/export_questions_pdf", json={"questions": [SAMPLE_QUESTIONS[3]], "title": "积分试卷"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        response = client.post("/api/export_questions_pdf", json={"questions": [ENGLISH_BLANK, INLINE_WRAP_REPRO] * 5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        response = client.post("/api/export_questions_pdf", json={"questions": [r"\(\badcommand{x}\)"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("第 1 题", response.json["msg"])
        with patch("pdf_math._engine", side_effect=RuntimeError("PDF 数学公式依赖缺失，请安装 requirements-pdf.txt。")):
            response = client.post("/api/export_questions_pdf", json={"questions": [r"\(x\)"]})
        self.assertEqual(response.status_code, 500)
        self.assertIn("requirements-pdf.txt", response.json["msg"])
        with patch.dict(namespace, {"_build_questions_pdf": Mock(side_effect=TypeError("PRIVATE_FORMULA_DO_NOT_LOG"))}):
            with self.assertLogs(app.logger, level="WARNING") as logs:
                response = client.post("/api/export_questions_pdf", json={"questions": ["Private question"]})
        self.assertEqual(response.status_code, 500)
        self.assertIn("内部错误", response.json["msg"])
        self.assertNotIn("缩短题目", response.json["msg"])
        self.assertIn("frames=", "\n".join(logs.output))
        self.assertNotIn("PRIVATE_FORMULA_DO_NOT_LOG", "\n".join(logs.output))
        self.assertNotIn("Private question", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
