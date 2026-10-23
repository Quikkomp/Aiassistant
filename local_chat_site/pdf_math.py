"""Offline math images for ReportLab; never run TeX, JavaScript or a subprocess.

The original question/answer strings are not modified. Only the PDF presentation
turns delimited LaTeX into tightly cropped, 300 dpi transparent images.
"""
import base64
from html import escape
from io import BytesIO
import math
import re
from threading import RLock
import warnings


_LOCK = RLock()  # Matplotlib's font/parser/rc state is not thread-safe.
_ENGINE = None
_TOKEN = re.compile(
    r"(?P<code>```[\s\S]*?```|`[^`\n]*`)"
    r"|(?P<display>\$\$(?P<display_body>[\s\S]*?)\$\$)"
    r"|(?P<bracket>\\\[(?P<bracket_body>[\s\S]*?)\\\])"
    r"|(?P<inline>\\\((?P<inline_body>[\s\S]*?)\\\))"
    r"|(?P<environment>\\begin\{(?P<env>equation\*?|align\*?|aligned|gather\*?)\}"
    r"(?P<env_body>[\s\S]*?)\\end\{(?P=env)\})"
    r"|(?P<dollar>(?<![\\$])\$(?![\s$])"
    r"(?!\d+(?:\.\d+)?(?:\s+(?:and|or)\b|[，；,;]))"
    r"(?P<dollar_body>[^$`\r\n]+?)(?<![\\\s])\$(?!\$))"
)
MAX_FORMULA_LENGTH = 2000
MAX_FORMULAS = 400
MAX_TOTAL_PIXELS = 30000000
DPI = 300


def math_segments(text):
    """Yield (plain|math, source, display). Keep prices and code literal."""
    position = 0
    for match in _TOKEN.finditer(text):
        if match.start() > position:
            yield "plain", text[position:match.start()], False
        if match.group("code") is not None:
            yield "code", match.group(0), False
        else:
            body = next(match.group(name) for name in
                        ("display_body", "bracket_body", "inline_body", "env_body", "dollar_body")
                        if match.group(name) is not None)
            display = bool(match.group("display") or match.group("bracket") or match.group("environment"))
            if match.group("env") and match.group("env").startswith(("align", "gather")):
                # Alignment markers carry no mathematical meaning. Put each
                # equation on its own line; do not flatten matrices or cases.
                for line in re.split(r"\\\\(?:\[[^\]]*\])?", body):
                    if line.strip():
                        yield "math", line.replace("&", ""), True
            else:
                yield "math", body, display
        position = match.end()
    if position < len(text):
        yield "plain", text[position:], False


def _engine():
    global _ENGINE
    if _ENGINE is None:
        try:
            import matplotlib
            from matplotlib import font_manager
            from matplotlib.mathtext import MathTextParser, math_to_image
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError(
                "PDF 数学公式依赖缺失，请在程序的 Python 虚拟环境中安装 requirements-pdf.txt。"
            ) from exc
        from pdf_fonts import FONT_PATH, get_pdf_font_name
        get_pdf_font_name()
        font_manager.fontManager.addfont(str(FONT_PATH))
        family = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
        _ENGINE = (matplotlib, font_manager, MathTextParser("path"), math_to_image,
                   Image, ImageOps, family, str(FONT_PATH))
    return _ENGINE


