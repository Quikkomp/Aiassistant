# ============================================
# rag_agent_v5_log.py
# 🚀 智能RAG助教 + 关键词提取 + Google Scholar学术检索 + 学生提问记录与学习反馈
# ============================================

from openai import OpenAI
from dotenv import load_dotenv
from document_loader import load_documents, read_txt, read_pdf, read_docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import os
import sys
import shutil
import requests
import json
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
serpapi_key = os.getenv("SERPAPI_KEY")

if not api_key:
    print("❌ 未检测到 OPENAI_API_KEY，请检查 .env 文件！")
else:
    print("✅ 已加载 OPENAI_API_KEY。")

if not serpapi_key:
    print("⚠️ 未检测到 SERPAPI_KEY（Google Scholar 搜索将不可用）")

client = OpenAI(api_key=api_key)
db = None

# # -------------------
# # 1️⃣ 加载资料
# # -------------------
# print("\n📚 正在加载 materials 文件夹下的资料...")
# docs = load_documents("materials")
#
# if not docs:
#     print("❌ 未找到任何文档，请确认 materials 文件夹中有 .txt / .pdf / .docx 文件。")
# else:
#     print(f"✅ 已加载 {len(docs)} 个文件: {list(docs.keys())}")
#
# all_docs = [
#     Document(page_content=text, metadata={"source": name})
#     for name, text in docs.items()
# ]
#
# # -------------------
# # 2️⃣ 分块
# # -------------------
# print("\n📚 正在加载 materials 文件夹下的资料...")
# docs = load_documents("materials")
#
# # 先假设没有任何文本块
# all_docs = []
# chunks = []
#
# if not docs:
#     # 这里直接提示 + 保持 db = None，不再尝试构建向量库
#     print("⚠️ 未找到任何文档，本地知识库暂时为空。")
# else:
#     print(f"✅ 已加载 {len(docs)} 个文件: {list(docs.keys())}")
#
#     # 1️⃣ 组装 LangChain 的 Document
#     all_docs = [
#         Document(page_content=text, metadata={"source": name})
#         for name, text in docs.items()
#     ]
#
#     # -------------------
#     # 2️⃣ 分块
#     # -------------------
#     print("\n✂️ 正在将文档切分为小块...")
#     splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
#     chunks = splitter.split_documents(all_docs)
#     print(f"✅ 分块完成，共生成 {len(chunks)} 个文本块。")
#
#     # -------------------
#     # 3️⃣ 生成向量数据库
#     # -------------------
#     if chunks:
#         print("\n🧠 正在生成向量数据库 (FAISS)...")
#         embeddings = OpenAIEmbeddings()
#         db = FAISS.from_documents(chunks, embeddings)
#         print("✅ 向量数据库创建成功！")
#     else:
#         # 有文件，但一个字都抽不出来（典型：纯图片 PDF）
#         print("⚠️ 所有文档都无法抽取出文本，本地知识库暂时为空。")
#         db = None


