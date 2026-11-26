"""WizPractice study agent: material ingestion, question generation and tutoring."""
from openai import OpenAI
from dotenv import load_dotenv
from document_loader import load_documents, read_txt, read_pdf, read_docx
from exam_import import ExamImportError, parse_model_questions, split_numbered_questions, question_type
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import os
import sys
import shutil
import json
import base64
import mimetypes
import tempfile
from datetime import datetime
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import threading

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

_USER_BUILD_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def get_user_build_lock(user_key: str):
    with _LOCKS_GUARD:
        if user_key not in _USER_BUILD_LOCKS:
            _USER_BUILD_LOCKS[user_key] = threading.Lock()
        return _USER_BUILD_LOCKS[user_key]

def configure_tesseract():
    """
    配置 Tesseract 路径：
    1. 优先读取环境变量 TESSERACT_CMD
    2. 如果没配，则尝试从系统 PATH 中查找 tesseract
    3. 如果还找不到，返回 False
    """
    env_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if env_cmd:
        if os.path.isfile(env_cmd):
            pytesseract.pytesseract.tesseract_cmd = env_cmd
            print(f"✅ 使用环境变量中的 Tesseract: {env_cmd}")
            return True
        else:
            print(f"⚠️ TESSERACT_CMD 已设置，但路径不存在: {env_cmd}")

    system_cmd = shutil.which("tesseract")
    if system_cmd:
        pytesseract.pytesseract.tesseract_cmd = system_cmd
        print(f"✅ 使用系统 PATH 中的 Tesseract: {system_cmd}")
        return True

    print("⚠️ 未找到 Tesseract，可继续运行，但 OCR 功能不可用。")
    return False


VECTOR_STORE_DIR = "vector_store"
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# -------------------
# 0️⃣ 环境变量加载
# -------------------
print("🔧 正在加载环境变量...")
load_dotenv()

TESSERACT_AVAILABLE = configure_tesseract()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ 未检测到 OPENAI_API_KEY，请检查 .env 文件！")
else:
    print("✅ 已加载 OPENAI_API_KEY。")


client = OpenAI(api_key=api_key)