def _formula_image(source, font_size, max_width):
    # Mathtext is a bounded parser, not a TeX interpreter. Deny external
    # links/images/macros explicitly and never expose parser internals.
    source = source.strip()
    if not source or len(source) > MAX_FORMULA_LENGTH:
        raise ValueError("公式为空或过长，请缩短公式后重试。")
    depth = 0
    for char in source:
        if char == "{":
            depth += 1
            if depth > 40:
                raise ValueError("公式嵌套过深，请简化后重试。")
        elif char == "}":
            depth -= 1
    if re.search(r"\\(?:input|include|includegraphics|href|url|write|def|newcommand|begin|end)\b", source):
        raise ValueError("公式包含不支持的命令或环境，请使用标准分式、积分、上下标等写法。")
    source = re.sub(r"\\(?:displaystyle|textstyle|limits)\b", "", source)
    source = re.sub(r"\\(?:tfrac|dfrac)\b", r"\\frac", source)
    expression = "$" + source.replace("\r", " ").replace("\n", " ") + "$"

    with _LOCK:
        mpl, fm, parser, render, Image, ImageOps, family, font_path = _engine()
        settings = {
            "text.usetex": False,
            "mathtext.fontset": "custom",
            "mathtext.rm": family,
            "mathtext.it": "STIXGeneral:italic",
            "mathtext.bf": "STIXGeneral:weight=bold",
            "mathtext.bfit": "STIXGeneral:italic:weight=bold",
            "mathtext.sf": family,
            "mathtext.tt": family,
            "mathtext.cal": "STIXGeneral",
            "mathtext.fallback": "stix",
        }
        with mpl.rc_context(settings), warnings.catch_warnings():
            warnings.filterwarnings("error", message=r"Glyph .*missing from font")
            prop = fm.FontProperties(fname=font_path, size=font_size, math_fontfamily="custom")
            try:
                width, height, baseline, _, _ = parser.parse(expression, dpi=72, prop=prop)
                if not all(math.isfinite(float(n)) for n in (width, height, baseline)):
                    raise ValueError("Invalid formula metrics")
                # Bound image allocation and avoid unreadably tiny expressions.
                if width <= 0 or height <= 0 or width > max_width * 1.6 or height > 150:
                    raise ValueError("Formula exceeds printable bounds")
                raw = BytesIO()
                render(expression, raw, prop=prop, dpi=DPI, format="png", color="black")
                raw.seek(0)
                with Image.open(raw) as image:
                    padding = 4
                    image = ImageOps.expand(image.convert("RGBA"), border=padding, fill=(255, 255, 255, 0))
                    final = BytesIO()
                    image.save(final, format="PNG")
                    width, height = image.width * 72 / DPI, image.height * 72 / DPI
                baseline += padding * 72 / DPI
            except Exception as exc:
                raise ValueError("公式无法排版，请检查 LaTeX 写法；过长公式请分行，复杂矩阵等环境暂不支持。") from exc
    scale = min(1, max_width / width)
    uri = "data:image/png;base64," + base64.b64encode(final.getvalue()).decode("ascii")
    return uri, width * scale, height * scale, float(baseline) * scale


class MathParagraphRenderer:
    """One cache per export; no persistent formula files or remote resources."""
    def __init__(self):
        self._images = {}
        self._count = 0
        self._pixels = 0

    def paragraph(self, text, style, max_width):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Paragraph
        markup = []
        contains_math = False
        for kind, source, display in math_segments(text):
            if kind != "math":
                if kind == "plain" and re.search(r"\\[\[(]|\\begin\{", source):
                    raise ValueError("公式分隔符没有配对，请检查 \\(…\\)、\\[…\\] 或 $$…$$。")
                markup.append(escape(source).replace("\n", "<br/>"))
                continue
            self._count += 1
            contains_math = True
            if self._count > MAX_FORMULAS:
                raise ValueError("本次导出的公式过多，请分批导出。")
            key = (source, style.fontSize, max_width)
            if key not in self._images:
                self._images[key] = _formula_image(*key)
                _, width, height, _ = self._images[key]
                self._pixels += width * height * (DPI / 72) ** 2
                if self._pixels > MAX_TOTAL_PIXELS:
                    raise ValueError("本次公式排版量过大，请分批导出。")
            uri, width, height, baseline = self._images[key]
            if display and markup and not markup[-1].endswith("<br/>"):
                markup.append("<br/>")
            markup.append(f'<img src="{uri}" width="{width:.3f}" height="{height:.3f}" valign="{-baseline:.3f}"/>')
            if display:
                markup.append("<br/>")
        if contains_math:
            # ReportLab's CJK breaker calls ord() on empty inline-image
            # fragments when an image overflows a line or English backtracking
            # crosses it. Use its image-aware word breaker for mixed content.
            # Long Chinese runs can still wrap, and the caller's shared style
            # must not change for other paragraphs or simultaneous exports.
            style = ParagraphStyle(
                style.name + "MathImages", parent=style, wordWrap="LTR",
                splitLongWords=1, autoLeading="max",
            )
        return Paragraph("".join(markup), style)
