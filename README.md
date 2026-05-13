# Local Chat Site

A Flask-based local RAG study assistant. It lets users upload course materials, build a local FAISS knowledge base, chat with the uploaded documents, generate practice questions, grade answers, and manage past exam materials.

## Features

- Upload and manage course materials.
- Build a per-user vector store with LangChain and FAISS.
- Ask questions grounded in uploaded materials.
- Generate final-exam style practice questions.
- Grade student answers and provide feedback.
- Optional Google Scholar search through SerpAPI.
- Optional MySQL storage for accounts, rounds, answers, and chat history.

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

Then fill in at least `OPENAI_API_KEY`. Set `SERPAPI_KEY`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `TESSERACT_CMD` as needed.

4. Run the app.

```powershell
cd local_chat_site
python app.py
```

Open the Flask URL printed in the terminal, usually `http://127.0.0.1:5000`.

## MySQL Setup

1. Create the database and application account in MySQL:

```sql
CREATE DATABASE IF NOT EXISTS local_chat_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'local_chat_user'@'127.0.0.1'
  IDENTIFIED BY 'change_this_password';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
  ON local_chat_ai.*
  TO 'local_chat_user'@'127.0.0.1';

FLUSH PRIVILEGES;
```

2. Put the matching connection settings in `local_chat_site/.env`:

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=local_chat_ai
MYSQL_USER=local_chat_user
MYSQL_PASSWORD=change_this_password
```

3. Start the Flask app once. On startup, `app.py` creates these tables automatically if they do not exist:

- `app_users`
- `user_rounds`
- `user_answers`
- `chat_messages`

4. The app now uses MySQL for login/register data and for question-page history data such as generated rounds, answers, and chat records. If MySQL is unavailable, only the auth module falls back to the local SQLite file `app_users.sqlite3`; question/chat history persistence still requires MySQL.

## Notes

- OCR requires Tesseract to be installed separately and configured through `TESSERACT_CMD` or your system `PATH`.
- MySQL is optional for basic local use, but database-backed exam/chat history requires the `MYSQL_*` settings above.
- Do not commit `.env`, uploaded materials, vector indexes, logs, or cached literature files.