class RagAgent:
    LOG_PATH = "student_logs/questions_log.json"
    EXAM_DB_PATH = os.path.join("exam_db", "past_exams.json")

    def __init__(self, client, db, exam_db_path=None):
        self.client = client
        self.db = db

        if exam_db_path:
            self.exam_db_path = exam_db_path
        else:
            self.exam_db_path = self.EXAM_DB_PATH

    def ensure_db_loaded(self, user_id=None):
        """
        懒加载知识库：
        - 如果 self.db 已经存在，直接返回 True
        - 如果传了 user_id，则尝试从磁盘加载该用户的向量库
        - 否则返回 False
        """
        if self.db is not None:
            return True

        if user_id:
            try:
                return self.load_or_create_db(user_id)
            except Exception as e:
                print(f"⚠️ ensure_db_loaded 失败: {e}")
                return False

        return False

    def load_or_create_db(self, user_id):
        """
        启动时从磁盘加载向量库，避免重建并保证多 Gunicorn worker 共享。
        """
        index_path = os.path.join(VECTOR_STORE_DIR, user_id)

        if os.path.exists(index_path):
            try:
                embeddings = OpenAIEmbeddings()
                self.db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
                print(f"📁 已从磁盘加载向量库: {index_path}")
                return True
            except Exception as e:
                print(f"⚠️ 加载失败，需重新构建：{e}")

        print("⚠️ 未找到向量库，请上传资料构建。")
        return False

    # ---- 📚 过往试卷题目数据库 ----

    def _load_exam_db(self):
        """
        从本地 JSON 文件加载过往试卷题目。
        返回值始终为 list[dict]，即使文件不存在或格式不标准。
        """
        # ★ 关键：优先使用实例自己的 exam_db_path
        path = getattr(self, "exam_db_path", self.EXAM_DB_PATH)

        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ [load_exam_db] 读取过往试卷数据库失败: {e}")
            return []

        # 兼容两种格式：{"questions":[...]} 或直接 [ ... ]
        if isinstance(data, dict):
            return data.get("questions", [])
        if isinstance(data, list):
            return data
        return []

    def _save_exam_db(self, questions):
        """
        把题目列表写回本地 JSON 文件。
        """
        # ★ 同样使用实例级别的路径
        path = getattr(self, "exam_db_path", self.EXAM_DB_PATH)

        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder or ".", suffix=".tmp", delete=False) as f:
                temp_path = f.name
                json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
        except Exception as e:
            print(f"⚠️ [save_exam_db] 保存失败: {type(e).__name__}")
            raise ExamImportError("storage", "题目已解析，但保存题库失败，请检查目录写入权限后重试。") from e
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)


    def list_past_exam_questions(self):
        """
        返回当前所有过往试卷题目。
        """
        return self._load_exam_db()

    def delete_past_exam_question(self, question_id=None, question_text=None):
        """
        从数据库中删除题目（你要的“删除数据库内相关资料的方法”）：
        - 优先使用 question_id 精确删除；
        - 若未提供 id，则按完整 question_text 匹配删除。
        返回删除的条目数量。
        """
        db = self._load_exam_db()
        if question_id is not None:
            try:
                qid = int(question_id)
            except Exception:
                raise ValueError("question_id 必须是整数。")
            new_db = [item for item in db if item.get("id") != qid]
        elif question_text:
            q_text = question_text.strip()
            new_db = [item for item in db if item.get("question") != q_text]
        else:
            raise ValueError("必须提供 question_id 或 question_text。")

        deleted = len(db) - len(new_db)
        if deleted > 0:
            self._save_exam_db(new_db)
        return deleted

    def _extract_questions_from_text(
                self,
                raw_text: str,
                default_question_type: str = "short_answer",
                source_name: str = "",
        ):
            """
            调用大模型，把一整份试卷文本拆分为若干条结构化题目，并写入本地 JSON 题库。
            返回解析后的题目记录列表。
            """
            if not raw_text or not raw_text.strip():
                raise ExamImportError("text", "文件未读取到有效文字，请检查文件是否损坏或需要文字识别。")

            snippet = raw_text.strip()

            prompt = f"""
    You will receive the plain text of a university exam paper (source file: {source_name}).

    1. Identify every explicit exam question that students need to answer.
    2. Ignore headers, page numbers, and instructions such as "Answer any 2 questions".
    3. For each question, output a JSON object with:
       - "question": full question text (keep the original language).
       - "question_type": one of ["fill_blank", "multiple_choice", "short_answer"].
       - "meta": an object with optional fields like "source_file", "index", "year", "paper".

    Return ONLY a JSON array, for example:

    [
      {{
        "question": "Explain the difference between circuit switching and packet switching.",
        "question_type": "short_answer",
        "meta": {{"source_file": "2023-final.pdf", "index": "Q1"}}
      }}
    ]

    Exam text:
    \"\"\"{snippet}\"\"\"
    """

            data = []
            model_issue = ""
            try:
                if len(snippet) > 24000:
                    raise ValueError("paper_too_long_for_single_model_request")
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You extract structured exam questions from raw exam papers and respond ONLY with JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    timeout=60,
                    max_tokens=6000,
                )
                content = response.choices[0].message.content
                if getattr(response.choices[0], "finish_reason", None) != "length":
                    data = parse_model_questions(content)
                if not data:
                    model_issue = "模型返回为空或格式不完整"
            except Exception as e:
                model_issue = "模型请求失败或试卷超过单次解析长度"
                print(f"⚠️ 试卷模型解析未完成: {type(e).__name__}")

            used_fallback = not data
            if used_fallback:
                data = split_numbered_questions(raw_text, default_question_type)
            if not data:
                raise ExamImportError("questions", "已读取到文字，但无法识别题目。模型解析未完成，按题号提取也未找到有效题目；请检查模型服务或试卷题号格式。")

            added = []
            for idx, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    continue
                q_text = str(item.get("question", "")).strip()
                if not q_text:
                    continue

                q_type = item.get("question_type")
                if q_type not in {"fill_blank", "multiple_choice", "short_answer"}:
                    q_type = question_type(q_text, default_question_type)
                meta = item.get("meta") or {}
                if not isinstance(meta, dict):
                    meta = {}

                # 补充一些默认元数据
                if source_name and "source_file" not in meta:
                    meta["source_file"] = source_name
                if "index" not in meta:
                    meta["index"] = f"Q{idx}"
                meta["extraction_method"] = "numbered_text" if used_fallback else "model"

                record = {**meta, "question": q_text, "question_type": q_type}
                added.append(record)

            # Save an entire import once, so a failed write cannot leave half a paper.
            lock_key = "exam:" + str(getattr(self, "exam_db_path", self.EXAM_DB_PATH))
            with get_user_build_lock(lock_key):
                existing = self._load_exam_db()
                next_id = max((item.get("id", 0) for item in existing), default=0) + 1
                for offset, record in enumerate(added):
                    record["id"] = next_id + offset
                self._save_exam_db(existing + added)
            self.last_exam_import = {"text_chars": len(raw_text), "method": "numbered_text" if used_fallback else "model",
                                     "warnings": ([model_issue + "，已按题号提取。请核对图表及跨页题干，必要时补充图片信息。"] if used_fallback else [])}
            return added

            # =======================
            # 🔍 OCR 工具函数
            # =======================

    def _ocr_image_to_text(self, file_path: str) -> str:
        """对单张图片做 OCR，返回识别出的文字"""
        if Image is None or pytesseract is None:
            print("⚠️ 未安装 Pillow / pytesseract，无法对图片做 OCR。")
            return ""

        if not TESSERACT_AVAILABLE:
            print("⚠️ Tesseract 未安装或未正确配置，无法对图片做 OCR。")
            return ""

        try:
            img = Image.open(file_path)
        except Exception as e:
            print(f"⚠️ 打开图片失败: {file_path}, error={e}")
            return ""

        try:
            text = pytesseract.image_to_string(img, lang="eng")
            return text
        except Exception as e:
            print(f"⚠️ 对图片做 OCR 失败: {file_path}, error={e}")
            return ""

    def _image_to_data_url(self, file_path: str) -> str:
        mime = mimetypes.guess_type(file_path)[0] or "image/png"
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def _describe_image_with_gpt(self, file_path: str, source_hint: str = "") -> str:
        """
        Convert image-only learning material into searchable text using GPT vision.
        The returned text is stored in the existing vector store; no image files are copied.
        """
        if not os.path.exists(file_path):
            return ""

        prompt = (
            "Analyze this image as study or exam material. Extract all visible text, "
            "describe diagrams, charts, maps, geometry figures, artwork, labels, symbols, "
            "and layout. Identify likely knowledge points and write concise observations "
            "that can be used to generate questions. If this is an exam page, preserve "
            "each question as fully as possible. Respond in the dominant language of the image."
        )
        if source_hint:
            prompt += f"\nSource: {source_hint}"

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": self._image_to_data_url(file_path)}},
                        ],
                    }
                ],
                temperature=0,
                max_tokens=900,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ GPT vision image analysis failed: {file_path}, error={e}")
            return ""

    def _describe_pdf_with_gpt_vision(self, file_path: str, max_pages: int = 4) -> str:
        """Analyze the first pages of an image-heavy PDF with GPT vision."""
        try:
            pages = convert_from_path(file_path, dpi=150, first_page=1, last_page=max_pages)
        except Exception as e:
            print(f"⚠️ PDF to image failed for GPT vision: {file_path}, error={e}")
            return ""

        descriptions = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, page in enumerate(pages, start=1):
                image_path = os.path.join(tmpdir, f"page_{i}.png")
                try:
                    page.save(image_path, "PNG")
                    desc = self._describe_image_with_gpt(
                        image_path,
                        source_hint=f"{os.path.basename(file_path)} page {i}",
                    )
                    if desc:
                        descriptions.append(f"[Page {i} visual analysis]\n{desc}")
                except Exception as e:
                    print(f"⚠️ GPT vision failed on PDF page {i}: {e}")
        return "\n\n".join(descriptions)

    def _ocr_pdf_to_text(self, file_path: str) -> str:
        """
        对纯图片 PDF 做 OCR：
        先把每一页转成图片，再用 Tesseract 识别，最后拼接成一个大文本。
        """
        if convert_from_path is None or Image is None or pytesseract is None:
            print("⚠️ 未安装 pdf2image / Pillow / pytesseract，无法对 PDF 做 OCR。")
            return ""

        if not TESSERACT_AVAILABLE:
            print("⚠️ Tesseract 未安装或未正确配置，无法对 PDF 做 OCR。")
            return ""

        try:
            pages = convert_from_path(file_path, dpi=200)
        except Exception as e:
            print(f"⚠️ 无法把 PDF 转成图片: {file_path}, error={e}")
            return ""

        all_texts = []
        for i, page in enumerate(pages, start=1):
            try:
                page_text = pytesseract.image_to_string(page, lang="eng")
                if page_text and page_text.strip():
                    all_texts.append(page_text)
            except Exception as e:
                print(f"⚠️ 第 {i} 页 OCR 失败: {file_path}, error={e}")

        joined = "\n\n".join(all_texts)
        if not joined.strip():
            print(f"⚠️ PDF OCR 后仍然没有有效文本: {file_path}")
        return joined

    def import_past_exam_from_file(
            self,
            file_path: str,
            default_question_type: str = "short_answer",
        ):
        """
        从单个“往年试卷文件”中自动抽取题目并写入 EXAM_DB_PATH。

        ✅ 新增：
        - 支持 png/jpg 等图片：用 OCR 把题目转成文本。
        - 对 PDF：如果 PyPDF2 没读出文本，则退回 OCR 方式。

        返回解析后的题目记录列表。
        """
        if not os.path.exists(file_path):
            raise ExamImportError("read", "上传文件不存在，请重新上传。")

        self.last_exam_import = {"attempts": []}
        attempts = self.last_exam_import["attempts"]

        ext = os.path.splitext(file_path)[1].lower()
        text = ""

        try:
            # 1) 纯文本类型
            if ext in [".txt", ".md"]:
                text = read_txt(file_path)

            # 2) PDF：先尝试正常提取文本，提不到时再 OCR
            elif ext == ".pdf":
                attempts.append("pdf_text")
                try:
                    text = read_pdf(file_path)
                except Exception as e:
                    print(f"⚠️ PDF 文字读取失败: {type(e).__name__}")
                    text = ""
                if not text or not text.strip():
                    attempts.append("ocr")
                    print(f"⚠️ PDF {file_path} 没有可提取的文本，尝试 OCR 方式...")
                    text = self._ocr_pdf_to_text(file_path)
                if not text or not text.strip():
                    attempts.append("vision")
                    print(f"PDF text/OCR extraction returned empty; trying GPT vision: {file_path}")
                    text = self._describe_pdf_with_gpt_vision(file_path)

            # 3) Word 文档
            elif ext == ".docx":
                text = read_docx(file_path)

            # 4) 常见图片格式：直接 OCR
            elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
                attempts.extend(["ocr", "vision"])
                print(f"ℹ️ 检测到图片试卷，将使用 OCR 识别: {file_path}")
                text = self._ocr_image_to_text(file_path)
                vision_text = self._describe_image_with_gpt(file_path, source_hint=os.path.basename(file_path))
                if vision_text and vision_text not in text:
                    text = (text + "\n\n[GPT vision description]\n" + vision_text).strip()

            # 5) 其他类型：先尝试按文本打开；有需要也可以扩展成 OCR
            else:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    text = ""

        except Exception as e:
            print(f"⚠️ 文件读取失败: {type(e).__name__}")
            raise ExamImportError("read", "文件内容读取失败，请检查文件格式是否有效、文件是否损坏。") from e

        if not text or not text.strip():
            print(f"⚠️ 文件内容为空或无法解析为文本，跳过：{file_path}")
            raise ExamImportError("text", "未读取到有效文字。请检查文字识别依赖和模型服务是否可用，或上传可复制文字的 PDF / Word / 文本文件。")

        source_name = os.path.basename(file_path)
        result = self._extract_questions_from_text(
            raw_text=text,
            default_question_type=default_question_type,
            source_name=source_name,
        )
        self.last_exam_import["attempts"] = attempts
        return result


    # ---- 🧾 提问日志系统 ----
    def log_question(self, user_query, reply):
        """保存学生提问记录"""
        os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": user_query,
            "answer": reply
        }

        try:
            if os.path.exists(self.LOG_PATH):
                with open(self.LOG_PATH, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(log_entry)

            with open(self.LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"⚠️ 日志保存失败: {e}")


            # ---- 🧪 期末复习出题 ----

            # ---- 🧪 Final exam question generation ----

    def generate_questions(
            self,
            query: str,
            question_type: str,
            num_questions: int = 5,
            difficulty: str = "medium",
            selected_docs=None,
            selected_exam_ids=None,
            style_template_only: bool = False,
    ) -> str:
        """
        Generate final-exam practice questions from uploaded course materials. When
        ``style_template_only`` is enabled, selected past-exam questions define the
        paper's format only; they must never contribute factual question content.

        ✅ 新增规则：
        - 如果左侧 Knowledge Base 没有勾选任何文献，右侧“过往试卷题库”勾选了题目，
          则完全只依据这些勾选的试卷题目出题（不再从知识库检索课件内容）。
        """

        # 0️⃣ 参数归一化
        if selected_docs is None:
            selected_docs = []
        exam_id_list = selected_exam_ids or []
        style_template_only = bool(style_template_only)

        if style_template_only and (not selected_docs or not exam_id_list):
            return (
                "⚠️ Template mode requires both selected Knowledge Base materials "
                "and selected model-paper questions."
            )

        # 双保险：两边都没选就直接拒绝
        if (not selected_docs) and (not exam_id_list) and not (query or "").strip():
            return (
                "⚠️ 当前没有勾选任何资料或过往试卷题目，"
                "请在界面右侧勾选后再点击“生成试题”。"
            )

        # 是否进入「只用过往试卷题目」模式：
        # 👉 Knowledge Base 完全没勾选，但过往试卷题库勾选了题目
        exam_only_mode = (not selected_docs) and bool(exam_id_list) and not style_template_only

        # 1️⃣ 统一题型
        type_map = {
            "fill": "fill_blank",
            "fill_blank": "fill_blank",
            "blank": "fill_blank",
            "gap": "fill_blank",
            "choice": "multiple_choice",
            "mcq": "multiple_choice",
            "multiple_choice": "multiple_choice",
            "short": "short_answer",
            "short_answer": "short_answer",
        }
        raw_types = question_type if isinstance(question_type, list) else str(question_type or "").split(",")
        selected_types = []
        for raw_type in raw_types:
            mapped = type_map.get(str(raw_type or "").strip().lower())
            if mapped and mapped not in selected_types:
                selected_types.append(mapped)
        if not selected_types:
            selected_types = ["fill_blank"]
        qt = selected_types[0]

        # 2️⃣ 题目数量归一化
        try:
            n = int(num_questions)
        except (TypeError, ValueError):
            n = 5
        n = max(1, min(n, 50))  # 限制在 1~50

        difficulty_map = {
            "low": (
                "Low difficulty: generate foundation-level questions. Focus on direct recall, "
                "basic definitions, simple recognition, and one-step application. Avoid tricky wording."
            ),
            "medium": (
                "Medium difficulty: generate standard university practice questions. Include a mix of "
                "recall and application, require students to connect 1-2 related concepts, and keep wording clear."
            ),
            "high": (
                "High difficulty: generate challenging questions. Require deeper reasoning, comparison, "
                "multi-step application, transfer to less familiar scenarios, and for multiple-choice questions use plausible distractors."
            ),
        }
        difficulty_key = (difficulty or "medium").strip().lower()
        difficulty_hint = difficulty_map.get(difficulty_key, difficulty_map["medium"])

        combined_context = ""
        results = []

        # 3️⃣ 如果不是“只用过往试卷题目”模式，就正常从知识库检索
        if selected_docs:
            # ⭐ 先判断向量库是不是空的
            if self.db is None:
                return ("⚠️ The local knowledge base is currently empty.\n"
                        "Please upload course materials on the right first.，"
                        "Then click Rebuild Knowledge Base or upload the files again.")

            search_query = query or "Final exam key points"
            try:
                results = self.db.similarity_search_with_score(search_query, k=80)
                print(f"✅ 从向量数据库检索到 {len(results)} 个片段。")
            except Exception as e:
                return f"⚠️ 无法从知识库检索内容，请检查 materials 是否正确建立：{e}"

            # 3.1️⃣ 如有勾选文献，则按文件名过滤
            if selected_docs:
                selected_norm = [s.strip().lower() for s in selected_docs]
                filtered = []
                for doc, score in results:
                    src = str(doc.metadata.get("source", "")).strip().lower()
                    base = os.path.basename(src)
                    if base in selected_norm or any(sel in src for sel in selected_norm):
                        filtered.append((doc, score))
                results = filtered
                print(f"✅ 根据勾选的文献过滤后剩余 {len(results)} 个片段。")

                if not results:
                    return (
                        "⚠️ Generation failed due to a server issue.. "
                        "Please click the button again."
                    )

            # 3.2️⃣ 完全没有文档
            if not results:
                return (
                    "⚠️ No documents are available in the knowledge base. "
                    "Please upload course slides or notes first."
                )

            # 4️⃣ 选出最相关的若干文本块
            threshold = 0.35
            relevant_docs = [doc for doc, score in results if score < threshold]
            if len(relevant_docs) < 5:
                relevant_docs = [doc for doc, score in results[:20]]

            combined_context = "\n\n".join(
                [
                    f"Source: {d.metadata.get('source', 'unknown')}\n{d.page_content}"
                    for d in relevant_docs
                ]
            )
            if len(combined_context) > 6000:
                combined_context = combined_context[:6000] + "\n...[truncated context]"

        # 4.1️⃣ 读取 & 过滤“过往试卷题库”
        past_exam_items = self._load_exam_db() if exam_id_list else []

        if exam_id_list:
            try:
                selected_set = {int(x) for x in exam_id_list if x is not None}
            except Exception:
                selected_set = set()

            if selected_set:
                filtered_items = []
                for item in past_exam_items:
                    try:
                        item_id = int(item.get("id", -1))
                    except Exception:
                        item_id = -1
                    if item_id in selected_set:
                        filtered_items.append(item)

                # 如果过滤后不是空，就用过滤后的题目
                if filtered_items:
                    past_exam_items = filtered_items
                elif style_template_only:
                    return (
                        "⚠️ The selected paper-template questions could not be found. "
                        "Please reselect or re-upload the model paper."
                    )

        # 4.2️⃣ 若处于「只用过往试卷题目」模式，用这些题目本身构建“知识上下文”
        if exam_only_mode:
            if not past_exam_items:
                return (
                    "⚠️ The selected past exam question could not be found in the database，"
                    "Please reselect or re-upload the exam file from the right panel."
                )

            lines_ctx = []
            for i, item in enumerate(past_exam_items, start=1):
                q_text = str(item.get("question", "")).strip()
                if not q_text:
                    continue
                meta = item.get("meta") or {}
                extra_tags = []
                year = meta.get("year")
                paper = meta.get("paper") or meta.get("source_file")
                if year:
                    extra_tags.append(str(year))
                if paper:
                    extra_tags.append(str(paper))
                tag_str = f" ({', '.join(extra_tags)})" if extra_tags else ""
                lines_ctx.append(f"Past exam Q{i}{tag_str}: {q_text}")

            combined_context = "\n".join(lines_ctx)
            if len(combined_context) > 6000:
                combined_context = (
                    combined_context[:6000]
                    + "\n...[truncated context from past exams]"
                )

        # 4.3️⃣ 构造“风格示例”（不论是否 exam_only_mode 都可以给模型看）
        exam_examples = ""
        template_blueprint = ""
        if past_exam_items:
            samples = past_exam_items[-10:]  # 只取最近 10 条避免太长
            lines_exam = []
            for i, item in enumerate(samples, start=1):
                q_text = str(item.get("question", "")).strip()
                if not q_text:
                    continue
                q_type = (item.get("question_type") or "").strip()
                prefix = f"Past Q{i}"
                if q_type:
                    prefix += f" ({q_type})"
                lines_exam.append(f"{prefix}: {q_text}")
            if lines_exam:
                exam_examples = "\n".join(lines_exam)
                if len(exam_examples) > 2000:
                    exam_examples = (
                        exam_examples[:2000] + "\n...[truncated exam examples]"
                    )

        if style_template_only:
            template_types = [
                str(item.get("question_type") or "short_answer").strip()
                for item in past_exam_items
                if str(item.get("question") or "").strip()
            ]
            sequence = " → ".join(template_types[:20]) or "short_answer"
            template_blueprint = (
                f"The selected paper contains {len(template_types)} extracted questions. "
                f"Its question-type sequence is: {sequence}. "
                "For this generated paper, preserve that relative type order by taking "
                "or cycling the sequence as needed to reach the requested question count."
            )

        # 5️⃣ 题型说明（英文）
        type_desc_map = {
            "fill_blank": (
                "fill-in-the-blank questions that require students to recall key terms, "
                "formulas or short phrases."
            ),
            "multiple_choice": (
                "single-choice questions with 4 options (A, B, C, D), where exactly one "
                "option is clearly correct."
            ),
            "short_answer": (
                "short-answer questions that can be reasonably answered in 2–5 sentences."
            ),
        }
        if len(selected_types) > 1:
            type_desc = (
                "a balanced mix of these question types: "
                + ", ".join(type_desc_map.get(item, item) for item in selected_types)
            )
        else:
            type_desc = type_desc_map.get(qt, "fill-in-the-blank questions.")

        # 6️⃣ 针对不同模式，给模型的强约束提示
        if exam_only_mode:
            mode_hint = (
                "- The 'Source materials' below are ONLY the past exam questions that the student selected.\n"
                "      - You MUST generate new questions that test the **same or very closely related concepts** "
                "as these past exam questions.\n"
                "      - Do NOT switch to unrelated chapters or topics that are not obviously connected to these questions."
            )
        elif style_template_only:
            mode_hint = (
                "- The 'Source materials' below are the ONLY source of factual content, concepts, examples, and answerable knowledge.\n"
                "      - The 'Past exam question examples' are a PAPER-STYLE TEMPLATE ONLY.\n"
                "      - Do NOT test, reuse, paraphrase, or infer any topic, case, name, number, or answer from the template questions.\n"
                "      - Copy only the paper's structural features: section rhythm, question-type sequence, numbering, wording pattern, cognitive demand, and option/answer format."
            )
        elif selected_docs:
            mode_hint = (
                "- The 'Source materials' below are knowledge snippets retrieved from the selected course materials.\n"
                "      - When 'Past exam question examples' are provided, use them ONLY as style/difficulty references; "
                "all factual content must still be grounded in 'Source materials'."
            )
        else:
            combined_context = query
            mode_hint = (
                "- No Knowledge Base file is selected. Use any supplied study text as the factual source.\n"
                "      - If the instruction supplies only a topic, generate general practice for that topic using established knowledge."
            )

        # 7️⃣ Prompt
        prompt = f"""
    You are an exam-preparation question generator for university students.

    [STRICT REQUIREMENTS]
    - Write questions in the same language as the user's instruction. If the user does not specify a language, use the dominant language of the source materials.
    - Base every question strictly on the context below. Do NOT introduce content that is not supported by the context.
    {mode_hint}
    - Default question type: {type_desc}
    - Default number of questions: {n} (valid range 1–50).
    - Default difficulty setting: {difficulty_key}
      {difficulty_hint}
    - The user's explicit requested type, count (clamped to 1–50), difficulty and scope override these defaults. Use defaults only for unspecified fields.
    - Label EVERY question with its actual type, e.g. Q1 [multiple_choice], Q2 [fill_blank], Q3 [short_answer].
    - Do NOT provide answers or solutions, only the questions themselves.
    - Clearly separate GIVEN conditions from the UNKNOWN being tested. Never ask a student to fill a value/term that the stem already explicitly supplies.
    - For numerical questions, ask for a meaningful derived quantity; e.g. radius 3 -> quarter-circle area ____, NOT radius 3 -> fill the radius in the area formula.
    - Ensure sufficient stated conditions, correct formulas/units, and a determinate answer for every objective blank. Do not reference an absent diagram.
    - Each multiple-choice question must have exactly one correct option. Short-answer questions must have assessable marking points, but may allow equivalent wording/examples.
    - Use clear numbering: Q1, Q2, Q3, ...
    - When possible, generate questions that are similar in style and difficulty
      to the past exam questions provided, but do NOT copy them verbatim.
    - If past exam examples are provided, imitate their question format, wording pattern,
      cognitive demand, and answer style while changing the concrete content.
    {"- Template blueprint: " + template_blueprint if template_blueprint else ""}

    [User's instruction / exam scope]
    {query}

    [Past exam question examples]
    {exam_examples or "(no past exam questions are currently stored)"}

    [Source materials]
    {combined_context}
    """

        from question_quality import QuestionQualityError, generate_reviewed_questions

        try:
            content = generate_reviewed_questions(
                self.client,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate high-quality final-exam practice questions "
                            "based strictly on the given course materials or past exam questions. "
                            "Use the user's language unless a different language is explicitly requested. "
                            "Never include answers, solutions or review notes in student questions. "
                            "Do not reveal a requested unknown as a given condition."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                review_scope={
                    "instruction": query, "default_count": n,
                    "default_types": selected_types, "default_difficulty": difficulty_key,
                    "source_policy": (
                        "Selected past questions define the factual scope; generate new related problems."
                        if exam_only_mode else
                        "Only selected course materials are factual sources; paper templates define STYLE ONLY."
                        if style_template_only or selected_docs else
                        "Use supplied study text, or established knowledge if only a topic is supplied."
                    ),
                    "course_context": combined_context,
                    "style_blueprint": template_blueprint,
                },
            )
            # 出题日志（可选）
            self.log_question(f"[Question Generation] {query}", content)
            return content
        except QuestionQualityError as exc:
            return f"❌ {exc}"
        except Exception as e:
            print(f"Question generation failed ({type(e).__name__})")
            return "❌ 出题或审题服务暂时不可用，本次未保存题目，请稍后重试。"


    def grade_answer(self,
                         question: str,
                         student_answer: str,
                         question_type: str = "short_answer",
                         selected_docs=None) -> str:
            """
            使用向量知识库 + 大模型对单道试题进行批改。
            要求：只要学生答案在语义上与标准答案接近，也视为正确或部分正确。
            返回一段文本，首行给出评分结果，后面给出简短说明与参考答案。
            """
            if selected_docs is None:
                selected_docs = []

            question = (question or "").strip()
            student_answer = (student_answer or "").strip()

            if not question or not student_answer:
                return (
                    "Result: Incorrect\n"
                    "Brief explanation: The question text or your answer is empty, so I cannot grade it.\n"
                    "Reference answer: (Not available because there is no valid input.)"
                )

            # 1️⃣ 用题干在向量库中检索相关片段，作为批改的上下文
            context = ""
            try:
                results = self.db.similarity_search_with_score(question, k=30)
                # 如果前端勾选了特定文献，则做一次过滤（按文件名匹配）
                if selected_docs:
                    selected_norm = [s.strip().lower() for s in selected_docs]
                    filtered = []
                    for doc, score in results:
                        src = str(doc.metadata.get("source", "")).strip().lower()
                        base = os.path.basename(src)
                        if base in selected_norm or any(sel in src for sel in selected_norm):
                            filtered.append((doc, score))
                    results = filtered

                if results:
                    threshold = 0.4
                    relevant_docs = [doc for doc, score in results if score < threshold]
                    if len(relevant_docs) < 3:
                        # 如果按阈值筛出来太少，就取前 10 个
                        relevant_docs = [doc for doc, score in results[:10]]

                    context = "\n\n".join(
                        f"Source: {d.metadata.get('source', 'unknown')}\n{d.page_content}"
                        for d in relevant_docs
                    )
                    # 防止 prompt 过长
                    if len(context) > 4000:
                        context = context[:4000] + "\n...[truncated context]"
            except Exception as e:
                print("⚠️ [grade_answer] 检索上下文失败：", e)

            type_hint_map = {
                "fill_blank": "fill-in-the-blank question",
                "multiple_choice": "single-choice question",
                "short_answer": "short-answer question",
            }
            qt = type_hint_map.get((question_type or "").lower(), "exam question")

            system_msg = (
                "You are a strict but fair teaching assistant for a university course. "
                "You grade exam questions and accept answers that are semantically "
                "equivalent even if they use different wording. "
                "Reply in the same language as the question or student answer."
            )

            user_prompt = f"""
            You are grading ONE {qt}.

            [Question]
            {question}

            [Student Answer]
            {student_answer}

            [Course Context]
            {context}

            Instructions:
            - Decide whether the student's answer is **correct**, **partially correct**, or **incorrect**.
            - Treat answers with similar meaning or synonyms as correct, even if the wording is different.
            - If the answer covers most but not all key points, treat it as partially correct.
            - If the answer is wrong, missing key ideas, or irrelevant, treat it as incorrect.
            - In the explanation part, always use an encouraging and personalized tone:
              - Start the explanation with "Nice try！" or “Good attempt!:” or “Nice effort!:”.
              - First briefly affirm anything reasonable, related, or showing effort in the student's answer (even if the final result is wrong). If the answer is completely irrelevant or empty, still encourage politely.
              - Then clearly tell the student where their answer is incorrect, incomplete, or off-topic.
              - Finally, tell the student how they should answer in 1–2 sentences, giving concrete guidance (what key terms/steps must appear), and connect this guidance to their original answer when possible.

            Write your reply in the same language as the question or student answer with the following structure:

            Result: <Correct / Partially correct / Incorrect>
            Brief explanation: <1-3 sentences, starting with an encouraging phrase and then explaining what is missing or wrong and how to improve.>
            Reference answer: <a concise model answer>.
            """.strip()

            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = resp.choices[0].message.content.strip()
                return content
            except Exception as e:
                return (
                    "Result: Unknown\n"
                    f"Brief explanation: An error occurred during grading: {e}\n"
                    "Reference answer: (Not available due to an internal error.)"
                )

    def generate_scenario_question(
            self,
            question: str,
            student_answer: str = "",
            feedback: str = "",
            question_type: str = "short_answer",
            selected_docs=None,
    ) -> str:
        """
        根据某道“错误试题”，在保持核心考点不变的前提下，生成一个全新的情境迁移题干。

        参数：
            question        : 原始题目文本
            student_answer  : 学生原始作答（可选，用于帮助推断错误点）
            feedback        : 批改反馈文本（可选，里面通常有参考答案/错误原因）
            question_type   : 题型，如 "fill_blank" / "multiple_choice" / "short_answer"
            selected_docs   : 前端勾选的文献文件名列表，用于向量检索过滤

        返回：
            仅返回新的题干文本（不包含答案/解析）。
        """
        question = (question or "").strip()
        student_answer = (student_answer or "").strip()
        feedback = (feedback or "").strip()

        if not question:
            return "⚠️ 无法生成情景迁移题：原始题干为空。"

        if selected_docs is None:
            selected_docs = []

        # 1️⃣ 按原题在向量库中检索上下文，尽量锁定相关片段
        context = ""
        try:
            search_query = question
            results = self.db.similarity_search_with_score(search_query, k=40)

            # 如有勾选文献，对检索结果按文件名进行过滤（与 generate_questions / grade_answer 保持一致风格）
            if selected_docs:
                selected_norm = [s.strip().lower() for s in selected_docs]
                filtered = []
                for doc, score in results:
                    src = str(doc.metadata.get("source", "")).strip().lower()
                    base = os.path.basename(src)
                    if base in selected_norm or any(name in src for name in selected_norm):
                        filtered.append((doc, score))
                if filtered:
                    results = filtered

            top_docs = [d for d, _ in results[:8]]
            if top_docs:
                context = "\n\n".join(
                    f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
                    for d in top_docs
                )

            if len(context) > 4000:
                context = context[:4000] + "\n...[truncated context]"
        except Exception as e:
            print("⚠️ [generate_scenario_question] 检索上下文失败：", e)

        type_hint_map = {
            "fill_blank": "fill-in-the-blank exam question",
            "multiple_choice": "single-choice exam question",
            "short_answer": "short-answer exam question",
        }
        qt_key = (question_type or "").lower()
        type_hint = type_hint_map.get(qt_key, "exam question")

        system_msg = (
            "You are a university teaching assistant. "
            "Given an exam question that a student answered incorrectly, "
            "you must create a new practice question that assesses the SAME core concept "
            "but embeds it into a clearly different real-world scenario. "
            "The new question must be a fresh variation and should not copy the wording of the original question. "
            "Whenever possible, design the new question so that its correct answer is not exactly the same as the original reference answer "
            "(for example by changing numeric values, parameter values, or concrete entities) while still testing the same concept. "
            "Do NOT provide any solution or explanation. "
            "Only output the new question text."
        )

        user_prompt = f"""
    [Original Question]
    {question}

    [Student Answer]
    {student_answer or "(not provided)"}

    [Grading Feedback]
    {feedback or "(not provided)"}

    [Course Context]
    {context or "(no extra context)"}

    Your task:
    1. Infer the core knowledge point that this question is targeting.
    2. Rewrite ONE {type_hint} that tests the same concept but uses a clearly different scenario or story.
    3. Keep the difficulty roughly the same as the original question.
    4. Make sure the expected correct answer for the new question is different from the original reference answer shown in [Grading Feedback]
       (e.g., change numbers, parameter values, or concrete entities) while still examining the same concept.
    5. Output ONLY the new question text. Do NOT include the answer, explanation, or any extra commentary.
    """.strip()

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            new_question = response.choices[0].message.content.strip()
            if not new_question:
                return "⚠️ 模型未能生成情景迁移题，请稍后重试。"
            return new_question
        except Exception as e:
            print("⚠️ [generate_scenario_question] 调用大模型失败：", e)
            return f"⚠️ 无法生成情景迁移题：{e}"

    def answer_exam_question(
            self,
            user_message: str,
            questions=None,
            current_index=None,
            selected_docs=None,
    ) -> str:
        """
        回答学生就当前试题或已上传资料提出的问题。

        - user_message: 学生在“向 AI 提问”区域输入的问题
        - questions: 当前页面上的所有试题文本列表（字符串列表）
        - current_index: 当前所在题目的下标（0-based），用于给 AI 说明“当前这道题”
        - selected_docs: 前端勾选的材料文件名列表，用来做向量检索过滤
        """
        if selected_docs is None:
            selected_docs = []
        questions = questions or []

        base_query = (user_message or "").strip()
        if not base_query:
            return "⚠️ 提问内容为空。"

        # 1️⃣ 构造“考试题目”上下文
        exam_context = ""
        if isinstance(current_index, int) and 0 <= current_index < len(questions):
            q_text = str(questions[current_index] or "")
            exam_context = f"Current exam question (Q{current_index + 1}): {q_text}"
        elif questions:
            joined = "\n".join(
                f"Q{i + 1}: {str(q or '')}" for i, q in enumerate(questions)
            )
            exam_context = "Exam questions:\n" + joined

        # 用「学生问题 + 考试上下文」作为检索 query
        if exam_context:
            search_query = base_query + "\n\n" + exam_context
        else:
            search_query = base_query

        # 2️⃣ 在向量库中检索相关片段
        try:
            results = self.db.similarity_search_with_score(search_query, k=40)
            print(f"✅ [answer_exam_question] 检索到 {len(results)} 个候选片段。")
        except Exception as e:
            print("⚠️ [answer_exam_question] 检索失败：", e)
            results = []

        # 3️⃣ 如果前端勾选了特定文献，则按文件名过滤
        if selected_docs and results:
            selected_norm = [s.strip().lower() for s in selected_docs]
            filtered = []
            for doc, score in results:
                src = str(doc.metadata.get("source", "")).strip().lower()
                base = os.path.basename(src)
                if base in selected_norm or any(sel in src for sel in selected_norm):
                    filtered.append((doc, score))

            if filtered:
                results = filtered
                print(
                    f"✅ [answer_exam_question] 按勾选文献过滤后剩余 {len(results)} 个片段。"
                )
            else:
                print(
                    "⚠️ [answer_exam_question] 勾选文献过滤后无结果，将退回使用全部检索结果。"
                )

        if not results:
            return (
                "⚠️ No relevant content was found in the current knowledge base. "
                "Please try rephrasing your question or check whether the course materials have been uploaded."
            )

        # 4️⃣ 选出最相关的若干文本块
        threshold = 0.35
        relevant_docs = [doc for doc, score in results if score < threshold]
        if len(relevant_docs) < 3:
            relevant_docs = [doc for doc, score in results[:10]]

        combined_context = "\n\n".join(
            f"Source: {d.metadata.get('source', 'unknown')}\n{d.page_content}"
            for d in relevant_docs
        )
        if len(combined_context) > 6000:
            combined_context = combined_context[:6000] + "\n...[truncated context]"

        # 5️⃣ 构造给大模型的提示词
        system_msg = (
            "You are a helpful teaching assistant for university courses. "
            "You explain exam questions and key concepts clearly using the provided course materials. "
            "Respond in the same language as the student's question unless they explicitly ask for another language. "
            "When the student asks about a specific exam question, focus on that question but still "
            "ground your explanation in the course materials."
        )

        user_prompt = f"""
    [Student question]
    {base_query}

    [Exam question context]
    {exam_context or "(no explicit exam question was provided)"}

    [Course materials]
    {combined_context}
    """.strip()

        # 6️⃣ 调用大模型生成回答
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            answer_text = response.choices[0].message.content.strip()
        except Exception as e:
            return f"❌ 回答失败: {e}"

        # 7️⃣ 记录到提问日志（可选）
        try:
            self.log_question(base_query, answer_text)
        except Exception as e:
            print("⚠️ [answer_exam_question] 日志记录失败：", e)

        return answer_text

    def explain_question_detailed(
                self,
                question: str,
                student_answer: str = "",
                feedback: str = "",
                question_type: str = "",
                selected_docs=None,
        ) -> str:
            """
            精讲模式：
            针对某一道题，结合学生答案和批改反馈，
            给出中文的、分步骤的详细讲解（考点 + 解题思路 + 常见错误等）。
            """
            if selected_docs is None:
                selected_docs = []

            question = (question or "").strip()
            student_answer = (student_answer or "").strip()
            feedback = (feedback or "").strip()

            if not question:
                return "当前题目信息为空，无法进行精讲。"

            # 1️⃣ 用题干在向量库中检索相关片段
            search_query = question
            context = ""
            try:
                results = self.db.similarity_search_with_score(search_query, k=40)

                # 如果前端勾选了特定文献，则按文件名做一次过滤
                if selected_docs:
                    selected_norm = [s.strip().lower() for s in selected_docs]
                    filtered = []
                    for doc, score in results:
                        src = str(doc.metadata.get("source", "")).strip().lower()
                        base = os.path.basename(src)
                        if base in selected_norm or any(sel in src for sel in selected_norm):
                            filtered.append((doc, score))
                    if filtered:
                        results = filtered

                if results:
                    threshold = 0.35
                    relevant_docs = [doc for doc, score in results if score < threshold]
                    if len(relevant_docs) < 3:
                        relevant_docs = [doc for doc, score in results[:10]]

                    context = "\n\n".join(
                        f"Source: {d.metadata.get('source', 'unknown')}\n{d.page_content}"
                        for d in relevant_docs
                    )
                    if len(context) > 6000:
                        context = context[:6000] + "\n...[truncated context]"
            except Exception as e:
                print("⚠️ [explain_question_detailed] 检索上下文失败：", e)

            system_msg = (
                "You are an excellent university-level teaching assistant. "
                "The student has just answered an exam question but still feels confused. "
                "Provide a detailed yet clear explanation of the underlying concepts and "
                "solution steps, grounded in the given course materials. "
                "Respond in the same language as the question or student answer."
            )

            user_prompt = f"""
    [Exam question]
    {question}

    [Student answer]
    {student_answer or "(学生答案未提供)"}

    [Grading feedback]
    {feedback or "(暂无详细批改反馈，可只基于题目进行讲解)"}

    [Course materials]
    {context or "(知识库检索失败时，可仅根据题干给出一般性讲解)"}

    Please answer in the same language as the question/student answer and use the following structure:

1. Core concepts examined in this question (2–4 sentences).
2. Step-by-step solution explanation (bullet list; each step should explain WHY it is needed).
3. Common mistakes and misconceptions (if possible, relate them to the student's answer).
4. A small example or analogy to help the student build intuition.

Use clear, supportive language suitable for undergraduate students.
        """.strip()

            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                )
                answer_text = resp.choices[0].message.content.strip()
            except Exception as e:
                return f"❌ 精讲模式调用失败: {e}"

            # 可选：把精讲记录到日志
            try:
                self.log_question(
                    f"[EXPLAIN_MODE] {question}",
                    answer_text,
                )
            except Exception as e:
                print("⚠️ [explain_question_detailed] 日志记录失败：", e)

            return answer_text


    # ---- 📘 动态学习：重建整个知识库 ----
    def ingest_material(self, folder_path="materials"):
        """
        每次调用时：
        1. 重新读取 folder_path 下的所有文档；
        2. 重新分块；
        3. 重新构建当前用户自己的 FAISS 向量库；
        4. 保存到 vector_store/<user_id>；
        5. 只更新当前 agent 的 self.db，不再写全局 db。
        """
        print(f"📂 [ingest_material] 正在重新构建知识库: {folder_path}")

        # 从 folder_path 推断当前用户的库目录名
        # 例如 materials/user_a1b2c3d4 -> user_a1b2c3d4
        user_key = os.path.basename(folder_path.rstrip(os.sep)) or "default"

        # 每个用户一个独立锁，防止同一用户并发重建自己的库
        build_lock = get_user_build_lock(user_key)

        if not build_lock.acquire(blocking=False):
            return "⚠️ 当前用户的知识库正在构建中，请稍后再试。"

        try:
            # 1️⃣ 读取资料
            try:
                docs = load_documents(folder_path)
            except Exception as e:
                msg = f"❌ 读取资料失败：{e}"
                print(msg)
                self.db = None
                return msg

            image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
            for name in os.listdir(folder_path):
                path = os.path.join(folder_path, name)
                if os.path.isdir(path):
                    continue
                ext = os.path.splitext(name)[1].lower()
                try:
                    if ext in image_exts:
                        ocr_text = self._ocr_image_to_text(path)
                        vision_text = self._describe_image_with_gpt(path, source_hint=name)
                        combined = "\n\n".join(
                            part for part in [ocr_text, vision_text] if part and part.strip()
                        )
                        if combined:
                            docs[name] = combined
                    elif ext == ".pdf" and (not docs.get(name) or not docs.get(name, "").strip()):
                        vision_text = self._describe_pdf_with_gpt_vision(path)
                        if vision_text:
                            docs[name] = vision_text
                except Exception as e:
                    print(f"⚠️ Multimodal material extraction failed: {name}, error={e}")

            if not docs:
                msg = f"❌ 未找到任何可用文件（目录：{folder_path}）。"
                print(msg)
                self.db = None
                return msg

            # 2️⃣ 组装 LangChain 的 Document
            all_docs = [
                Document(page_content=text, metadata={"source": name})
                for name, text in docs.items()
            ]

            # 3️⃣ 分块
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            chunks = splitter.split_documents(all_docs)
            print(f"✂️ [ingest_material] 分块完成，本次共 {len(chunks)} 个文本块。")

            if not chunks:
                msg = "⚠️ 文档解析后没有任何可用文本块，知识库为空。"
                print(msg)
                self.db = None
                return msg

            # 4️⃣ 构建当前用户自己的向量库
            try:
                embeddings = OpenAIEmbeddings()
                new_db = FAISS.from_documents(chunks, embeddings)

                # 5️⃣ 保存到当前用户自己的向量库目录
                index_path = os.path.join(VECTOR_STORE_DIR, user_key)
                os.makedirs(index_path, exist_ok=True)
                new_db.save_local(index_path)
                print(f"💾 已保存向量库到: {index_path}")

                # 6️⃣ 只更新当前 agent 的 self.db
                self.db = new_db

            except Exception as e:
                msg = f"❌ 构建向量数据库失败：{e}"
                print(msg)
                self.db = None
                return msg

            msg = f"✅ 知识库已重建：{len(docs)} 个文件，{len(chunks)} 个文本块。"
            print(msg)

            try:
                self.log_question("ingest_material(rebuild)", msg)
            except Exception as e:
                print(f"⚠️ 记录日志失败：{e}")

            return msg

        finally:
            build_lock.release()


    def summarize_wrong_questions(self, wrong_items: list) -> str:
            """
            根据一轮答题中学生的错误试题，给出本轮需要加强的知识点和学习建议。
            wrong_items: 来自前端的列表，每个元素大致是：
                {
                    "index": int,
                    "question": str,
                    "student_answer": str,
                    "feedback": str,
                    "question_type": str,
                }
            """
            if not wrong_items:
                return "In this round you did not have any wrong questions, so there is no obvious weak topic at the moment."

            parts = []
            for i, item in enumerate(wrong_items, start=1):
                q = (item.get("question") or "").strip()
                ans = (item.get("student_answer") or "").strip()
                fb = (item.get("feedback") or "").strip()
                qt = (item.get("question_type") or "").strip()

                snippet_q = q[:400]
                snippet_ans = ans[:400]
                snippet_fb = fb[:400]

                parts.append(
                    f"Question {i} (type: {qt})\n"
                    f"Stem: {snippet_q}\n"
                    f"Student answer: {snippet_ans}\n"
                    f"Grading feedback: {snippet_fb}"
                )

            joined = "\n\n".join(parts)
            if len(joined) > 4000:
                joined = joined[:4000] + "\n...[truncated; only the first part of the round is kept]"

            system_msg = (
                "You are a teaching assistant for a university course. "
                "You analyse the questions that a student got wrong in one practice round, "
                "and identify their weak knowledge areas and give concrete study advice. "
                "Respond in the same language as the student's answers or feedback when possible."
            )

            user_prompt = f"""
            Below are some questions that the student answered incorrectly in this round,
            including the stem, the student's answer and the grading feedback:

    {joined}

Please give concise but well-structured personalized learning feedback in the same language as the student's answers or feedback, including:

1. A list of 3–6 key knowledge points that the student needs to strengthen (use the course's technical terms).
2. For each knowledge point, give 1–2 specific study suggestions (e.g., which lectures to review, which concepts to focus on, what kind of practice to do).
3. If the same knowledge point appears in multiple wrong questions, explicitly emphasise it.

Do NOT repeat the full question stems; just refer to the concepts.
        """.strip()

            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                print("❌ summarize_wrong_questions 失败:", e)
                return f"⚠️ 生成个性化反馈失败：{e}"


