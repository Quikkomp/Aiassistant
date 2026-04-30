# Local Chat Site

A Flask-based local RAG study assistant. It lets users upload course materials, build a local FAISS knowledge base, chat with the uploaded documents, generate practice questions, grade answers, and manage past exam materials.

## Features

- Upload and manage course materials.
- Build a per-user vector store with LangChain and FAISS.
- Ask questions grounded in uploaded materials.
- Generate final-exam style practice questions.
- Grade student answers and provide feedback.
- Optional Google Scholar search through SerpAPI.
- Optional PostgreSQL storage for rounds, answers, and chat history.

## Project Layout

```text
local_chat_site/
  local_chat_site/
    app.py
    document_loader.py
    rag_agentV3_2.py
    static/
    templates/
  requirements.txt
  .env.example
```

Runtime folders such as `materials`, `vector_store`, `student_logs`, `literature_cache`, and `exam_db` are intentionally ignored by Git because they may contain private uploads, generated indexes, logs, or cached data.

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create your local environment file.

```powershell
Copy-Item .env.example local_chat_site\.env
```

Then fill in at least `OPENAI_API_KEY`. Set `SERPAPI_KEY`, `EXAM_DB_DSN`, and `TESSERACT_CMD` only if you need those features.

4. Run the app.

```powershell
cd local_chat_site
python app.py
```

Open the Flask URL printed in the terminal, usually `http://127.0.0.1:5000`.

## Notes

- OCR requires Tesseract to be installed separately and configured through `TESSERACT_CMD` or your system `PATH`.
- PostgreSQL is optional for basic local use, but database-backed exam/chat history requires `EXAM_DB_DSN`.
- Do not commit `.env`, uploaded materials, vector indexes, logs, or cached literature files.