# -------------------
# 4️⃣ 系统提示语
# -------------------
SYSTEM_PROMPT = """
# 角色
你是一名面向**所有学科领域**的学术写作与文献综述智能助手；能够依据权威文献进行证据导向的梳理、比较与总结，并输出结构清晰、可追溯、有引文的回答。你可以处理教育学、医学、护理学、心理学、计算机科学等各类学术领域的问题；当问题涉及混合式学习（Blended Learning）或 HyFlex 时，同样按本规则处理。

## 总体目标
- 依据本地知识库与授权的外部文献，给出**有证据支撑的学术回答**；
- 回答聚焦学术问题本身，不输出与学术无关的闲聊；
- 对每个重要论断，尽量指出对应文献来源，并在结尾给出 **References (APA 7)** 列表。

## 技能 1：收集与筛选证据
1. 检索范围：
   - 首先使用已接入的本地知识库/资料库（如 knowledge_base / materials 中的文献）；
   - 如本地证据明显不足，且系统允许，可结合外部学术检索（如 Google Scholar / SerpAPI）补充文献。

2. 证据筛选：
   - 优先保留与用户问题**直接相关**的段落，例如：定义、理论/模型、研究发现、方法、实验结果、案例等；
   - 舍弃广告性内容、与主题无关的段落、缺乏明确来源的泛泛陈述；
   - 如命中的片段相关性较弱，应在回答中说明“证据有限/相关性较弱”。

3. 证据不足时：
   - 若现有文献不足以支撑可靠回答，应明确说明“证据不足/不确定”，而不是猜测；
   - 可以提示用户：需要补充哪些类型的文献或允许扩展检索。

## 技能 2：撰写学术回答 / 文献综述
1. 默认输出结构（可适度调整以适配问题）：
   - **简要总体概述**：1–2 句给出核心概念或结论；
   - **3–5 个关键要点**：每个要点对应一个或一组研究结果/理论观点，并标明来源；
   - **实践/设计/应用启示**（如适用）：2–3 条可操作的建议或启示；
   - **References (APA 7)**：只列本次正文中明确使用过的文献。

2. 引文规范（强约束）：
   - 在正文中对重要论断使用文内引注，比如 `(Author, Year)` 或 `(Author1 & Author2, Year)`；
   - 参考文献列表按 **APA 第 7 版** 格式书写，包含：作者、年份、标题、来源（期刊/出版社等）以及 DOI/URL（若已在资料中给出）；
   - **不得编造**不存在的作者、年份、期刊名、页码、DOI 或结论；
   - 正文与参考文献须一一对应：不得出现“正文未提及”的参考文献，也不得遗漏正文中已经引到的关键文献。

3. 比较与概念澄清：
   - 涉及多个理论/模型/干预/案例时，给出优点、局限、适用情境、实施要点等的对照；
   - 若不同文献观点存在差异，说明各自立场、研究边界及可能原因，而非简单混合。

4. 语言与风格：
   - Always respond in **English**, regardless of the user's input language. Reference lists must follow APA 7 in English;
   - 首次出现的重要术语，尽量给出中英对照（如用户使用中文提问）；
   - 先结论后证据，避免空泛、堆砌式罗列，突出“发现了什么、依据是什么、有什么启示”。

## 限制与安全边界
- 主题范围：可以处理任何学术领域的问题，但应始终围绕“学术与研究”展开；对于与学术无关的娱乐、闲聊、政治立场煽动等，礼貌拒绝或弱化回答。
- 证据约束：仅使用本地知识库与明确授权的外部学术来源；不得凭空编造研究、数据或引文。
- 准确性优先：当证据不足或研究结论相互矛盾时，要明确说明不确定性和争议点，而不是给出过度肯定的结论。
- 一致性：同一概念/模型/量表等，应尽量使用同一权威来源的描述；若引用多源，应说明差别及原因。
- 不输出思考链；不生成带有强烈个人偏见、与证据不符或不适合学术语境的内容。
"""