# -------------------
# 6️⃣ 主交互循环
# -------------------
    def analyze_full_round(self, all_items: list) -> str:
            """
            Analyze the entire completed practice round, not only wrong answers.
            """
            if not all_items:
                return "No completed round data was provided, so analysis could not be generated."

            parts = []
            for i, item in enumerate(all_items, start=1):
                question = (item.get("question") or "").strip()
                answer = (item.get("student_answer") or "").strip()
                evaluation = (item.get("evaluation") or "").strip()
                verdict = (item.get("verdict") or "unknown").strip()
                question_type = (item.get("question_type") or "").strip()

                parts.append(
                    f"Question {i} (type: {question_type}, verdict: {verdict})\n"
                    f"Stem: {question[:450]}\n"
                    f"Student answer: {answer[:450]}\n"
                    f"Grading feedback: {evaluation[:450]}"
                )

            joined = "\n\n".join(parts)
            if len(joined) > 9000:
                joined = joined[:9000] + "\n...[truncated due to length]"

            system_msg = (
                "You are a university learning analyst. "
                "You review a student's full completed practice round, including correct, partial, "
                "and incorrect answers, in order to infer strengths, weak knowledge areas, and recurring misconceptions. "
                "Respond in the same language as the student's answers or feedback when possible."
            )

            user_prompt = f"""
Below is one full completed practice round. Each item includes the question stem, the student's answer,
the grading verdict, and the grading feedback:

{joined}

Please produce a clear study analysis with these sections:

1. Overall performance summary in 2-4 sentences.
2. Main weak knowledge areas, prioritised from most urgent to least urgent.
3. Evidence from the student's answers showing why each area is weak.
4. Strengths or concepts the student appears to understand well.
5. A concrete improvement plan with 3-5 next study actions.

Do not simply restate each question. Synthesize patterns across the whole round.
            """.strip()

            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                print("鉂?analyze_full_round 澶辫触:", e)
                return f"鈿狅笍 Failed to generate full-round analysis: {e}"


