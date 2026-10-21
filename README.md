# WizPractice · 智练

A Flask-based local RAG study assistant. It lets users upload course materials, build a local FAISS knowledge base, chat with the uploaded documents, generate practice questions, grade answers, and manage past exam materials.

## Features

- Upload and manage course materials.
- Build a per-user vector store with LangChain and FAISS.
- Ask questions grounded in uploaded materials.
- Generate final-exam style practice questions.
- Grade student answers and provide feedback.
- Optional Google Scholar search through SerpAPI.
- Optional MySQL storage for accounts, rounds, answers, and chat history.
- Learning groups with owner-managed membership, invitation links/QR codes, reviewed exam delivery and group-scoped results.

## Learning groups

Open **小组 / Groups** in the sidebar. Teacher accounts can create groups and become their owners; students can join groups and view only their own membership and exam results.

## Teacher and student accounts

- The entry page has separate teacher/student cards. Either role can register normally with username, email and password; no invitation code or external teacher verification is required. These are self-selected account roles, not verified professional credentials.
- The selected card expands into sign-in/registration. A saved role belongs to the account, not the entrance: choosing the other card cannot change permissions. A role mismatch prompts the user to switch entrances; email login and password recovery use the same account.
- Teachers create/review/publish exams, manage their own groups, view score distributions, and open a student's read-only answer sheet from either an exam roster or group results. This includes submitted answers, per-question marks, marking feedback and any existing study report. Teachers cannot access another teacher's private exams.
- Students have only **My attempts** in Exams, can join shared/assigned exams, resume their single attempt and view their own marks, answers and AI study feedback. Personal question libraries and practice remain available to both roles. Teacher-only APIs enforce roles as well as ownership; hiding buttons is not the permission boundary.
- Startup creates `account_roles` in the existing account database (MySQL or SQLite), without replacing accounts or passwords. Pre-upgrade accounts retain teacher capabilities to preserve their existing exams/groups. New accounts default to student if an older API client omits the role. Role changes are not exposed through the client. Back up both account and exam databases before deployment; restart the app to apply the migration.
- The chooser uses short card-expansion transitions and diagonal background trails that extend near the pointer. Touch devices and reduced-motion preferences keep effects minimal. `tests/roles_browser.cjs` uses temporary accounts, mock AI and no real email; `tests/test_account_roles.py` covers role persistence, legacy migration and authorization.

## Group workflow

1. Create a group and invite registered users with its link or QR code. Joining requires sign-in and explicit confirmation. Owners can renew invites to invalidate old links.
2. In **发布考试 / Assign exam**, select a question set and review its answers, explanations and marking criteria in the existing exam editor. Confirm publication to deliver the exam to all active members. Already-reviewed published exams can also be reused.
3. Recipients find assignments in **考试 → 我参与的 / Exams → My attempts**, initially **待参加 / Not started**. Delivery does not start an attempt. Existing answer locking, single-attempt grading and weakness feedback remain unchanged; the same exam shared through multiple groups still permits only one attempt per account.
4. New members receive group exams that remain open. Removing members hides unstarted group assignments and prevents future delivery; historical started/completed attempts are retained. Removed users cannot rejoin using the old invite until the owner restores their membership.
5. Owners can inspect members' public usernames/IDs, joining dates and group exam history. Group results include not-started students, progress, normalized scores and distributions, excluding outsiders and unfinished scores from the average. Members can view only their own results; private emails, personal libraries and chat history are not exposed.

Groups, membership and assignments are stored alongside exams in `local_chat_site/exams.sqlite3`; missing tables are created automatically without deleting existing records. Back up this database along with the existing account database and uploads before production updates. Set `PUBLIC_BASE_URL` to the externally reachable HTTPS site URL so both exam and group QR links work across devices. Never commit runtime databases or `.env` credentials.

Regression tests use temporary databases and mock AI: `python -m unittest discover -s tests -p 'test_*.py'`. `tests/groups_browser.cjs` checks actual browser accounts, invitation sign-in, assignment/grades, member administration and mobile/dark/language behavior using the bundled Playwright runtime.

## Project Layout