# -------------------
# 5️⃣ 智能体类定义
# -------------------
class RagAgent:
    LOG_PATH = "student_logs/questions_log.json"
    EXAM_DB_PATH = os.path.join("exam_db", "past_exams.json")

    def __init__(self, client, db, serpapi_key=None, exam_db_path=None):
        self.client = client
        self.db = db
        self.serpapi_key = serpapi_key
        self.last_query = None

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

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [save_exam_db] 保存过往试卷数据库失败: {e}")

    def add_past_exam_question(self, question_text, question_type="short_answer", meta=None):
        """
        向过往试卷数据库加入一道题目。
        question_type 建议使用：fill_blank / multiple_choice / short_answer
        meta 可以包含 year、course、source 等信息。
        """
        q = (question_text or "").strip()
        if not q:
            raise ValueError("question_text 不能为空。")

        db = self._load_exam_db()
        next_id = max((item.get("id", 0) for item in db), default=0) + 1

        record = {
            "id": next_id,
            "question": q,
            "question_type": question_type or "short_answer",
        }
        if meta and isinstance(meta, dict):
            # 允许补充额外字段，例如 {"year": "2024", "paper": "A卷"}
            for k, v in meta.items():
                if k not in record:
                    record[k] = v

        db.append(record)
        self._save_exam_db(db)
        return record

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
            返回新增题目的列表（每个元素是 add_past_exam_question 返回的 dict）。
            """
            if not raw_text or not raw_text.strip():
                return []

            # 避免 prompt 过长，做个截断（可以按需调节）
            snippet = raw_text.strip()
            if len(snippet) > 8000:
                snippet = snippet[:8000] + "\n...[truncated]"

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

            try:
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
                )
                content = response.choices[0].message.content
                data = json.loads(content)
            except Exception as e:
                print(f"⚠️ 解析试卷文本失败: {e}")
                return []

            if not isinstance(data, list):
                print("⚠️ 模型返回的不是列表，忽略。")
                return []

            added = []
            for idx, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    continue
                q_text = str(item.get("question", "")).strip()
                if not q_text:
                    continue

                q_type = (item.get("question_type") or default_question_type).strip() or default_question_type
                meta = item.get("meta") or {}
                if not isinstance(meta, dict):
                    meta = {}

                # 补充一些默认元数据
                if source_name and "source_file" not in meta:
                    meta["source_file"] = source_name
                if "index" not in meta:
                    meta["index"] = f"Q{idx}"

                record = self.add_past_exam_question(
                    question_text=q_text,
                    question_type=q_type,
                    meta=meta,
                )
                added.append(record)

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

        返回新增题目的列表（每个元素是 add_past_exam_question 返回的 dict）。
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        ext = os.path.splitext(file_path)[1].lower()
        text = ""

        try:
            # 1) 纯文本类型
            if ext in [".txt", ".md"]:
                text = read_txt(file_path)

            # 2) PDF：先尝试正常提取文本，提不到时再 OCR
            elif ext == ".pdf":
                text = read_pdf(file_path)
                if not text or not text.strip():
                    print(f"⚠️ PDF {file_path} 没有可提取的文本，尝试 OCR 方式...")
                    text = self._ocr_pdf_to_text(file_path)

            # 3) Word 文档
            elif ext == ".docx":
                text = read_docx(file_path)

            # 4) 常见图片格式：直接 OCR
            elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
                print(f"ℹ️ 检测到图片试卷，将使用 OCR 识别: {file_path}")
                text = self._ocr_image_to_text(file_path)

            # 5) 其他类型：先尝试按文本打开；有需要也可以扩展成 OCR
            else:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    text = ""

        except Exception as e:
            print(f"⚠️ 无法从文件中读取内容: {file_path}, error={e}")
            text = ""

        if not text or not text.strip():
            print(f"⚠️ 文件内容为空或无法解析为文本，跳过：{file_path}")
            return []

        source_name = os.path.basename(file_path)
        return self._extract_questions_from_text(
            raw_text=text,
            default_question_type=default_question_type,
            source_name=source_name,
        )



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

    # ---- 🧭 任务规划 ----
    def plan(self, query: str) -> str:
            """
            根据用户的问题选择任务类型：
            - answer：直接用本地知识库 + 自身推理回答
            - search：调用 Google Scholar / 外部文献搜索，做文献综述
            - learn：将用户提供的新资料加入知识库
            """
            prompt = f"""
    你是一个负责处理各种学术任务的智能代理（不限于某一学科或主题），可以处理教育学、医学、计算机科学、心理学等所有学术领域的问题。

    你现在拥有的资源：
    1. 本地文献知识库（位于 knowledge_base/materials 等文件夹中，已构建为向量数据库，可用于检索和回答问题）。
    2. 外部文献搜索能力（通过 Google Scholar + SerpAPI 获取最新或更广泛的学术论文）。
    3. 将新资料“学习”并加入本地知识库的能力（由系统的 ingest / learn 接口实现）。

    你的任务是：**只根据用户给出的 query，判断当前应该执行哪一种任务类型**。

    可选的任务类型只有三个（全部使用小写英文）：
    - "answer"：当你认为本地知识库中已经有足够的信息，或者问题属于
        * 概念/术语的解释或比较；
        * 理论、模型、方法的说明与对比；
        * 总结已有材料中的观点、结论、优缺点；
        * 对用户提供的文章进行解读、对比、提炼；
      且不需要额外去互联网上检索新文献时，选择 answer。

    - "search"：当你认为需要**系统性地查找学术文献**时，例如：
        * 需要做文献综述（review）、系统综述（systematic review）、meta-analysis 等；
        * 需要查找“最新研究”“近几年研究趋势”“某领域代表性论文”；
        * 需要获取具体论文、期刊文章，而本地知识库明显不够时；
      此时使用外部文献搜索更合适，就选择 search。

    - "learn"：当用户的意图是让系统“学习/导入/加入/更新”资料，而不是立刻回答具体学术问题时，例如：
        * 用户说 “帮我把这些文章加入你的知识库”；
        * 用户强调 “先学习这些材料/文献，以后回答我的问题”；  
      这类以“扩充知识库”为主的请求，选择 learn。

    注意：
    - 不要再把自己限定在 Blended Learning 或 HyFlex Learning 主题上；无论问题来自哪个学科或主题，都按上述规则判断。
    - 如果问题本身就是一般性学术问题（例如任何领域的定义、理论、模型、实验结果等），且你觉得不需要实时检索最新论文，优先选择 "answer"。
    - 只有在**明显**需要查找额外文献时才选择 "search"。
    - 只有当用户明确提出“让你学习/导入新的资料”时才选择 "learn"。

    输出要求（非常重要）：
    - 你 **只能** 输出下面三个小写单词之一：answer、search 或 learn。
    - 不能输出解释、理由、标点或其它任何内容。
    - 不要加引号，不要加换行或空格。
    用户的问题是：
    {query}
            """.strip()

            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个严谨的学术助手，会根据用户的需求在 answer / search / learn 三种任务中选择其一。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            decision = completion.choices[0].message.content.strip().lower()
            # 保险起见，只保留三种合法输出
            if decision not in {"answer", "search", "learn"}:
                decision = "answer"
            print(f"🧠 任务规划结果: {decision}")
            return decision

        # ---- 📖 改进版：基于所有相关资料进行总结回答 ----
    def answer(self, query):
        print("🔍 正在检索知识库（广域匹配模式）...")

        # 1️⃣ 空库保护
        if self.db is None:
            return (
                "⚠️ The local knowledge base is currently empty or not loaded.\n"
                "Please upload materials first, or rebuild the knowledge base."
            )

        try:
            # 2️⃣ 使用 similarity_search_with_score 返回相似度分数
            results = self.db.similarity_search_with_score(query, k=50)
            print(f"✅ 从数据库中检索到 {len(results)} 个候选片段。")

            # 3️⃣ 设定相关度阈值（例如 0.3，越小表示越相似）
            threshold = 0.3
            relevant_docs = [doc for doc, score in results if score < threshold]

            # 如果匹配片段太少，则放宽阈值
            if len(relevant_docs) < 3:
                relevant_docs = [doc for doc, score in results[:10]]
                print("⚠️ 匹配片段较少，已自动放宽相似度筛选。")

            # 4️⃣ 合并所有高相关内容
            combined_context = "\n\n".join(
                [
                    f"📄 来源：{d.metadata.get('source', '未知文件')}\n{d.page_content}"
                    for d in relevant_docs
                ]
            )

            # 限制文本长度（避免超出 token 限制）
            if len(combined_context) > 6000:
                combined_context = combined_context[:6000] + "\n...[内容过长已截断]"

            print(f"🧠 已整合 {len(relevant_docs)} 个片段进行总结。")

            # 5️⃣ 构建提示词
            prompt = f"""
    You are an educational-technology research assistant.

    Based on ALL the materials below, answer the question "{query}" in a structured and synthetic way.

    Requirements:
    - First give a 1–2 sentence overall definition or overview.
    - Then extract 3–5 key points, models, or findings, and for each one indicate the source (file name or author).
    - End with a short concluding paragraph summarizing the main trends or consensus.
    - Always write your answer in **English**, even if the source materials or the question are in another language.

    【资料内容】
    {combined_context}
    """

            # 6️⃣ 向模型请求回答
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.choices[0].message.content
            self.log_question(query, content)
            return content

        except Exception as e:
            return f"❌ 回答失败: {e}"
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
    ) -> str:
        """
        Generate final-exam practice questions in **English** based on uploaded materials
        AND/OR past exam questions.

        ✅ 新增规则：
        - 如果左侧 Knowledge Base 没有勾选任何文献，右侧“过往试卷题库”勾选了题目，
          则完全只依据这些勾选的试卷题目出题（不再从知识库检索课件内容）。
        """

        # 0️⃣ 参数归一化
        if selected_docs is None:
            selected_docs = []
        exam_id_list = selected_exam_ids or []

        # 双保险：两边都没选就直接拒绝
        if (not selected_docs) and (not exam_id_list):
            return (
                "⚠️ 当前没有勾选任何资料或过往试卷题目，"
                "请在界面右侧勾选后再点击“生成试题”。"
            )

        # 是否进入「只用过往试卷题目」模式：
        # 👉 Knowledge Base 完全没勾选，但过往试卷题库勾选了题目
        exam_only_mode = (not selected_docs) and bool(exam_id_list)

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
        qt = type_map.get((question_type or "").lower(), "fill_blank")

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
        if not exam_only_mode:
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
        past_exam_items = self._load_exam_db()

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
        type_desc = type_desc_map.get(qt, "fill-in-the-blank questions.")

        # 6️⃣ 针对不同模式，给模型的强约束提示
        if exam_only_mode:
            mode_hint = (
                "- The 'Source materials' below are ONLY the past exam questions that the student selected.\n"
                "      - You MUST generate new questions that test the **same or very closely related concepts** "
                "as these past exam questions.\n"
                "      - Do NOT switch to unrelated chapters or topics that are not obviously connected to these questions."
            )
        else:
            mode_hint = (
                "- The 'Source materials' below are knowledge snippets retrieved from the selected course materials.\n"
                "      - When 'Past exam question examples' are provided, use them ONLY as style/difficulty references; "
                "all factual content must still be grounded in 'Source materials'."
            )

        # 7️⃣ Prompt
        prompt = f"""
    You are an exam-preparation question generator for university students.

    [STRICT REQUIREMENTS]
    - Always write ALL questions in **English**, even if the source materials or the user message are in other languages.
    - Base every question strictly on the context below. Do NOT introduce content that is not supported by the context.
    {mode_hint}
    - Question type: {type_desc}
    - Number of questions: {n}
    - Difficulty setting: {difficulty_key}
      {difficulty_hint}
    - Do NOT provide answers or solutions, only the questions themselves.
    - Use clear numbering: Q1, Q2, Q3, ...
    - When possible, generate questions that are similar in style and difficulty
      to the past exam questions provided, but do NOT copy them verbatim.

    [User's instruction / exam scope]
    {query}

    [Past exam question examples]
    {exam_examples or "(no past exam questions are currently stored)"}

    [Source materials]
    {combined_context}
    """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate high-quality final-exam practice questions "
                            "in English based strictly on the given course materials or past exam questions. "
                            "Never include answers unless explicitly asked."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            # 出题日志（可选）
            self.log_question(f"[Question Generation] {query}", content)
            return content
        except Exception as e:
            return f"❌ Failed to generate questions: {e}"


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
                "equivalent even if they use different wording."
                "even if they use different wording. Always reply in English."
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

            Write your reply in **English** with the following structure:

            Result: <Correct / Partially correct / Incorrect>
            Brief explanation: <1–3 sentences in English, starting with an encouraging phrase and then explaining what is missing or wrong and how to improve.>
            Reference answer: <a concise model answer in English>.
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
            "Always respond in English, even if the student's question or the materials are in another language. "
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
                "solution steps, grounded in the given course materials. Always respond in English."
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

    Please answer in **English** and use the following structure:

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

    # ---- 🎯 关键词提取 ----
    def extract_keywords(self, query):
        prompt = f"""
You are an academic keyword extractor.
Given ONLY the following question, extract 3-5 concise English keywords for literature search.
Question: "{query}"
Output: comma-separated keywords only.
"""
        try:
            result = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return result.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ 关键词提取失败: {e}")
            return query

    # ---- 🌐 谷歌学术搜索 ----
    def search_and_summarize(self, query=None):
        if not self.serpapi_key:
            return "⚠️ SERPAPI_KEY 未设置，无法使用 Google Scholar 搜索。"

        if not query and self.last_query:
            query = self.last_query
            print(f"🔁 使用上次问题进行学术搜索：{query}")
        elif not query:
            return "⚠️ 当前无有效问题，请先提问。"

        self.last_query = query
        keywords = self.extract_keywords(query)
        print(f"🎯 提取到的检索关键词：{keywords}")

        try:
            params = {
                "engine": "google_scholar",
                "q": keywords,
                "api_key": self.serpapi_key,
                "num": 5
            }
            response = requests.get("https://serpapi.com/search", params=params)
            data = response.json()

            results = []
            for item in data.get("organic_results", []):
                title = item.get("title")
                link = item.get("link")
                snippet = item.get("snippet", "")
                results.append(f"• {title}\n  {snippet}\n  🔗 {link}\n")

            if not results:
                return "⚠️ 未从 Google Scholar 找到相关结果。"

            summary_prompt = f"""
Summarize the following papers into a concise academic overview (3-5 sentences)
focusing on blended learning or HyFlex education.

Papers:
{chr(10).join(results)}
"""
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a research summarizer."},
                    {"role": "user", "content": summary_prompt}
                ]
            )
            summary = completion.choices[0].message.content
            self.log_question(query, summary)
            self.last_query = None
            return f"📚 Here is a literature summary based on the keywords {keywords}:\n\n{summary}\n\nReferences:\n" + "\n".join(results)

        except Exception as e:
            return f"❌ 搜索失败: {e}"

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

    # ---- 🎓 学习反馈功能 ----
    def summarize_learning(self):
        """总结学生最近的学习问题并生成反馈"""
        if not os.path.exists(self.LOG_PATH):
            return "⚠️ There are no logged questions yet."

        with open(self.LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)

        if not logs:
            return ("⚠️ The question log is empty.")

        recent_logs = logs[-20:]
        history_text = "\n".join([f"Q{i+1}: {item['question']}" for i, item in enumerate(recent_logs)])

        prompt = f"""
        You are a learning coach. The following are the student's recent questions:

        {history_text}

        Please:
        1. Summarize the main topics the student is focusing on.
        2. Point out their strengths and common misunderstandings.
        3. Give 3 concrete and personalized study suggestions.

        Always respond in English.
                """.strip()

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一名负责学习反馈的智能助教。"},
                    {"role": "user", "content": prompt}
                ]
            )
            feedback = response.choices[0].message.content
            return f"🧭 Here is your learning feedback.\n{feedback}"
        except Exception as e:
            return f"❌ 生成反馈失败: {e}"

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
                "Always respond in English."
            )

            user_prompt = f"""
            Below are some questions that the student answered incorrectly in this round,
            including the stem, the student's answer and the grading feedback:

    {joined}

Please give a concise but well-structured personalized learning feedback in English, including:

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
                "Always respond in English."
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


def chat_with_agent():
    print("\n🤖 智能 RAG Agent 启动！输入 'exit' 退出\n")
    agent = RagAgent(client, db, serpapi_key)

    while True:
        query = input("👩‍🎓 你：")
        if query.lower() in ["exit", "quit", "bye"]:
            print("👋 再见～")
            break

        plan = agent.plan(query)
        print(f"🧭 任务类型：{plan}")

        if plan == "answer":
            reply = agent.answer(query)
        elif plan == "search":
            reply = agent.search_and_summarize(query)
        elif plan == "learn":
            reply = agent.ingest_material("materials")
        elif plan == "feedback":
            reply = agent.summarize_learning()
        else:
            reply = "❓ Unable to identify task type. Please try again."

        print(f"\n🤖 Agent：{reply}\n")



if __name__ == "__main__":
    chat_with_agent()
