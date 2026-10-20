"""Project-local, embedded Chinese font for PDF export on any host OS."""
from pathlib import Path
from threading import Lock


FONT_PATH = Path(__file__).resolve().parent / "fonts" / "NotoSansSC-Regular.ttf"
FONT_NAME = "WizPracticePDFCJK"
_FONT_LOCK = Lock()


def get_pdf_font_name():
    # Do not silently emit an unreadable PDF when a deploy omits this asset.
    if not FONT_PATH.is_file():
        raise RuntimeError("PDF 中文字体缺失，请将 fonts/NotoSansSC-Regular.ttf 随项目一起部署。")

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Load/register once per worker, including concurrent export requests.
    # ReportLab embeds a document-specific subset in each resulting PDF.
    with _FONT_LOCK:
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
            except Exception as exc:
                raise RuntimeError("PDF 中文字体加载失败，请检查打包字体是否完整可读。") from exc
    return FONT_NAME