```text
Aiassistant/
  local_chat_site/
    app.py
    auth_store.py
    auth_routes.py
    mail_service.py
    document_loader.py
    rag_agentV3_2.py
    static/
    templates/
  tests/
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

## Import learning materials from a URL

In **Create question set**, **Upload URL / 上传 URL** sits next to **Import documents / 导入文档**. Enter a public HTTP/HTTPS webpage, plain-text/Markdown URL or direct PDF link. The app extracts webpage text (or saves the PDF), places it in the signed-in user's existing materials folder and runs the same knowledge-base ingest pipeline as file uploads. Successfully imported materials are automatically selected; written requirements and detailed settings then work as usual.

The feature requires sign-in and permits 10 imports per hour per account. Downloads are limited to 8 MB and extracted text to 200,000 characters. Local/private/cloud-metadata addresses and non-standard ports are blocked; redirects are revalidated and connections are pinned to the validated DNS address with TLS certificate checks. Environment proxy settings are not used. No additional packages are required. Network-level outbound filtering remains recommended for production defense in depth; see the [OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

Sign-in pages, cloud-drive sharing pages, paywalls, JavaScript-only pages and sites that block automated access may not yield usable content. Download an authorized copy and upload it instead. Images/scanned PDFs still depend on the existing document/OCR pipeline. Tests in `tests/test_url_material.py` mock all external requests and verify address restrictions, DNS pinning, redirects, extraction, limits and per-user storage.

## Accounts and QQ email password recovery

Usernames now accept 3–32 Chinese characters, English letters, digits, `_`, `-` and `.`. They must start and end with a Chinese character, letter or digit; spaces, `@` and emoji are not accepted. English case is normalized and full-width letters/digits are normalized to avoid duplicate-looking names. New registration/password changes require 8–128 characters, but existing shorter passwords still work for sign-in.

The sign-in field accepts either the username or the registered email with the **same password and account ID**. Existing libraries, uploads, exams and group membership remain associated with the original ID. Registration requires an email but does not yet verify its ownership; email verification occurs during password recovery. Do not register with an email you cannot access.

### Configure the QQ sending mailbox

1. Open QQ Mail on the web. In **Settings → Account**, enable **POP3/SMTP** or **IMAP/SMTP**, complete QQ's verification, and obtain an **SMTP authorization code**. This is not the QQ login password.
2. On an existing installation, append these settings to `local_chat_site/.env` without replacing its existing API keys, database settings or `FLASK_SECRET_KEY`:

```dotenv
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=your-sending-mailbox@qq.com
SMTP_PASSWORD=your-qq-smtp-authorization-code
# Optional; defaults to SMTP_USER.
SMTP_FROM=your-sending-mailbox@qq.com
```

Keep authorization codes out of chat, screenshots and Git. The sending mailbox is configured by the website administrator; students enter their own **registered** email, not this sender address. Recipients are not limited to QQ email.

3. Use a stable, non-default random `FLASK_SECRET_KEY`. Preserve a secure existing value; only new/default-secret installations need a new one. Changing it logs out existing sessions and invalidates pending recovery challenges. Set `PUBLIC_BASE_URL` to the production HTTPS origin and `SESSION_COOKIE_SECURE=1` on HTTPS deployments (keep `0` for local HTTP). TLS certificate checks are enabled for SMTP; plaintext SMTP is rejected.
4. Restart the app after changing configuration. For the existing Alibaba Cloud service, after deploying this code and backing up the account database: `sudo systemctl restart herlink.service`. Verify the service and site before requesting a real email. No additional Python packages are needed for SMTP.

### Recovery and safety

Click **Forgot password / 忘记密码** → enter registered email → verify the six-digit code → choose and confirm a new password → return to sign-in. Codes expire after 10 minutes, allow at most 5 guesses, and become invalid after successful verification or resend. A verified reset grant expires after 10 minutes and permits exactly one password change. Password reset invalidates previous login sessions and never automatically signs in.

Sending is limited to once per 60 seconds and 5 times per hour per email, plus 30 requests per hour per source IP. Verification and final reset are also rate-limited. Limits and hashed recovery state live in the account database and survive app restarts. Behind a reverse proxy, the app uses the socket source IP; configure a properly restricted trusted-proxy setup before relying on individual-IP limits. It does not blindly trust client-supplied forwarded IP headers.

Mail is dispatched by a bounded background worker, so SMTP does not hold up the HTTP response. Registered and unregistered emails receive the same generic request response to prevent account enumeration. That response is **not a delivery receipt**. Failed delivery does not change the password; administrators can inspect service logs for a failure type (no credentials or codes are logged).

Missing SMTP settings or a known default session secret disable recovery with a clear error; username/email sign-in still works. Startup adds `auth_security`, `auth_rate_limits` and `password_reset_requests` to the existing MySQL/SQLite account database without recreating existing accounts. Back up that database and preserve its location/settings during deployment; never commit runtime databases, SQLite WAL/SHM files or `.env`.

`tests/test_auth_recovery.py` and `tests/auth_recovery_browser.cjs` cover real disposable account databases, session revocation, single-use grants, errors and responsive UI. All automated mail tests use a fake mailbox or mocked SMTP; they never send real email. QQ credentials and an actual delivery test are still required on deployment.

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
- `account_roles` (saved teacher/student account role)
- `auth_security`, `auth_rate_limits`, `password_reset_requests` (account security and recovery)
- `user_rounds`
- `user_answers`
- `chat_messages`

4. The app now uses MySQL for login/register data and for question-page history data such as generated rounds, answers, and chat records. If MySQL is unavailable, only the auth module falls back to the local SQLite file `app_users.sqlite3`; question/chat history persistence still requires MySQL.

## Notes

- New question sets pass a fail-closed quality gate before display or saving: conservative format checks plus an independent structured AI review for leaked answers, missing givens/diagrams, invalid mathematics, ambiguous objective answers, scope/type mismatches and duplicates. Rejected drafts regenerate at most twice; service errors, incomplete/malformed reviews and exhausted retries do not save a set. The model stage has a 120-second total budget, per-call timeouts and SDK retries disabled. Existing question sets are not rewritten; teacher publication review remains necessary. See `docs/question-quality.md` for scope and tests.
- PDF export uses the project-local `local_chat_site/fonts/NotoSansSC-Regular.ttf` (SIL OFL 1.1) and embeds a subset in every PDF. Include the entire `fonts/` directory when deploying; no Windows/Linux system fonts or server-side font installation is needed. The path is resolved relative to the module, not the working directory. A missing or unreadable font reports an export error rather than silently producing Chinese black boxes. See `local_chat_site/fonts/README.md` for source, license and reproducible build details.
- Mathematical content uses the bundled KaTeX 0.19.0 engine and fonts (no CDN): `\(...\)` / `$...$` for inline formulas and `\[...\]` / `$$...$$` for display formulas. Existing question sets, choices, grading feedback, explanations, exams and history render on display without regenerating questions. Editing fields keep the original LaTeX; saved answers and AI grading are unchanged. Unsupported or malformed formulas fall back to literal text. This applies to browser display, not PDF export.
- OCR requires Tesseract to be installed separately and configured through `TESSERACT_CMD` or your system `PATH`.
- MySQL is optional for basic local use, but database-backed exam/chat history requires the `MYSQL_*` settings above.
- Do not commit `.env`, uploaded materials, vector indexes, logs, or cached literature files.
