let chatHistory = []; // 鐢ㄦ潵璁板綍鍘嗗彶瀵硅瘽锛屼紶缁欏悗绔?
// ====== Exam Question Card State & Helpers ======
let questionList = [];
let questionAnswers = [];
let questionEvaluations = [];
let currentQuestionIndex = 0;
let questionExplainStage = [];
let questionExplainText = [];


let qaHistory = [];


let answeredFlags = [];
let wrongQuestions = [];
let hasShownRoundFeedback = false;

let scenarioQuestionTexts = [];   // 姣忛亾棰樺搴旂殑涓€閬撯€滄儏鏅縼绉婚鈥濈殑棰樺共
let scenarioAnswers = [];         // 姣忛亾棰樺搴旀儏鏅鐨勪綔绛?
let scenarioEvaluations = [];     // 姣忛亾鎯呮櫙棰樼殑鎵规敼鍙嶉
// 鎯呮櫙棰樼殑绮捐鐘舵€?& 绮捐鍐呭
let scenarioExplainStage = [];   // 0=鏈簿璁诧紱1=宸茬粡鐢熸垚绮捐
let scenarioExplainText = [];

// 鎯呮櫙棰樹笓鐢?QA 鍘嗗彶 & 褰撳墠姝ｅ湪鍋氭儏鏅瀵瑰簲鍝竴閬撳師棰?
let scenarioQaHistory = [];
let currentScenarioIndex = null;
let pastExamQuestions = [];  //  杩囧線璇曞嵎棰樺簱鍦ㄥ墠绔殑缂撳瓨


const SCORE_HISTORY_KEY = "exam_score_history";
let scoreHistory = [];
let kbReady = true;
const LANG_KEY = "ui_lang";
let currentLang = "zh";

const I18N = {
  "zh": {
    "lang_toggle": "EN",
    "kb_label": "???",
    "documents": "???",
    "title": "??????",
    "subtitle": "????????????????????????",
    "type": "??",
    "fill_blank": "???",
    "multiple_choice": "???",
    "short_answer": "???",
    "count": "??",
    "generate_questions": "????",
    "prev_question": "???",
    "next_question": "???",
    "survey": "????",
    "feedback_default": "??????????????????????",
    "scenario_entry_desc": "????????????????????????",
    "scenario_entry_disabled": "?????",
    "no_score": "??????????????????????",
    "latest_points": "???{n} ?",
    "latest_empty": "???-- ?",
    "total_attempts": "??????{n}",
    "total_zero": "??????0",
    "empty_questions_hint": "???????????????????????????????",
    "question_x": "? {a} ? / ? {b} ?",
    "your_answer": "????",
    "submit": "??",
    "got_it": "????",
    "i_dont_understand": "?????",
    "detailed_explain": "????",
    "ask_ai": "? AI",
    "followup_title": "???????",
    "need_submit_first": "??????????",
    "need_submit_finish": "????????????",
    "next_question_action": "???",
    "extra_practice": "????",
    "no_more_questions_tip": "????????????????????????????",
    "qa_error": "? ?????",
    "qa_request_failed": "? ?????????????????",
    "qa_followup_prompt": "?????????????",
    "scenario_title": "??????????",
    "scenario_generate": "?????",
    "scenario_not_ready": "????????",
    "scenario_need_generate": "????????",
    "scenario_submit_first": "??????????",
    "scenario_modal_need_submit": "???????????????",
    "please_input_answer": "??????????",
    "grading_failed": "???????????",
    "network_error_grade": "??????????????????????",
    "submit_answer": "????",
    "kb_empty": "?????????????",
    "delete_file_title": "?????????",
    "delete_btn": "??",
    "no_metadata": "????",
    "delete_failed": "?????",
    "delete_failed_server": "?????????????????",
    "select_file_first": "???????",
    "uploading": "???...",
    "upload_success": "??????{names}\\n??????? {n} ????",
    "upload_failed": "?????",
    "upload_failed_server": "?????????????????",
    "upload_kb_btn": "??????",
    "kb_rebuilding": "??????...",
    "upload_material_first": "??????",
    "checking_docs_before_generate": "?????????????????????",
    "generate_loading": "???...",
    "error_prefix": "???",
    "request_failed": "?????????????????",
    "upload_exam_first": "?????????????",
    "upload_parse_loading": "??????...",
    "upload_exam_ok": "??? {saved} ???????? {imported} ???",
    "upload_past_btn": "????????",
    "generate_btn": "????"
  },
  "en": {
    "lang_toggle": "??",
    "kb_label": "Knowledge Base",
    "documents": "documents",
    "title": "Coursework Practice Assistant",
    "subtitle": "Upload your study materials, then select question type to generate questions.",
    "type": "Type",
    "fill_blank": "Fill-in-the-blank",
    "multiple_choice": "Multiple Choice",
    "short_answer": "Short Answer",
    "count": "Count",
    "generate_questions": "Generate Questions",
    "prev_question": "Last question",
    "next_question": "Next question",
    "survey": "Start Questionnaire",
    "feedback_default": "After completing all questions, I will tell you which areas need improvement.",
    "scenario_entry_desc": "You can click below to generate similar questions using the same concept.",
    "scenario_entry_disabled": "Available after answering incorrectly",
    "no_score": "No score records yet. Scores will be recorded automatically after grading.",
    "latest_points": "Latest: {n} points",
    "latest_empty": "Latest: -- points",
    "total_attempts": "Total Attempts: {n}",
    "total_zero": "Total Attempts: 0",
    "empty_questions_hint": "No questions yet. Please select materials and click Generate Questions.",
    "question_x": "Question {a} / {b}",
    "your_answer": "Your Answer",
    "submit": "Submit",
    "got_it": "Got it",
    "i_dont_understand": "I don't understand",
    "detailed_explain": "Detailed Explanation",
    "ask_ai": "Ask AI",
    "followup_title": "Follow-up Questions for This Problem",
    "need_submit_first": "Please submit your answer and complete grading first.",
    "need_submit_finish": "Please submit your answer and complete grading first.",
    "next_question_action": "Next Question",
    "extra_practice": "Extra Practice",
    "no_more_questions_tip": "You reached the last question.",
    "qa_error": "? Error: ",
    "qa_request_failed": "? Request failed. Please check backend service.",
    "qa_followup_prompt": "Any further questions about this problem?",
    "scenario_title": "Scenario Practice (Retry Incorrect Questions)",
    "scenario_generate": "Generate Similar Question",
    "scenario_not_ready": "No scenario question has been generated yet.",
    "scenario_need_generate": "Please generate a scenario question first.",
    "scenario_submit_first": "Please submit and finish grading first.",
    "scenario_modal_need_submit": "Please finish and submit the scenario question above first.",
    "please_input_answer": "Please enter your answer before submitting.",
    "grading_failed": "Grading failed. Please try again later.",
    "network_error_grade": "Network error. Unable to grade. Please check server.",
    "submit_answer": "Submit Answer",
    "kb_empty": "The knowledge base is currently empty. Please upload files.",
    "delete_file_title": "Delete this file from the knowledge base",
    "delete_btn": "Delete",
    "no_metadata": "No metadata",
    "delete_failed": "Delete failed: ",
    "delete_failed_server": "Delete failed, please check server.",
    "select_file_first": "Please select a file first.",
    "uploading": "Uploading...",
    "upload_success": "Uploaded files: {names}\\nCurrent knowledge base contains {n} document(s).",
    "upload_failed": "Upload failed: ",
    "upload_failed_server": "Upload failed, please check server.",
    "upload_kb_btn": "Upload to Knowledge Base",
    "kb_rebuilding": "Knowledge base rebuilding...",
    "upload_material_first": "Upload materials first",
    "checking_docs_before_generate": "Please check at least one material or past question before generating.",
    "generate_loading": "Generating...",
    "error_prefix": "Error: ",
    "request_failed": "Request failed, please check server.",
    "upload_exam_first": "Please select exam files first.",
    "upload_parse_loading": "Uploading and parsing...",
    "upload_exam_ok": "Uploaded {saved} file(s), extracted {imported} question(s).",
    "upload_past_btn": "Upload Past Exam Papers",
    "generate_btn": "Generate Questions"
  }
};

const ZH_OVERRIDES = {
  lang_toggle: "EN",
  kb_label: "知识库",
  documents: "份文档",
  title: "课程练习助手",
  subtitle: "请先上传学习资料到知识库，再选择题型生成练习题。",
  type: "题型",
  fill_blank: "填空题",
  multiple_choice: "选择题",
  short_answer: "简答题",
  count: "数量",
  generate_btn: "生成试题",
  prev_question: "上一题",
  next_question: "下一题",
  survey: "开始问卷",
  feedback_default: "完成全部题目后，我会告诉你需要加强的知识点。",
  scenario_entry_desc: "你可以点击下方按钮，基于同一知识点生成相似题目。",
  scenario_entry_disabled: "答错后可用",
  no_score: "暂无成绩记录。每次批改完成后会自动记录分数。",
  latest_points: "最近：{n} 分",
  latest_empty: "最近：-- 分",
  total_attempts: "总练习次数：{n}",
  total_zero: "总练习次数：0",
  empty_questions_hint: "还没有生成题目。请先在右侧选择资料和参数，再点击“生成试题”。",
  question_x: "第 {a} 题 / 共 {b} 题",
  your_answer: "你的答案",
  submit: "提交",
  got_it: "我理解了",
  i_dont_understand: "我还不理解",
  detailed_explain: "详细讲解",
  ask_ai: "问 AI",
  followup_title: "继续追问这道题",
  need_submit_first: "请先提交并完成批改。",
  need_submit_finish: "请先提交答案并完成批改。",
  next_question_action: "下一题",
  extra_practice: "巩固练习",
  no_more_questions_tip: "你已经到最后一题了，可以回看前面的题目，或结束本轮练习。",
  qa_error: "❌ 发生错误：",
  qa_request_failed: "❌ 请求失败，请检查后端是否正常运行。",
  qa_followup_prompt: "关于这道题还有其他问题吗？",
  scenario_title: "情景练习（错题重练）",
  scenario_generate: "生成相似题",
  scenario_not_ready: "尚未生成情景题。",
  scenario_need_generate: "请先生成情景题。",
  scenario_submit_first: "请先提交并完成批改。",
  scenario_modal_need_submit: "请先完成上方情景题并提交批改。",
  please_input_answer: "请先输入答案再提交。",
  grading_failed: "批改失败，请稍后再试。",
  network_error_grade: "网络错误，无法批改答案，请检查服务是否正常。",
  submit_answer: "提交答案",
  kb_empty: "知识库为空，请先上传文件。",
  delete_file_title: "从知识库删除此文件",
  delete_btn: "删除",
  no_metadata: "无元数据",
  delete_failed: "删除失败：",
  delete_failed_server: "删除失败，请检查后端服务是否启动。",
  select_file_first: "请先选择文件。",
  uploading: "上传中...",
  upload_success: "已上传文件：{names}\\n当前知识库共有 {n} 份文档。",
  upload_failed: "上传失败：",
  upload_failed_server: "上传失败，请检查后端服务是否启动。",
  upload_kb_btn: "上传到知识库",
  kb_rebuilding: "知识库构建中...",
  upload_material_first: "请先上传资料",
  checking_docs_before_generate: "请至少勾选一个资料或历年题目后再生成试题。",
  generate_loading: "生成中...",
  error_prefix: "错误：",
  request_failed: "请求失败，请检查后端服务是否启动。",
  upload_exam_first: "请先选择要上传的试卷文件。",
  upload_parse_loading: "上传并解析中...",
  upload_exam_ok: "已上传 {saved} 个文件，成功提取 {imported} 道题。",
  upload_past_btn: "上传历年试卷文件"
};

function t(key, vars = {}) {
  const table = I18N[currentLang] || I18N.zh;
  const fallback = I18N.en;
  let text = table[key] ?? fallback[key] ?? key;
  if (currentLang === "zh" && ZH_OVERRIDES[key]) {
    text = ZH_OVERRIDES[key];
  }
  Object.keys(vars).forEach((k) => {
    text = text.replace(`{${k}}`, String(vars[k]));
  });
  return text;
}

function ensureLangToggleButton() {
  let btn = document.getElementById("lang-toggle-btn");
  if (btn) return btn;

  const topbarRight = document.querySelector(".topbar-right");
  if (!topbarRight) return null;
  btn = document.createElement("button");
  btn.id = "lang-toggle-btn";
  btn.className = "small-btn lang-toggle-btn";
  topbarRight.appendChild(btn);
  return btn;
}

function updateAccountAvatar(username) {
  const avatar = document.getElementById("account-avatar");
  if (!avatar) return;
  const initial = (username || "").trim().charAt(0).toUpperCase();
  avatar.textContent = initial || "U";
}

function applyAuthI18n() {
  const zh = currentLang === "zh";
  const loginCopy = document.querySelector(".auth-copy-login");
  const registerCopy = document.querySelector(".auth-copy-register");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  if (loginCopy) {
    loginCopy.querySelector(".auth-kicker").innerText = zh ? "EXERCISE AGENT 入口" : "EXERCISE AGENT ACCESS";
    loginCopy.querySelector("h1").innerText = zh ? "欢迎回到 Exercise Agent。" : "Welcome back to Exercise Agent.";
    const items = loginCopy.querySelectorAll(".auth-benefits div");
    const text = zh
      ? [
          ["练习历史", "回到之前生成的题目、答案、分数和反馈记录。"],
          ["个人学习空间", "集中管理上传资料、题库、练习和 AI 反馈。"],
          ["智能出题", "基于课程文件和模拟题生成有针对性的练习。"],
          ["安全账户", "保存学习进度，并保护你上传的学习内容。"],
        ]
      : [
          ["Saved practice history", "Return to generated questions, answers, scores, and feedback from earlier sessions."],
          ["Personal study workspace", "Manage uploaded materials, question banks, exam practice, and AI feedback in one place."],
          ["Question generation", "Create targeted exercises from your own course files and selected model questions."],
          ["Secure account", "Keep your learning progress connected while protecting your uploaded study content."],
        ];
    items.forEach((item, idx) => {
      if (!text[idx]) return;
      item.querySelector("strong").innerText = text[idx][0];
      item.querySelector("span").innerText = text[idx][1];
    });
  }

  if (registerCopy) {
    registerCopy.querySelector(".auth-kicker").innerText = zh ? "创建账户" : "CREATE AN ACCOUNT";
    registerCopy.querySelector("h1").innerText = zh ? "开始使用 Exercise Agent 练习。" : "Start practicing with Exercise Agent.";
    const items = registerCopy.querySelectorAll(".auth-benefits div");
    const text = zh
      ? [
          ["建立练习空间", "为课程资料和生成练习建立个人账户。"],
          ["从反馈中学习", "每轮练习后查看批改结果、解释和薄弱点。"],
          ["AI 辅助学习", "使用面向出题、批改和复习指导的智能助手。"],
          ["随时继续", "注册后，你的资料和练习记录会保留下来。"],
        ]
      : [
          ["Build your practice space", "Set up a personal account for uploaded course resources and generated exercises."],
          ["Learn from feedback", "Review grading results, explanations, and weak points after each practice round."],
          ["Study with AI", "Use an agent designed for question generation, answer checking, and guided revision."],
          ["Continue anytime", "After joining, your saved materials and practice records stay available when you return."],
        ];
    items.forEach((item, idx) => {
      if (!text[idx]) return;
      item.querySelector("strong").innerText = text[idx][0];
      item.querySelector("span").innerText = text[idx][1];
    });
  }

  if (loginForm) {
    loginForm.querySelector(".auth-badge").innerText = zh ? "登录" : "LOGIN";
    loginForm.querySelector("h2").innerText = zh ? "登录 Exercise Agent" : "Sign in to Exercise Agent";
    loginForm.querySelector("p").innerText = zh ? "使用用户名和密码进入你的练习空间。" : "Use your username and password to access your exercise workspace.";
    loginForm.querySelector("label").childNodes[0].textContent = zh ? "用户名\n              " : "Username\n              ";
    document.getElementById("login-username").placeholder = zh ? "输入用户名" : "Enter your username";
    loginForm.querySelector("#login-username + span").innerText = zh ? "输入你创建账户时使用的用户名。" : "Enter the username you used when creating your account.";
    loginForm.querySelectorAll("label")[1].childNodes[0].textContent = zh ? "密码\n              " : "Password\n              ";
    document.getElementById("login-password").placeholder = zh ? "输入密码" : "Enter your password";
    loginForm.querySelector(".auth-check span").innerText = zh ? "记住我" : "Remember me";
    loginForm.querySelector(".auth-link").innerText = zh ? "创建账户" : "Create account";
    loginForm.querySelector(".auth-primary").innerText = zh ? "登录" : "Sign In";
    loginForm.querySelector(".auth-guest").innerText = zh ? "以访客身份继续" : "Continue as Guest";
    loginForm.querySelector(".auth-switch").childNodes[0].textContent = zh ? "还没有账户？ " : "Don't have an account? ";
    loginForm.querySelector(".auth-switch button").innerText = zh ? "创建一个" : "Create one";
  }

  if (registerForm) {
    registerForm.querySelector(".auth-badge").innerText = zh ? "注册" : "REGISTER";
    registerForm.querySelector("h2").innerText = zh ? "创建 Exercise Agent 账户" : "Create your Exercise Agent account";
    registerForm.querySelector("p").innerText = zh ? "填写表单，创建你的个人练习空间。" : "Complete the form below to create your personal exercise workspace.";
    const labels = registerForm.querySelectorAll("label");
    labels[0].childNodes[0].textContent = zh ? "用户名\n              " : "Username\n              ";
    document.getElementById("register-username").placeholder = zh ? "创建用户名" : "Create a username";
    registerForm.querySelector("#register-username + span").innerText = zh ? "选择一个用于登录的唯一用户名。" : "Choose a unique username for signing in.";
    labels[1].childNodes[0].textContent = zh ? "邮箱地址\n              " : "Email address\n              ";
    document.getElementById("register-email").placeholder = zh ? "输入邮箱" : "Enter your email";
    registerForm.querySelector("#register-email + span").innerText = zh ? "使用一个你可以访问的邮箱地址。" : "Use an email address you can access.";
    labels[2].childNodes[0].textContent = zh ? "密码\n                " : "Password\n                ";
    document.getElementById("register-password").placeholder = zh ? "创建密码" : "Create a password";
    labels[3].childNodes[0].textContent = zh ? "确认密码\n                " : "Confirm password\n                ";
    document.getElementById("register-confirm").placeholder = zh ? "再次输入密码" : "Re-enter password";
    registerForm.querySelector(".terms span").innerText = zh ? "我同意平台条款和隐私说明。" : "I agree to the platform terms and privacy notice.";
    registerForm.querySelector(".auth-primary").innerText = zh ? "创建账户" : "Create Account";
    registerForm.querySelector(".auth-switch").childNodes[0].textContent = zh ? "已经有账户？ " : "Already have an account? ";
    registerForm.querySelector(".auth-switch button").innerText = zh ? "登录" : "Sign in";
  }
}

function applyStaticI18n() {
  const zh = currentLang === "zh";
  const panelTitle = document.querySelector(".panel-title");
  if (panelTitle) panelTitle.innerText = t("title");
  const panelSubtitle = document.querySelector(".panel-subtitle");
  if (panelSubtitle) panelSubtitle.innerText = t("subtitle");

  const kbInfo = document.querySelector(".kb-info");
  const kbCount = document.getElementById("kb-count");
  if (kbInfo && kbCount) {
    const c = kbCount.innerText || "0";
    kbInfo.innerHTML = zh
      ? `知识库: <span id="kb-count">${c}</span> 份文档`
      : `Knowledge Base: <span id="kb-count">${c}</span> documents`;
  }

  const typeLabel = document.querySelector(".source-row .source-label");
  if (typeLabel) typeLabel.innerText = t("type");
  const sourceLabels = document.querySelectorAll(".source-row .source-label");
  if (sourceLabels && sourceLabels.length > 1) sourceLabels[1].innerText = t("count");

  const qMap = [
    ["fill_blank", "fill_blank"],
    ["multiple_choice", "multiple_choice"],
    ["short_answer", "short_answer"],
  ];
  qMap.forEach(([val, key]) => {
    const input = document.querySelector(`input[name="question-type"][value="${val}"]`);
    const label = input ? input.closest("label") : null;
    if (input && label) {
      label.innerHTML = "";
      label.appendChild(input);
      label.appendChild(document.createTextNode(` ${t(key)}`));
    }
  });

  const userInput = document.getElementById("user-input");
  if (userInput) {
    userInput.placeholder = zh
      ? "简要描述出题范围，例如：根据第3讲生成10道题..."
      : "Briefly describe the question scope, e.g., generate 10 questions from Lecture 3...";
  }
  const sendBtn = document.getElementById("send-btn");
  if (sendBtn && !sendBtn.disabled) sendBtn.innerText = t("generate_btn");

  const prevBtn = document.getElementById("exam-prev-btn");
  if (prevBtn) prevBtn.innerText = t("prev_question");
  const nextBtn = document.getElementById("exam-next-btn");
  if (nextBtn) nextBtn.innerText = t("next_question");
  const surveyBtn = document.querySelector(".survey-btn");
  if (surveyBtn) surveyBtn.innerText = t("survey");
  const examFeedback = document.getElementById("exam-feedback");
  if (examFeedback) examFeedback.innerText = t("feedback_default");
  const scenarioDesc = document.getElementById("scenario-entry-desc");
  if (scenarioDesc) scenarioDesc.innerText = t("scenario_entry_desc");
  const scenarioEntryBtn = document.getElementById("scenario-entry-btn");
  if (scenarioEntryBtn && scenarioEntryBtn.disabled) scenarioEntryBtn.innerText = t("scenario_entry_disabled");

  const uploadBtn = document.getElementById("upload-btn");
  if (uploadBtn && !uploadBtn.disabled) uploadBtn.innerText = t("upload_kb_btn");
  const pastBtn = document.getElementById("past-exam-upload-btn");
  if (pastBtn && !pastBtn.disabled) pastBtn.innerText = t("upload_past_btn");

  const kbTitle = document.querySelector(".bordered-box h2");
  if (kbTitle) kbTitle.innerText = zh ? "知识库" : "Knowledge Base";
  const hints = document.querySelectorAll(".hint");
  if (hints[0]) hints[0].innerHTML = zh ? "支持上传 <strong>txt, md, pdf, docx, pptx</strong> 等格式文件。" : "Supports uploading <strong>txt, md, pdf, docx, pptx</strong> and other formats.";
  if (hints[1]) hints[1].innerHTML = zh ? "支持上传 <strong>任意格式</strong> 的历年试卷文件（pdf、docx、pptx 等），系统将基于其生成相似题目。" : "Supports uploading <strong>any type</strong> of previous model files (pdf, docx, pptx, etc.). The system will generate similar questions based on the model.";

  const materialTitle = document.querySelector(".material-list-title");
  if (materialTitle) materialTitle.innerText = zh ? "选择参考资料（默认全选）" : "Select reference materials (enabled by default)";
  const selectAllBtn = document.getElementById("select-all-materials");
  if (selectAllBtn) selectAllBtn.innerText = zh ? "全选" : "Select All";
  const clearBtn = document.getElementById("clear-materials");
  if (clearBtn) clearBtn.innerText = zh ? "清空" : "Clear All";

  const examDbTitle = document.querySelector(".exam-db-title");
  if (examDbTitle) examDbTitle.innerText = zh ? "模拟题库" : "Model Question Bank";
  const examDbMeta = document.querySelector(".exam-db-meta");
  const pastCount = document.getElementById("past-exam-count");
  if (examDbMeta && pastCount) {
    const cnt = pastCount.innerText || "0";
    examDbMeta.innerHTML = zh
      ? `共 <span id="past-exam-count">${cnt}</span> 题`
      : `Total <span id="past-exam-count">${cnt}</span> questions`;
  }

  const scoreTitle = document.querySelector(".score-panel-title");
  if (scoreTitle) scoreTitle.innerText = zh ? "成绩折线图" : "Score Line Chart";
  const tipsTitle = document.querySelector(".tip-title");
  if (tipsTitle) tipsTitle.innerText = zh ? "提示" : "Tips";
  const tipItems = document.querySelectorAll(".tip-box li");
  if (tipItems[0]) tipItems[0].innerText = zh ? "优先上传质量较高、筛选后的文档（如综述、实证研究等）。" : "Upload high-quality filtered documents first (e.g., review papers, empirical studies, etc.).";
  if (tipItems[1]) tipItems[1].innerText = zh ? "建议上传课程讲义、课堂笔记等与你学习内容直接相关的资料。" : "Uploading lecture slides and coursework notes is highly recommended.";

  const scenarioTitles = document.querySelectorAll(".scenario-modal-title");
  if (scenarioTitles[0]) scenarioTitles[0].innerText = zh ? "情景练习" : "Scenario Practice";
  if (scenarioTitles[1]) scenarioTitles[1].innerText = zh ? "详细讲解" : "Detailed Explanation";
  const scenarioAnswerLabel = document.querySelector(".scenario-answer-label");
  if (scenarioAnswerLabel) scenarioAnswerLabel.innerText = t("your_answer");
  const scenarioAnswerInput = document.getElementById("scenario-modal-answer");
  if (scenarioAnswerInput) scenarioAnswerInput.placeholder = zh ? "请在这里写下你对新情景题的作答..." : "Write your answer for this scenario question here...";
  const scenarioSubmitBtn = document.getElementById("scenario-submit-btn");
  if (scenarioSubmitBtn) scenarioSubmitBtn.innerText = zh ? "提交答案" : "Submit Answer";
  const scenarioNextBtn = document.getElementById("scenario-next-btn");
  if (scenarioNextBtn) scenarioNextBtn.innerText = zh ? "再来一题" : "Another Question";
  const scenarioUnderstandBtn = document.getElementById("scenario-understand-btn");
  if (scenarioUnderstandBtn) scenarioUnderstandBtn.innerText = zh ? "我理解了" : "I Understand";
  const scenarioDontUnderstandBtn = document.getElementById("scenario-dont-understand-btn");
  if (scenarioDontUnderstandBtn) scenarioDontUnderstandBtn.innerText = zh ? "我还不理解" : "I Don't Understand";
  const scenarioQaTitle = document.querySelector("#scenario-qa-panel .qa-panel-title");
  if (scenarioQaTitle) scenarioQaTitle.innerText = zh ? "继续追问这个情景题" : "Continue Asking About This Scenario";
  const scenarioQaSub = document.querySelector("#scenario-qa-panel .qa-panel-subtitle");
  if (scenarioQaSub) scenarioQaSub.innerText = zh ? "你可以继续追问，例如：可以换个例子再解释一次吗？" : "You may ask follow-up questions, such as: Could you explain it with another example?";
  const scenarioQaInput = document.getElementById("scenario-qa-input");
  if (scenarioQaInput) scenarioQaInput.placeholder = zh ? "继续追问这个情景题..." : "Ask follow-up questions about this scenario.";

  const guestLoginBtn = document.getElementById("guest-login-btn");
  if (guestLoginBtn) guestLoginBtn.innerText = zh ? "登录" : "Login";
}

function setLanguage(lang) {
  currentLang = lang === "en" ? "en" : "zh";
  localStorage.setItem(LANG_KEY, currentLang);
  document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
  const btn = ensureLangToggleButton();
  const authBtn = document.getElementById("auth-lang-toggle-btn");
  const label = currentLang === "zh" ? "EN" : "\u4e2d\u6587";
  if (btn) btn.innerText = label;
  if (authBtn) authBtn.innerText = label;
  applyAuthI18n();
  applyStaticI18n();
  renderScoreChart();
  renderQuestionCard();
}

// Parse backend text (Q1, Q2, ...) into separate questions
function parseQuestionsFromText(rawText) {
  if (!rawText) return [];
  const text = String(rawText).replace(/\r\n/g, "\n").trim();
  if (!text) return [];

  const results = [];
  const regex = /(Q\d+\s*[.:銆乗)]?[\s\S]*?)(?=\nQ\d+\s*[.:銆乗)]?|\s*$)/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const block = match[1].trim();
    if (block) results.push(block);
  }

  // 濡傛灉妯″瀷娌℃湁鐢?Q1/Q2 鏍煎紡锛屽氨鎶婃暣娈靛綋浣滀竴棰?
  if (results.length === 0 && text) {
    results.push(text);
  }
  return results;
}

// ====== Score helpers ======

// 浠?localStorage 璇诲彇鍘嗗彶鎴愮哗
function loadScoreHistory() {
  try {
    const raw = localStorage.getItem(SCORE_HISTORY_KEY);
    if (!raw) {
      scoreHistory = [];
      return;
    }
    const parsed = JSON.parse(raw);
    scoreHistory = Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.error("鍔犺浇寰楀垎鍘嗗彶澶辫触:", e);
    scoreHistory = [];
  }
}

// 鎶婂巻鍙叉垚缁╁啓鍥?localStorage
function saveScoreHistory() {
  try {
    localStorage.setItem(SCORE_HISTORY_KEY, JSON.stringify(scoreHistory));
  } catch (e) {
    console.error("淇濆瓨寰楀垎鍘嗗彶澶辫触:", e);
  }
}

// 鏍规嵁鎵规敼鏂囨湰閲岀殑鈥滅粨鏋滐細...鈥濇帹鏂竴涓垎鏁?
// 鏄犲皠瑙勫垯锛氭纭?100锛岄儴鍒嗘纭?60锛岄敊璇?0
function mapFeedbackToScore(feedback) {
  if (!feedback) return null;
  const firstLine = String(feedback).split(/\r?\n/)[0] || "";

  if (firstLine.includes("Partially correct")) {
    return 60;
  }
  if (firstLine.includes("Correct")) {
    return 100;
  }
  if (firstLine.includes("Incorrect") || firstLine.includes("Not correct") || firstLine.includes("Wrong")) {
    return 0;
  }
  return null; // 鏃犳硶璇嗗埆灏变笉璁板叆鎶樼嚎鍥?
}

function computeRoundScoreFromEvaluations() {
  if (!questionList || questionList.length === 0) return null;

  const total = questionList.length;
  let correctCount = 0;
  let partialCount = 0;

  for (let i = 0; i < total; i++) {
    const fb = questionEvaluations[i] || "";
    const firstLine = String(fb).split(/\r?\n/)[0] || "";

    if (!firstLine) continue;

    if (firstLine.includes("Partially correct")) {
      partialCount += 1;
    } else if (firstLine.includes("Incorrect") || firstLine.includes("Not correct")|| firstLine.includes("Wrong")) {
      // wrong锛屼笉鍔犲垎
    } else if (firstLine.includes("Correct")) {
      correctCount += 1;
    }
  }

  if (total === 0) return null;

  // 姝ｇ‘棰樿 1 鍒嗭紝閮ㄥ垎姝ｇ‘璁?0.5 鍒嗭紙浣犲彲浠ユ寜闇€瑕佽皟鏁达級
  const accuracy = ((correctCount + 0.5 * partialCount) / total) * 100;
  return Math.round(accuracy);  // 鍥涜垗浜斿叆寰楀埌 0~100 鐨勬暣鏁?
}

// 鍦ㄩ〉闈笂缁樺埗鎶樼嚎鍥?
function renderScoreChart() {
  const canvas = document.getElementById("score-chart");
  if (!canvas) return;

  const latestSpan = document.getElementById("score-latest");
  const countSpan = document.getElementById("score-count");

  // 鏇存柊鏍囬鏃佽竟鐨勫皬鏂囧瓧
  if (!scoreHistory || scoreHistory.length === 0) {
    if (latestSpan) latestSpan.innerText = t("latest_empty");
    if (countSpan) countSpan.innerText = t("total_zero");

    const ctxEmpty = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = 180 * dpr;
    ctxEmpty.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctxEmpty.clearRect(0, 0, rect.width, 180);
    ctxEmpty.fillStyle = "#9ca3af";
    ctxEmpty.font = "12px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    ctxEmpty.fillText(t("no_score"), 16, 180 / 2);
    return;
  }

  const latest = scoreHistory[scoreHistory.length - 1];
  if (latestSpan) latestSpan.innerText = t("latest_points", { n: latest });
  if (countSpan) countSpan.innerText = t("total_attempts", { n: scoreHistory.length });

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = rect.width || 600;
  const cssHeight = 180;

  canvas.width = cssWidth * dpr;
  canvas.height = cssHeight * dpr;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const w = cssWidth;
  const h = cssHeight;

  ctx.clearRect(0, 0, w, h);

  const paddingLeft = 32;
  const paddingRight = 16;
  const paddingTop = 16;
  const paddingBottom = 24;

  const maxScore = 100;
  const minScore = 0;
  const n = scoreHistory.length;
  const innerWidth = w - paddingLeft - paddingRight;
  const innerHeight = h - paddingTop - paddingBottom;
  const xStep = n > 1 ? innerWidth / (n - 1) : 0;

  // 鍧愭爣杞?
  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(paddingLeft, paddingTop);
  ctx.lineTo(paddingLeft, h - paddingBottom);
  ctx.lineTo(w - paddingRight, h - paddingBottom);
  ctx.stroke();

  // Y 杞村埢搴︾嚎鍜屾枃瀛楋紙0 / 50 / 100锛?
  ctx.font = "10px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  [0, 50, 100].forEach((v) => {
    const ratio = (v - minScore) / (maxScore - minScore);
    const y = h - paddingBottom - ratio * innerHeight;

    ctx.strokeStyle = v === 0 ? "#e5e7eb" : "#f3f4f6";
    ctx.beginPath();
    ctx.moveTo(paddingLeft, y);
    ctx.lineTo(w - paddingRight, y);
    ctx.stroke();

    ctx.fillStyle = "#6b7280";
    ctx.fillText(String(v), 4, y + 3);
  });

  // 鎶樼嚎
  ctx.strokeStyle = "#3b82f6";
  ctx.lineWidth = 2;
  ctx.beginPath();
  scoreHistory.forEach((score, index) => {
    const x = paddingLeft + (n > 1 ? xStep * index : innerWidth / 2);
    const ratio = (score - minScore) / (maxScore - minScore);
    const y = h - paddingBottom - ratio * innerHeight;
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  // 鏁版嵁鐐?+ 涓婃柟灏忔暟瀛?
  scoreHistory.forEach((score, index) => {
    const x = paddingLeft + (n > 1 ? xStep * index : innerWidth / 2);
    const ratio = (score - minScore) / (maxScore - minScore);
    const y = h - paddingBottom - ratio * innerHeight;

    ctx.beginPath();
    ctx.fillStyle = "#1d4ed8";
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#111827";
    ctx.fillText(String(score), x - 8, y - 6);
  });

  // X 杞达細绗嚑娆?
  ctx.fillStyle = "#6b7280";
  for (let i = 0; i < n; i++) {
    const x = paddingLeft + (n > 1 ? xStep * i : innerWidth / 2);
    ctx.fillText(String(i + 1), x - 3, h - paddingBottom + 12);
  }
}

// ====== 鏂板锛氬悜 AI 鎻愰棶鍖哄煙鐨勬覆鏌?======
function appendQaBubble(role, text) {
  const win = document.getElementById("qa-chat-window");
  if (!win) return;

  // 濡傛灉杩樺湪鏄剧ず placeholder锛屽厛娓呯┖
  const placeholder = win.querySelector(".qa-placeholder");
  if (placeholder) {
    win.innerHTML = "";
  }

  const div = document.createElement("div");
  div.className = "qa-message " + (role === "user" ? "qa-user" : "qa-assistant");
  div.innerText = text;

  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

// 鎶娾€滃悜 AI 鎻愰棶鈥濆尯鍩熺殑闂鍙戠粰鍚庣
// 鎶娾€滄湰棰樿繘涓€姝ユ彁闂€濆尯鍩熺殑闂鍙戠粰鍚庣 / 鎴栫洿鎺ュ嚭鎸夐挳
async function sendQaQuestion() {
  const input = document.getElementById("qa-input");
  const btn = document.getElementById("qa-send-btn");
  const win = document.getElementById("qa-chat-window");
  if (!input || !btn || !win) return;

  const text = (input.value || "").trim();
  if (!text) {
    return;
  }

  // 褰撳墠璇曢鍒楄〃鍜屽綋鍓嶉鐩笅鏍囷紙鐢ㄤ簬缁欏悗绔澶栦笂涓嬫枃锛?
  const questions = questionList || [];
  const currentIndex =
    typeof currentQuestionIndex === "number" ? currentQuestionIndex : 0;

  // 褰撳墠鍕鹃€夌殑鏂囩尞鍒楄〃锛堜笌鐢熸垚璇曢鏃朵繚鎸佷竴鑷达級
  const selectedDocs = Array.from(
    document.querySelectorAll(".material-checkbox:checked")
  ).map((cb) => cb.value);

  // 猸?鍒ゆ柇鐢ㄦ埛鏄惁琛ㄨ揪鈥滃凡缁忔病鏈夌枒闂?/ 宸茬粡鐞嗚В浜嗏€?
  const normalized = text.toLowerCase();  // 鎴?text.trim().toLowerCase()
    const understandKeywords = [
    "no", "nothing", "no problem", "no problems", "no question", "no questions",
    "i understand", "i got it", "got it", "understood", "all clear", "clear now",
    "makes sense", "i'm good", "i'm fine", "nothing else", "that's all", "all good",
    "i'm done", "done", "no issues", "nothing more", "no further questions"
  ];
  const isUserNoMoreQuestions = understandKeywords.some((kw) =>
    normalized.includes(kw)
  );

  // 鍏堣拷鍔犱竴鏉°€岀敤鎴枫€嶆皵娉?
  appendQaBubble("user", text);

  // 鉁?鎯呭喌涓€锛氱敤鎴疯鈥滄病闂 / 娌℃湁鐤戦棶鈥濃€斺€旂洿鎺ュ嚭鎸夐挳锛屼笉鍐嶈 AI 璇翠竴澶ф
  if (isUserNoMoreQuestions) {
    // 鍙褰曠敤鎴疯繖鍙ュ埌鍘嗗彶閲屽嵆鍙?
    qaHistory.push({ role: "user", content: text });

    const btnRow = document.createElement("div");
    btnRow.className = "qa-message qa-assistant qa-options-row";

    const practiceBtn = document.createElement("button");
    practiceBtn.className = "qa-option-btn";
    practiceBtn.innerText = t("extra_practice");

    const nextBtn = document.createElement("button");
    nextBtn.className = "qa-option-btn qa-option-btn-secondary";
    nextBtn.innerText = t("next_question_action");

    btnRow.appendChild(practiceBtn);
    btnRow.appendChild(nextBtn);
    win.appendChild(btnRow);
    win.scrollTop = win.scrollHeight;

    // 宸╁浐缁冧範锛氭墦寮€涓庘€滄儏鏅縼绉荤粌涔犫€濆悓妯″紡鐨勭粌涔犵晫闈紙force = true锛?
    practiceBtn.addEventListener("click", () => {
      const idx =
        typeof currentQuestionIndex === "number" ? currentQuestionIndex : 0;
      generateScenarioQuestion(idx, practiceBtn, true);
    });

    // 杩涘叆涓嬩竴棰橈細澶嶇敤搴曢儴瀵艰埅閫昏緫
    nextBtn.addEventListener("click", () => {
      if (!questionList || questionList.length === 0) return;

      if (
        typeof currentQuestionIndex === "number" &&
        currentQuestionIndex < questionList.length - 1
      ) {
        currentQuestionIndex += 1;
        renderQuestionCard();
      } else {
        alert(t("no_more_questions_tip"));
      }
    });

    // 娓呯┖杈撳叆妗嗭紝缁撴潫鏈疆鎻愰棶
    input.value = "";
    return; // 猸?鍏抽敭锛氫笉鍐嶈姹?/api/qa
  }

  // 鉁?鎯呭喌浜岋細姝ｅ父鎻愰棶锛岀户缁蛋鍘熸潵鐨?/api/qa 娴佺▼
  btn.disabled = true;
  const oldLabel = btn.innerText;
  btn.innerText = "鎬濊€冧腑...";

  try {
    const res = await fetch("/api/qa", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        history: qaHistory,
        questions: questions,
        current_index: currentIndex,
        selected_docs: selectedDocs,
      }),
    });

    const data = await res.json();
    if (data.ok) {
      const reply = data.reply || "";
      appendQaBubble("assistant", reply);

      // 璁板綍鏈疆瀵硅瘽鍒?qaHistory
      qaHistory.push({ role: "user", content: text });
      qaHistory.push({ role: "assistant", content: reply });

      // 鍥炵瓟瀹岄棶棰樺悗锛屽啀鑷姩琛ヤ竴鍙モ€滃浜庢棰樿繕鏈変粈涔堢枒闂悧锛?+ 淇忕毊琛ㄦ儏鈥?
      const playfulEmojis = ["😊", "😎", "👍", "✨", "🤝", "🙂"];
      const randomEmoji =
        playfulEmojis[Math.floor(Math.random() * playfulEmojis.length)];
      const followupText = `${t("qa_followup_prompt")}${randomEmoji}`;

      appendQaBubble("assistant", followupText);
      qaHistory.push({ role: "assistant", content: followupText });
    } else {
      const msg = data.msg || "鏈煡閿欒";
      appendQaBubble("assistant", t("qa_error") + msg);
    }
  } catch (e) {
    console.error(e);
    appendQaBubble("assistant", t("qa_request_failed"));
  } finally {
    btn.disabled = false;
    btn.innerText = oldLabel || "→";
    input.value = "";
  }
}





function renderQuestionCard() {
  const container = document.getElementById("chat-window");
  if (!container) return;

  container.innerHTML = "";

  // 杩樻病鏈夐鐩椂鐨勬彁绀?
  if (!questionList || questionList.length === 0) {
    const hint = document.createElement("div");
    hint.className = "empty-hint";
    hint.innerText = t("empty_questions_hint");
    container.appendChild(hint);

    // 搴曢儴瀵艰埅鎸夐挳涓€璧风鐢?
    const bottomPrevBtn = document.getElementById("exam-prev-btn");
    const bottomNextBtn = document.getElementById("exam-next-btn");
    if (bottomPrevBtn && bottomNextBtn) {
      bottomPrevBtn.disabled = true;
      bottomNextBtn.disabled = true;
    }

    return;
  }

  const total = questionList.length;
  const idx = Math.max(0, Math.min(currentQuestionIndex, total - 1));
  currentQuestionIndex = idx;

  const wrapper = document.createElement("div");
  wrapper.className = "question-card-wrapper";

  const card = document.createElement("div");
  card.className = "question-card";

  // 棰樺彿
  const header = document.createElement("div");
  header.className = "question-card-header";
  header.innerText = t("question_x", { a: idx + 1, b: total });

  // 棰樺共
  const body = document.createElement("div");
  body.className = "question-card-body";
  body.innerText = questionList[idx];

  // 绛旈鍖哄煙
  const answerArea = document.createElement("div");
  answerArea.className = "answer-area";

  const answerLabel = document.createElement("div");
  answerLabel.className = "answer-label";
  answerLabel.innerText = t("your_answer");

  const answerInput = document.createElement("textarea");
  answerInput.className = "answer-input";
  answerInput.placeholder = "Write your answer here...";
  if (questionAnswers[idx]) {
    answerInput.value = questionAnswers[idx];
  }
  answerInput.addEventListener("input", (e) => {
    questionAnswers[idx] = e.target.value;
  });

  answerArea.appendChild(answerLabel);
  answerArea.appendChild(answerInput);

  card.appendChild(header);
  card.appendChild(body);
  card.appendChild(answerArea);

  // ===== 鎸夐挳 + 鎵规敼缁撴灉 =====
  const actions = document.createElement("div");
  actions.className = "card-actions";

  const submitBtn = document.createElement("button");
  submitBtn.className = "submit-btn";
  submitBtn.innerText = t("submit");

  const understandBtn = document.createElement("button");
  understandBtn.className = "understand-btn";
  understandBtn.innerText = t("got_it");

  const dontUnderstandBtn = document.createElement("button");
  dontUnderstandBtn.className = "dont-understand-btn";
  dontUnderstandBtn.innerText = t("i_dont_understand");

  // 鉁?鈥滅簿璁测€濇寜閽細鐢ㄦ潵鎵撳紑绮捐寮圭獥
  const explainBtn = document.createElement("button");
  explainBtn.className = "explain-btn";
  explainBtn.innerText = t("detailed_explain");

  // 鉁?鏂板 鈥淎sk AI鈥?鎸夐挳锛氳繘鍏ヤ换鎰忔彁闂ā寮?
  const askAiBtn = document.createElement("button");
  askAiBtn.className = "ask-ai-btn";
  askAiBtn.innerText = t("ask_ai");

  // 猸?鎶娾€淕ot it / I don't understand / Detailed Explanation / Ask AI鈥?鏀惧湪鍚屼竴琛?
  const understandRow = document.createElement("div");
  understandRow.className = "understand-row";
  understandRow.appendChild(understandBtn);
  understandRow.appendChild(dontUnderstandBtn);
  understandRow.appendChild(explainBtn);
  understandRow.appendChild(askAiBtn);


  // 鍙湁鎵规敼杩囧悗鎵嶈兘鐐圭悊瑙ｇ浉鍏虫寜閽?
    // 鍙湁鎵规敼杩囧悗鎵嶈兘鐐圭悊瑙ｇ浉鍏虫寜閽?
  let canClickUnderstand = false;
  if (
    Array.isArray(answeredFlags) &&
    answeredFlags.length === questionList.length
  ) {
    canClickUnderstand = !!answeredFlags[idx];
  }

  if (!canClickUnderstand) {
    understandBtn.disabled = true;
    dontUnderstandBtn.disabled = true;
    explainBtn.disabled = true;
    askAiBtn.disabled = true;

    const disableTip = t("need_submit_first");
    understandBtn.title = disableTip;
    dontUnderstandBtn.title = t("need_submit_finish");
    explainBtn.title = disableTip;
    askAiBtn.title = disableTip;
  } else {
    understandBtn.disabled = false;
    dontUnderstandBtn.disabled = false;
    explainBtn.disabled = false;
    askAiBtn.disabled = false;

    understandBtn.title = "";
    dontUnderstandBtn.title = "";
    explainBtn.title = "";
    askAiBtn.title = "";
  }


  // 鎵规敼缁撴灉鍖哄煙
  const resultBox = document.createElement("div");
  resultBox.className = "grade-result";
  if (questionEvaluations[idx]) {
    resultBox.innerText = questionEvaluations[idx];
  }

  // 绮捐鍐呭灞曠ず鍖哄煙锛堢幇鍦ㄥ彧鐢ㄦ潵淇濆瓨鏂囨湰锛屼笉鍦ㄩ鍗￠噷鐩存帴鏄剧ず锛?
  const explainBox = document.createElement("div");
  explainBox.className = "explain-detail";
  explainBox.style.display = "none";
  if (questionExplainText[idx]) {
    explainBox.innerText = questionExplainText[idx];
  }

  // 鎵规敼鎸夐挳閫昏緫
  submitBtn.addEventListener("click", () => {
    gradeQuestion(idx, submitBtn, resultBox);
  });

  // 鎴戠悊瑙ｄ簡锛氳烦涓嬩竴棰?
  understandBtn.addEventListener("click", () => {
    if (currentQuestionIndex < questionList.length - 1) {
      currentQuestionIndex += 1;
      renderQuestionCard();
    } else {
      alert("This is already the last question. You may now review the feedback above or revisit the incorrect questions.");
    }
  });

  // 鎴戞病鐞嗚В锛氳蛋绮捐 + 鑱婂ぉ閫昏緫
  dontUnderstandBtn.addEventListener("click", () => {
    handleDontUnderstand(idx);
  });

  explainBtn.addEventListener("click", () => {
    openExplainModal(idx, explainBtn);
  });

    // Ask AI锛氭墦寮€浠绘剰鎻愰棶妯″紡
  askAiBtn.addEventListener("click", () => {
    handleAskAi(idx);
  });


  // 鎸夋樉绀洪『搴忥細鎻愪氦绛旀 -> 鎵规敼缁撴灉 -> 鈥滄垜鐞嗚В浜?+ 鎴戞病鐞嗚В鈥濅竴琛?
  actions.appendChild(submitBtn);
  actions.appendChild(resultBox);
  actions.appendChild(understandRow);

  card.appendChild(actions);
  card.appendChild(explainBox);

  // ===== 鍦ㄩ鐩崱鐗囧簳閮ㄥ鍔犫€滄湰棰樹笓灞炲璇濇鈥濓紙榛樿鏀惰捣锛岀偣鈥滄垜娌＄悊瑙ｂ€濇椂灞曞紑锛?====
  const explainStage = questionExplainStage[idx] || 0; // 鍏堜繚鐣欙紝鍚庨潰濡傛灉闇€瑕佸尯鍒嗛樁娈佃繕鍙互鐢?

  const qaPanel = document.createElement("div");
  qaPanel.className = "qa-panel";
  qaPanel.id = "question-qa-panel";

  const qaHeader = document.createElement("div");
  qaHeader.className = "qa-panel-header";

  const qaTitle = document.createElement("div");
  qaTitle.className = "qa-panel-title";
  qaTitle.innerText = t("followup_title");

  const qaSubtitle = document.createElement("div");
  qaSubtitle.className = "qa-panel-subtitle";
  qaSubtitle.innerText = "You may ask follow-up questions about this problem.";

  qaHeader.appendChild(qaTitle);
  qaHeader.appendChild(qaSubtitle);

  const qaChatWindow = document.createElement("div");
  qaChatWindow.id = "qa-chat-window";
  qaChatWindow.className = "qa-chat-window";

  // 鏈杩涗竴姝ユ彁闂?鈥斺€?鍒濆姘旀场鏂囨锛? 涓煭鍙ヤ腑闅忔満閫?1 涓級
  const followupHints = [
    "Is there anything you still don鈥檛 understand?",
"Do you have any other questions?",
"Which parts are still unclear to you?",
"Are there any concepts from this topic that remain confusing?",
"Is there anything you鈥檇 like further clarification on?",
"Did we miss any questions you still want to ask?",
"Which part are you still unsure about?"

  ];
  const randomHint =
    followupHints[Math.floor(Math.random() * followupHints.length)];

  const qaPlaceholder = document.createElement("div");
  qaPlaceholder.className = "qa-placeholder";
  qaPlaceholder.innerText = randomHint;
  qaChatWindow.appendChild(qaPlaceholder);


  const qaInputRow = document.createElement("div");
  qaInputRow.className = "textarea-row qa-input-row";

  const qaInput = document.createElement("textarea");
  qaInput.id = "qa-input";
  qaInput.placeholder = "You may ask further questions about this problem.";

  const qaButton = document.createElement("button");
  qaButton.id = "qa-send-btn";
  qaButton.innerText = "→";

  qaInputRow.appendChild(qaInput);
  qaInputRow.appendChild(qaButton);

  qaPanel.appendChild(qaHeader);
  qaPanel.appendChild(qaChatWindow);
  qaPanel.appendChild(qaInputRow);

  // 鍒濆闅愯棌锛氱偣鍑烩€滄垜娌＄悊瑙ｂ€濇椂鍐嶆樉绀?
  qaPanel.style.display = "none";

  card.appendChild(qaPanel);

  qaButton.addEventListener("click", sendQaQuestion);
  qaInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendQaQuestion();
    }
  });



    // === 鎯呮櫙杩佺Щ鍖哄煙鏀逛负搴曢儴缁熶竴鍏ュ彛锛屼笉鍐嶆斁鍦ㄩ鍗″唴閮?===
  updateScenarioEntry(idx);

  wrapper.appendChild(card);
  container.appendChild(wrapper);



  // 搴曢儴宸﹀彸瀵艰埅鎸夐挳
  const bottomPrevBtn = document.getElementById("exam-prev-btn");
  const bottomNextBtn = document.getElementById("exam-next-btn");

  if (bottomPrevBtn && bottomNextBtn) {
    bottomPrevBtn.disabled = idx === 0;
    bottomNextBtn.disabled = idx === total - 1;

    bottomPrevBtn.onclick = () => {
      if (currentQuestionIndex > 0) {
        currentQuestionIndex -= 1;
        renderQuestionCard();
      }
    };

    bottomNextBtn.onclick = () => {
      if (currentQuestionIndex < questionList.length - 1) {
        currentQuestionIndex += 1;
        renderQuestionCard();
      }
    };
  }
}

// 鏍规嵁褰撳墠棰樼洰锛屾洿鏂板簳閮ㄧ殑鈥滄儏鏅縼绉荤粌涔犫€濆叆鍙?
function updateScenarioEntry(idx) {
  const titleEl = document.getElementById("scenario-entry-title");
  const descEl = document.getElementById("scenario-entry-desc");
  const btn = document.getElementById("scenario-entry-btn");

  if (!titleEl || !descEl || !btn) return;

  titleEl.textContent = t("scenario_title");
  descEl.textContent =
    "When this question is marked as incorrect, you may click the button below to generate a new scenario-based practice question from the same knowledge point.";

  const isWrong =
    wrongQuestions && wrongQuestions.some((item) => item.index === idx);

  btn.disabled = !isWrong;
btn.textContent = isWrong
  ? t("scenario_generate")
  : "Scenario practice available only after incorrect answer";

  btn.onclick = () => {
    const latestIsWrong =
      wrongQuestions && wrongQuestions.some((item) => item.index === idx);
    if (!latestIsWrong) {
      alert("You can only generate a scenario practice after this question has been marked as incorrect.");
      return;
    }

    // 宸茬粡鐢熸垚杩囨儏鏅锛岀洿鎺ユ墦寮€寮圭獥锛涘惁鍒欏厛鐢熸垚鍐嶆墦寮€
    if (scenarioQuestionTexts[idx]) {
      openScenarioModal(idx);
    } else {
      generateScenarioQuestion(idx, btn);
    }
  };
}

// 鎶婂唴瀛樹腑鐨勬儏鏅鐘舵€佸～鍏呭埌寮圭獥 UI
function fillScenarioModalFromState(idx) {
  const modalQuestion = document.getElementById("scenario-modal-question");
  const answerInput = document.getElementById("scenario-modal-answer");
  const resultBox = document.getElementById("scenario-modal-result");
  const explainBox = document.getElementById("scenario-modal-explain");
  const qaPanel = document.getElementById("scenario-qa-panel");
  const qaWindow = document.getElementById("scenario-qa-window");

  if (!modalQuestion || !answerInput || !resultBox || !explainBox) return;

  const q = scenarioQuestionTexts[idx] || "";
  modalQuestion.textContent = q || t("scenario_not_ready");

  answerInput.value = scenarioAnswers[idx] || "";
  resultBox.textContent = scenarioEvaluations[idx] || "";

  const explainText = scenarioExplainText[idx] || "";
  explainBox.textContent = explainText;
  explainBox.style.display = explainText ? "block" : "none";

  if (qaPanel && qaWindow) {
    qaPanel.style.display = "none";
    qaWindow.innerHTML = "";
    delete qaWindow.dataset.initialized;
  }
}

// 鉁?鏍规嵁鎯呮櫙棰樻槸鍚﹀凡缁忔壒鏀癸紝鎺у埗鈥滄垜鐞嗚В浜?/ 鎴戜笉鐞嗚В / 鍐嶆潵涓€棰?/ AI 鎻愰棶鈥濇槸鍚﹀彲鐢?
function updateScenarioButtonsState(idx) {
  const scenarioUnderstandBtn = document.getElementById("scenario-understand-btn");
  const scenarioDontUnderstandBtn = document.getElementById("scenario-dont-understand-btn");
  const scenarioNextBtn = document.getElementById("scenario-next-btn");
  const scenarioQaInput = document.getElementById("scenario-qa-input");
  const scenarioQaBtn = document.getElementById("scenario-qa-send-btn");

  const hasGraded =
    Array.isArray(scenarioEvaluations) &&
    typeof idx === "number" &&
    scenarioEvaluations[idx] &&
    scenarioEvaluations[idx].trim() !== "";

  const disabled = !hasGraded;

  if (scenarioUnderstandBtn) {
    scenarioUnderstandBtn.disabled = disabled;
    scenarioUnderstandBtn.title = disabled ? t("scenario_submit_first") : "";
  }
  if (scenarioDontUnderstandBtn) {
    scenarioDontUnderstandBtn.disabled = disabled;
    scenarioDontUnderstandBtn.title = disabled ? t("need_submit_finish") : "";
  }
  if (scenarioNextBtn) {
    scenarioNextBtn.disabled = disabled;
    scenarioNextBtn.title = disabled ? t("scenario_submit_first") : "";
  }
  if (scenarioQaInput) {
    scenarioQaInput.disabled = disabled;
    scenarioQaInput.placeholder = disabled
      ? t("scenario_modal_need_submit")
      :" You may ask further questions about this topic.";
  }
  if (scenarioQaBtn) {
    scenarioQaBtn.disabled = disabled;
  }
}


// 鎵撳紑鎯呮櫙杩佺Щ缁冧範寮圭獥
function openScenarioModal(idx) {
  const modal = document.getElementById("scenario-modal");
  if (!modal) return;

  if (!scenarioQuestionTexts[idx]) {
    alert(t("scenario_need_generate"));
    return;
  }

  currentScenarioIndex = idx;
  fillScenarioModalFromState(idx);

  // 鉁?鎵撳紑寮圭獥鏃讹紝鏍规嵁鏄惁宸茬粡鎵规敼杩囨儏鏅锛岀粺涓€鎺у埗鍏朵粬鎸夐挳鐘舵€?
  updateScenarioButtonsState(idx);

  modal.classList.remove("hidden");
}


// 鍏抽棴寮圭獥
function closeScenarioModal() {
  const modal = document.getElementById("scenario-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
}




// 猸?鍗曢鎵规敼锛氳皟鐢ㄥ悗绔?/api/grade
async function gradeQuestion(idx, submitBtn, resultBox) {
  if (!questionList || !questionList[idx]) return;

  const questionText = questionList[idx];
  const answerText = (questionAnswers[idx] || "").trim();

  if (!answerText) {
    alert(t("please_input_answer"));
    return;
  }

  // 棰樺瀷锛氭部鐢ㄥ乏渚у崟閫夋锛堣鍚庣鐭ラ亾鏄～绌?/ 閫夋嫨 / 绠€绛旓級
  const typeInput = document.querySelector(
    'input[name="question-type"]:checked'
  );
  const questionType = typeInput ? typeInput.value : "short_answer";

  // 鍕鹃€夌殑鏂囩尞鍒楄〃锛堜笌鐢熸垚棰樼洰鏃朵繚鎸佷竴鑷达級
  const selectedDocs = Array.from(
    document.querySelectorAll(".material-checkbox:checked")
  ).map((cb) => cb.value);

  // 鎸夐挳鐘舵€佸垏鎹?
  let oldLabel = "";
  if (submitBtn) {
    submitBtn.disabled = true;
    oldLabel = submitBtn.innerText;
    submitBtn.innerText = "Grading...";
  }
  if (resultBox) {
    resultBox.innerText = "";
  }

  try {
    const res = await fetch("/api/grade", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: questionText,
        answer: answerText,
        question_type: questionType,
        selected_docs: selectedDocs,
      }),
    });

    const data = await res.json();

    if (data.ok) {
      const feedback = data.result || "Grading completed.";

      // 1锔忊儯 淇濆瓨鎵规敼缁撴灉锛堝垏棰樺啀鍥炴潵杩樿兘鐪嬪埌锛?
      questionEvaluations[idx] = feedback;
      if (resultBox) {
        // 鉁?鍙洿鏂板綋鍓嶅崱鐗囨寜閽笅鏂圭殑缁撴灉鍖哄煙
        resultBox.innerText = feedback;
      }

      // 2锔忊儯 瑙ｆ瀽鈥滅粨鏋滐細姝ｇ‘ / 閮ㄥ垎姝ｇ‘ / 閿欒鈥?
      const firstLine = String(feedback).split(/\r?\n/)[0] || "";
      let verdict = "unknown";
      if (firstLine.includes("Partially correct")) {
        verdict = "partial";
      } else if (firstLine.includes("Incorrect") || firstLine.includes("Not correct")|| firstLine.includes("Wrong")) {
        verdict = "wrong";
      } else if (firstLine.includes("Correct")) {
        verdict = "correct";
      }

      // 3锔忊儯 濡傛灉鏄€滈敊璇鐩€濓紝璁板綍鍒?wrongQuestions锛堝彧璁颁竴娆★級
      if (verdict === "wrong") {
        if (!wrongQuestions) wrongQuestions = [];
        const exists = wrongQuestions.some((item) => item.index === idx);
        if (!exists) {
          wrongQuestions.push({
            index: idx,
            question: questionText,
            student_answer: answerText,
            feedback: feedback,
            question_type: questionType,
          });
        }
      }

      // 4锔忊儯 鏍囪璇ラ宸茬粡瀹屾垚鎵规敼锛堢敤浜庝竴杞瓟棰樼粺璁★級
      if (answeredFlags && answeredFlags.length > idx) {
        answeredFlags[idx] = true;
      }

      // 5锔忊儯 鎵规敼瀹屾垚鍚庯紝绔嬪嵆瑙ｉ攣銆屾垜鐞嗚В浜?/ 鎴戞病鐞嗚В / 绮捐銆嶆寜閽?
      const understandBtn = document.querySelector(".understand-btn");
      const dontUnderstandBtn = document.querySelector(".dont-understand-btn");
      const explainBtn = document.querySelector(".explain-btn");
      const askAiBtn = document.querySelector(".ask-ai-btn");   // 馃啎 鏂板杩欎竴琛?

      if (understandBtn) {
          understandBtn.disabled = false;
          understandBtn.title = "";
      }
      if (dontUnderstandBtn) {
          dontUnderstandBtn.disabled = false;
          dontUnderstandBtn.title = "";
      }
      if (explainBtn) {
          explainBtn.disabled = false;
          explainBtn.title = "";
      }
      if (askAiBtn) {                       // 馃啎 鏂板杩欎竴娈?
          askAiBtn.disabled = false;
          askAiBtn.title = "";
      }



      // 鈿狅笍 鍏抽敭锛氫笉鍐嶉噸鏂版覆鏌撴暣寮犻鐩崱鐗囷紝閬垮厤棰樼洰琚竻绌?
      // renderQuestionCard();

      // 7锔忊儯 妫€鏌ユ槸鍚﹀畬鎴愪竴杞瓟棰橈紝鐢ㄤ簬鐢熸垚涓€у寲鍙嶉 & 鎶樼嚎鍥?
      checkRoundAndRequestFeedback();
    } else {
      const msg = data.msg || t("grading_failed");
      if (resultBox) {
        resultBox.innerText = msg;
      } else {
        alert(msg);
      }
    }
  } catch (e) {
    console.error(e);
    const msg = t("network_error_grade");
    if (resultBox) {
      resultBox.innerText = msg;
    } else {
      alert(msg);
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = oldLabel || t("submit");
    }
  }

  updateScenarioEntry(idx);
}



// 猸?鎯呮櫙杩佺Щ棰橈細鍚戝悗绔姹傚熀浜庨敊棰樼敓鎴愭柊鎯呭
async function generateScenarioQuestion(idx, btn, force = false) {
  if (!questionList || !questionList[idx]) return;

  const questionText = questionList[idx];
  const ans = (questionAnswers[idx] || "").trim();
  const fb = questionEvaluations[idx] || "";

  // 纭繚鏈宸茬粡琚垽瀹氫负閿欒锛坵rongQuestions 閲屽瓨鍦ㄥ搴?index锛?
  const isWrong =
    wrongQuestions &&
    wrongQuestions.some((item) => item.index === idx);

  // 猸?榛樿浠嶇劧鍙鈥滈敊棰樷€濆紑鏀炬儏鏅縼绉伙紱鐗规畩鍦烘櫙鍙互閫氳繃 force = true 璺宠繃闄愬埗
  if (!isWrong && !force) {
    alert("Scenario practice is available only after this question is marked incorrect.");
    return;
  }

  // 棰樺瀷锛堜笌鍑洪/鎵规敼淇濇寔涓€鑷达級
  const typeInput = document.querySelector(
    'input[name="question-type"]:checked'
  );
  const questionType = typeInput ? typeInput.value : "short_answer";

  // 鍕鹃€夌殑鏂囩尞锛堜笌鍑洪鏃朵繚鎸佷竴鑷达級
  const selectedDocs = Array.from(
    document.querySelectorAll(".material-checkbox:checked")
  ).map((cb) => cb.value);

  if (btn) {
    btn.disabled = true;
    var oldLabel = btn.innerText;
    btn.innerText = t("generate_loading");
  }

  try {
    const res = await fetch("/api/scenario_question", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: questionText,
        student_answer: ans,
        feedback: fb,
        question_type: questionType,
        selected_docs: selectedDocs,
      }),
    });

    const data = await res.json();
    if (data.ok && data.scenario_question) {
      // 璁板綍杩欓亾棰樼殑鎯呮櫙棰樺共锛屽苟閲嶇疆鍏朵綔绛?鎵规敼
      scenarioQuestionTexts[idx] = data.scenario_question;

      if (!Array.isArray(scenarioAnswers)) scenarioAnswers = [];
      if (!Array.isArray(scenarioEvaluations)) scenarioEvaluations = [];

      scenarioAnswers[idx] = "";
      scenarioEvaluations[idx] = "";
      scenarioExplainStage[idx] = 0;
      scenarioExplainText[idx] = "";
      scenarioQaHistory = [];

      // 鐩存帴鎵撳紑鎯呮櫙杩佺Щ缁冧範寮圭獥
      openScenarioModal(idx);

      // 閲嶆柊娓叉煋褰撳墠棰樺崱锛屽睍绀烘儏鏅鍜屼綔绛斿尯鍩?
      renderQuestionCard();
    } else {
      const msg = data.msg || (currentLang === "zh" ? "????????????????" : "Unable to generate the scenario question for now. Please try again later.");
      alert(msg);
    }
  } catch (e) {
    console.error(e);
    alert((currentLang === "zh" ? "??????????????????????" : "A network or service error occurred while generating the scenario question. Please try again later."));
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = oldLabel || t("scenario_generate");
    }
  }
}

// 猸?鎯呮櫙杩佺Щ棰樻壒鏀癸細澶嶇敤 /api/grade 鎺ュ彛
async function gradeScenarioQuestion(idx, submitBtn, resultBox) {
  const sQuestion = scenarioQuestionTexts[idx];
  if (!sQuestion) {
    alert(t("scenario_need_generate"));
    return;
  }

  const sAnswer = (scenarioAnswers[idx] || "").trim();
  if (!sAnswer) {
    alert(t("please_input_answer"));
    return;
  }

  const typeInput = document.querySelector(
    'input[name="question-type"]:checked'
  );
  const questionType = typeInput ? typeInput.value : "short_answer";

  const selectedDocs = Array.from(
    document.querySelectorAll(".material-checkbox:checked")
  ).map((cb) => cb.value);

  if (submitBtn) {
    submitBtn.disabled = true;
    var oldLabel = submitBtn.innerText;
    submitBtn.innerText = "Grading...";
  }
  if (resultBox) {
    resultBox.innerText = "";
  }

  try {
    const res = await fetch("/api/grade", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: sQuestion,
        answer: sAnswer,
        question_type: questionType,
        selected_docs: selectedDocs,
      }),
    });

        const data = await res.json();
    if (data.ok && data.result) {
      // /api/grade 杩斿洖瀛楁鍚嶆槸 result锛岃繖閲屼繚鎸佷竴鑷?
      scenarioEvaluations[idx] = data.result;
      if (resultBox) {
        resultBox.innerText = data.result;
      }

      // 鉁?鎵规敼鎴愬姛鍚庯紝鎵嶅厑璁哥偣鍑烩€滄垜鐞嗚В浜?/ 鎴戜笉鐞嗚В / 鍐嶆潵涓€棰?/ AI 鎻愰棶鈥?
      updateScenarioButtonsState(idx);
    }else {
      const msg = data.msg || "Unable to grade the scenario question for now.";
      if (resultBox) {
        resultBox.innerText = msg;
      } else {
        alert(msg);
      }
    }
  } catch (e) {
    console.error(e);
    const msg = (currentLang === "zh" ? "??????????????????????" : "Network or service error occurred while grading the scenario question. Please try again later.");
    if (resultBox) {
      resultBox.innerText = msg;
    } else {
      alert(msg);
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = oldLabel || "Submit Scenario Answer";
    }
  }
}


// 猸?绮捐妯″紡 + 鈥滄湰棰樼户缁拷闂€濊亰澶╅€昏緫
// ===== 绮捐寮圭獥鐩稿叧閫昏緫 =====
function openExplainModal(idx, triggerBtn) {
  if (!questionList || !questionList[idx]) return;

  const modal = document.getElementById("explain-modal");
  const questionEl = document.getElementById("explain-modal-question");
  const contentEl = document.getElementById("explain-modal-content");

  if (!modal || !questionEl || !contentEl) return;

  // 鏄剧ず褰撳墠棰樼洰
  questionEl.textContent = questionList[idx] || "";
  modal.classList.remove("hidden");

  // 濡傛灉宸茬粡鐢熸垚杩囩簿璁诧紝鐩存帴鐢ㄧ紦瀛?
  const existing = questionExplainText[idx];
  if (existing) {
    contentEl.innerText = existing;
    return;
  }

  // 杩樻病鐢熸垚杩囩簿璁诧紝鍏堟樉绀烘彁绀猴紝鍐嶅悜鍚庣璇锋眰
  contentEl.innerText =
    "正在生成这道题的详细讲解，请稍候...";

  generateExplainForQuestion(idx, contentEl, triggerBtn);
}

async function generateExplainForQuestion(idx, contentEl, triggerBtn) {
  if (!questionList || !questionList[idx]) return;

  const questionText = questionList[idx];
  const answerText = (questionAnswers[idx] || "").trim();
  const feedbackText = (questionEvaluations[idx] || "").trim();

  const typeInput = document.querySelector(
    'input[name="question-type"]:checked'
  );
  const questionType = typeInput ? typeInput.value : "short_answer";

  const selectedDocs = Array.from(
    document.querySelectorAll(".material-checkbox:checked")
  ).map((cb) => cb.value);

  let oldLabel = "";
  if (triggerBtn) {
    oldLabel = triggerBtn.innerText;
    triggerBtn.disabled = true;
    triggerBtn.innerText = "Generating explanation...";
  }

  try {
    const res = await fetch("/api/explain_detailed", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: questionText,
        answer: answerText,
        feedback: feedbackText,
        question_type: questionType,
        selected_docs: selectedDocs,
      }),
    });

    const data = await res.json();
    if (data.ok) {
      const explanation =
        data.explanation || "(Unable to generate explanation, please try again later.)";

      // 璁板綍绮捐鐘舵€佷笌鏂囨湰锛屼究浜庡垏棰樺洖鏉ュ悗澶嶇敤
      questionExplainStage[idx] = 1;
      questionExplainText[idx] = explanation;

      if (contentEl) {
        contentEl.innerText = explanation;
      }
    } else {
      const msg = data.msg || "Failed to generate explanation, please try again.";
      if (contentEl) {
        contentEl.innerText = "鉂?" + msg;
      } else {
        alert(msg);
      }
    }
  } catch (e) {
    console.error(e);
    const msg = "Network error. Unable to generate explanation, please try again.";
    if (contentEl) {
      contentEl.innerText = "鉂?" + msg;
    } else {
      alert(msg);
    }
  } finally {
    if (triggerBtn) {
      triggerBtn.disabled = false;
      triggerBtn.innerText = oldLabel || "Explain";
    }
  }
}

function closeExplainModal() {
  const modal = document.getElementById("explain-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

// ===== t("i_dont_understand") button in main question card: only opens AI dialog, no automatic detailed explanation =====
async function handleDontUnderstand(idx) {
  if (!questionList || !questionList[idx]) return;

  const qaPanel = document.getElementById("question-qa-panel");
  const qaWindow = document.getElementById("qa-chat-window");
  const qaInput = document.getElementById("qa-input");

  // 鎵撳紑骞惰缃负鈥滄湰棰樿拷闂€濇ā寮忕殑鏍囬
  if (qaPanel) {
    qaPanel.style.display = "flex"; // .qa-panel 鏄?flex 甯冨眬

    const qaTitleEl = qaPanel.querySelector(".qa-panel-title");
    const qaSubtitleEl = qaPanel.querySelector(".qa-panel-subtitle");
    if (qaTitleEl) {
      qaTitleEl.innerText = currentLang === "zh" ? "继续追问这道题" : "Follow-up Questions";
    }
    if (qaSubtitleEl) {
      qaSubtitleEl.innerText =
        currentLang === "zh" ? "围绕当前题目继续提问，我会结合题目上下文回答。" : "Ask about the current question and I will answer with this problem's context.";
    }
  }

  if (qaWindow) {
    // 绗竴娆¤繘鍏モ€滄湰棰樿拷闂€濇ā寮忔椂锛岀粰涓€鍙ュ紩瀵艰瘽
    if (!qaWindow.dataset.initialized) {
      const followupPrompts = [
        "Which knowledge point is still unclear?",
        "Do you have any other questions?",
        "Which concept is still not fully understood?",
        "Is there anything from this content that remains unclear?",
        "Would you like clarification on any part?",
        "Is there any unanswered question you would like to add?",
        "Which part of the topic is still confusing?"
      ];

      const randomPrompt =
        followupPrompts[Math.floor(Math.random() * followupPrompts.length)];

      // 濡傛灉宸茬粡鏈夊叾瀹冩秷鎭紙姣斿 Ask AI 鍏堟墦寮€杩囷級锛屽氨涓嶈娓呯┖锛屽彧杩藉姞鎻愮ず
      const hasMessages = qaWindow.querySelector(".qa-message");
      if (!hasMessages) {
        qaWindow.innerHTML = "";
      }

      appendQaBubble("assistant", randomPrompt);
      qaWindow.dataset.initialized = "1";
    }

    qaWindow.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (qaInput) {
    qaInput.placeholder =
      "You may ask further questions about this problem.";
    qaInput.focus();
  }
}

// Ask AI锛氭墦寮€鈥滃彲浠ラ棶浠讳綍涓滆タ鈥濈殑瀵硅瘽妗?
async function handleAskAi(idx) {
  if (!questionList || !questionList[idx]) return;

  const qaPanel = document.getElementById("question-qa-panel");
  const qaWindow = document.getElementById("qa-chat-window");
  const qaInput = document.getElementById("qa-input");

  if (qaPanel) {
    qaPanel.style.display = "flex";

    const qaTitleEl = qaPanel.querySelector(".qa-panel-title");
    const qaSubtitleEl = qaPanel.querySelector(".qa-panel-subtitle");
    if (qaTitleEl) {
      qaTitleEl.innerText = currentLang === "zh" ? "Ask AI" : "Ask AI";
    }
    if (qaSubtitleEl) {
      qaSubtitleEl.innerText = currentLang === "zh" ? "可以继续提问概念、解题思路或相关知识点。" : "Ask about concepts, reasoning steps, or related knowledge points.";
    }
  }

  if (qaWindow) {
    // 绗竴娆′娇鐢?Ask AI 鏃剁粰涓€鍙ュ紑鍦虹櫧
    if (!qaWindow.dataset.askAiInitialized) {
      appendQaBubble("assistant", "What can I help you with?");
      qaWindow.dataset.askAiInitialized = "1";
    }

    qaWindow.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (qaInput) {
    qaInput.placeholder = "Type your question here...";
    qaInput.focus();
  }
}



// Scenario-based question version of t("i_dont_understand")
// Scenario-based question version of t("i_dont_understand") 鈥?directly enter AI Q&A mode (same logic as main exam questions)
async function handleScenarioDontUnderstand() {
  if (currentScenarioIndex == null) return;
  const idx = currentScenarioIndex;

  const question = (scenarioQuestionTexts[idx] || "").trim();
  if (!question) {
    alert(t("scenario_need_generate"));
    return;
  }

  const qaPanel = document.getElementById("scenario-qa-panel");
  const qaWindow = document.getElementById("scenario-qa-window");
  const qaInput = document.getElementById("scenario-qa-input");

  // Open the QA panel for this question
  if (qaPanel) {
    qaPanel.style.display = "flex"; // .qa-panel is usually flex layout
  }

  if (qaWindow) {
    // When opening for the first time, show one guidance message (same 7 short variations as main exam)
    if (!qaWindow.dataset.initialized) {
      qaWindow.innerHTML = "";

      const followupPrompts = [
        "Which part is still unclear?",
        "Do you have any unresolved questions?",
        "Which knowledge point is not fully understood yet?",
        "Any concepts still unclear from this topic?",
        "Would you like clarification on anything?",
        "Is there any unanswered question you'd like to raise?",
        "Which part of the content is still confusing?"
      ];

      const randomPrompt =
        followupPrompts[Math.floor(Math.random() * followupPrompts.length)];

      appendScenarioQaBubble("assistant", randomPrompt);
      qaWindow.dataset.initialized = "1";
    }

    qaWindow.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (qaInput) {
    qaInput.focus();
  }
}


function appendScenarioQaBubble(role, text) {
  const win = document.getElementById("scenario-qa-window");
  if (!win) return;
  const div = document.createElement("div");
  div.className =
    "qa-message " + (role === "user" ? "qa-user" : "qa-assistant");
  div.textContent = text;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

async function sendScenarioQaQuestion() {
  if (currentScenarioIndex == null) return;

  const input = document.getElementById("scenario-qa-input");
  const btn = document.getElementById("scenario-qa-send-btn");
  const win = document.getElementById("scenario-qa-window");
  if (!input || !btn || !win) return;

  const text = input.value.trim();
  if (!text) return;

// 鉁?Same logic as main Q&A: detect whether user means 鈥淚 have no more questions鈥?
const normalized = text.toLowerCase();  // 鎴?text.trim().toLowerCase()
  const understandKeywords = [
    "no", "nothing", "no problem", "no problems", "no question", "no questions",
    "i understand", "i got it", "got it", "understood", "all clear", "clear now",
    "makes sense", "i'm good", "i'm fine", "nothing else", "that's all", "all good",
    "i'm done", "done", "no issues", "nothing more", "no further questions"
  ];
const isUserNoMoreQuestions = understandKeywords.some((kw) =>
  normalized.includes(kw)
);

// Display user's message and push to history
appendScenarioQaBubble("user", text);
scenarioQaHistory.push({ role: "user", content: text });
input.value = "";

// 鉁?Case 1: User says 鈥淣o questions / understood / clear鈥?鈥?do NOT call /api/qa, show two buttons instead
if (isUserNoMoreQuestions) {
  const btnRow = document.createElement("div");
  btnRow.className = "qa-message qa-assistant qa-options-row";

  const againBtn = document.createElement("button");
  againBtn.className = "qa-option-btn";
  againBtn.innerText = "One more question";

  const endBtn = document.createElement("button");
  endBtn.className = "qa-option-btn qa-option-btn-secondary";
  endBtn.innerText = "Finish practice";

  btnRow.appendChild(againBtn);
  btnRow.appendChild(endBtn);
  win.appendChild(btnRow);
  win.scrollTop = win.scrollHeight;

  // 鈥淥ne more question鈥?= regenerate a new scenario question under the same knowledge point
  againBtn.addEventListener("click", () => {
    if (currentScenarioIndex == null) return;
    const idx = currentScenarioIndex;
    generateScenarioQuestion(idx, againBtn, true); // force = true 鈫?refresh immediately
  });

  // 鈥淔inish practice鈥?= close scenario modal
  endBtn.addEventListener("click", () => {
    closeScenarioModal();
  });

  return; // 猸?Stop here 鈥?do not request /api/qa
}


// 鉁?Case 2: User continues asking 鈥?go through /api/qa flow
btn.disabled = true;
const oldLabel = btn.innerText;
btn.innerText = "思考中...";

const question = scenarioQuestionTexts[currentScenarioIndex] || "";
const selectedDocs = Array.from(
  document.querySelectorAll(".material-checkbox:checked")
).map((cb) => cb.value);

try {
  const resp = await fetch("/api/qa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: text,
      history: scenarioQaHistory,
      questions: question ? [question] : [],
      current_index: 0,
      selected_docs: selectedDocs,
    }),
  });
  const data = await resp.json();
  if (data.ok) {
    const reply = data.reply || "";

    // 鈶?Display normal assistant reply inside scenario chat window
    appendScenarioQaBubble("assistant", reply);

    // 鈶?Add playful follow-up: 鈥淎ny more questions?鈥?
    const playfulEmojis = ["😊", "😎", "👍", "✨", "🤝", "🙂"];
    const randomEmoji =
      playfulEmojis[Math.floor(Math.random() * playfulEmojis.length)];
    const followupText = `Any more questions regarding this topic? ${randomEmoji}`;

    appendScenarioQaBubble("assistant", followupText);

    // 鈶?Update history
    scenarioQaHistory.push({ role: "assistant", content: reply });
    scenarioQaHistory.push({ role: "assistant", content: followupText });
  } else {
    appendScenarioQaBubble(
      "assistant",
      "鈿狅笍 Request failed: " + (data.msg || (currentLang === "zh" ? "????" : "Unknown error"))
    );
  }
} catch (err) {
  console.error(err);
  appendScenarioQaBubble("assistant", "鈿狅笍 Request failed, please try again later.");
} finally {
  btn.disabled = false;
  btn.innerText = oldLabel;
}
}

// 猸?Check whether "all questions of this round have been answered" and request personalized feedback from backend
function checkRoundAndRequestFeedback() {
  if (!questionList || questionList.length === 0) return;
  if (!answeredFlags || answeredFlags.length !== questionList.length) return;

  const allAnswered = answeredFlags.every((v) => v);
  if (!allAnswered || hasShownRoundFeedback) return;

  hasShownRoundFeedback = true;

  // 猸?1. 浠庡綋鍓嶅崟閫夋鎷块鍨嬶紙鏁磋疆缁熶竴绫诲瀷锛?
  const typeInput = document.querySelector(
    'input[name="question-type"]:checked'
  );
  const questionType = typeInput ? typeInput.value : "short_answer";

  // 猸?2. 鎶婃湰杞墍鏈夐鐩墦鍖呮垚 all_items
  const allItems = questionList.map((q, idx) => {
    const evalText = questionEvaluations[idx] || "";
    const ansText = (questionAnswers[idx] || "").trim();

    const firstLine = String(evalText).split(/\r?\n/)[0] || "";
    let verdict = "unknown";
    if (firstLine.includes("Partially correct")) {
      verdict = "partial";
    } else if (
      firstLine.includes("Incorrect") ||
      firstLine.includes("Not correct") ||
      firstLine.includes("Wrong")
    ) {
      verdict = "wrong";
    } else if (firstLine.includes("Correct")) {
      verdict = "correct";
    }

    return {
      index: idx,
      question: q,
      student_answer: ansText,
      evaluation: evalText,
      verdict: verdict,
      question_type: questionType,
    };
  });

  const roundScore = computeRoundScoreFromEvaluations();
  if (typeof roundScore === "number") {
    scoreHistory.push(roundScore);
    saveScoreHistory();
    renderScoreChart();
  }

  const feedbackBox = document.getElementById("exam-feedback");
  if (!wrongQuestions || wrongQuestions.length === 0) {
    // No mistakes this round
    if (feedbackBox) {
      feedbackBox.innerText =
        "All answers in this round are correct. No weak knowledge points detected. Keep going!";
    }
    return;
  }

  if (feedbackBox) {
    feedbackBox.innerText = "正在根据错题生成个性化反馈，请稍候...";
  }

    fetch("/api/exam_feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      wrong_items: wrongQuestions,
      all_items: allItems,       // 猸?鏂板锛氭湰杞墍鏈夐鐩?
      round_score: roundScore,   // 猸?鏂板锛氭湰杞緱鍒?
    }),
  })

    .then((res) => res.json())
    .then((data) => {
      if (data.ok && data.feedback) {
        showExamFeedback(data.feedback);
      } else {
        const msg = data.msg || "Unable to generate personalized feedback temporarily.";
        showExamFeedback(msg);
      }
    })
    .catch((err) => {
      console.error(err);
      showExamFeedback((currentLang === "zh" ? "????????????????" : "An error occurred while generating feedback. Please try again later."));
    });
}

// 猸?Display personalized feedback on the page
function showExamFeedback(text) {
  const feedbackBox = document.getElementById("exam-feedback");
  if (feedbackBox) {
    feedbackBox.innerText = text;
  }
}


function setQuestions(rawText) {
  questionList = parseQuestionsFromText(rawText);
  questionAnswers = new Array(questionList.length).fill("");
  questionEvaluations = new Array(questionList.length).fill("");  // Initialize evaluation result
  questionExplainStage = new Array(questionList.length).fill(0);
  questionExplainText = new Array(questionList.length).fill("");

  currentQuestionIndex = 0;

  // 猸?Each t("generate_btn") action is treated as starting a new practice round
  answeredFlags = new Array(questionList.length).fill(false);
  wrongQuestions = [];
  hasShownRoundFeedback = false;

   // 猸?Reset scenario-based training states
  scenarioQuestionTexts = new Array(questionList.length).fill("");
  scenarioAnswers = new Array(questionList.length).fill("");
  scenarioEvaluations = new Array(questionList.length).fill("");

  // Reset personalized feedback display area
  const feedbackBox = document.getElementById("exam-feedback");
  if (feedbackBox) {
    feedbackBox.innerText = "After completing all questions, I will tell you which knowledge points need improvement.";
  }

  renderQuestionCard();
}



// Convert URLs in text into clickable <a> links
function renderTextWithLinks(container, text) {
  // Match http/https links and capture trailing punctuation
  const urlRegex = /(https?:\/\/[^\s)]+)([).,;:!?]?)/g;

  let lastIndex = 0;
  let match;

  while ((match = urlRegex.exec(text)) !== null) {
    const url = match[1];
    const punctuation = match[2] || "";
    const start = match.index;

    // Add normal text before URL
    if (start > lastIndex) {
      const plainText = text.slice(lastIndex, start);
      container.appendChild(document.createTextNode(plainText));
    }

    // Create <a> tag
    const a = document.createElement("a");
    a.href = url;
    a.textContent = url;
    a.target = "_blank"; // Open new tab
    a.rel = "noopener noreferrer";
    container.appendChild(a);

    // Add punctuation after link if exists
    if (punctuation) {
      container.appendChild(document.createTextNode(punctuation));
    }

    lastIndex = urlRegex.lastIndex;
  }

  // Process remaining text after the last URL
  if (lastIndex < text.length) {
    container.appendChild(document.createTextNode(text.slice(lastIndex)));
  }
}

// Append a chat message
function appendMessage(role, text) {
  const chatWindow = document.getElementById("chat-window");
  const bubble = document.createElement("div");
  bubble.classList.add("msg");

  if (role === "user") {
    bubble.classList.add("msg-user");
    // User messages remain plain text
    bubble.innerText = text;
  } else {
    bubble.classList.add("msg-bot");
    // Bot messages: convert URLs into clickable links
    renderTextWithLinks(bubble, text);
  }

  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Render selectable material list on the right panel
function renderMaterialList(files) {
  const container = document.getElementById("material-list");
  if (!container) return;

  container.innerHTML = "";

  if (!files || files.length === 0) {
    container.innerHTML =
      "<div class='empty-hint'>The knowledge base is currently empty. Please upload files above.</div>";
    return;
  }

  files.forEach((name) => {
    const label = document.createElement("label");
    label.className = "material-item";

    // Checkbox: controls whether used for question generation
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = name;
    checkbox.className = "material-checkbox";
    checkbox.checked = true; // Default selected

    // File name
    const span = document.createElement("span");
    span.className = "material-name";
    span.textContent = name;

    // Trash button: delete this file
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "material-delete-btn";
    delBtn.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M3 6h18"></path>
        <path d="M8 6V4h8v2"></path>
        <path d="M6 6l1 15h10l1-15"></path>
        <path d="M10 10v7"></path>
        <path d="M14 10v7"></path>
      </svg>
    `;
    delBtn.setAttribute("aria-label", t("delete_file_title"));
    delBtn.title = t("delete_file_title");

    delBtn.addEventListener("click", (event) => {
      // Prevent the checkbox toggling when clicking delete
      event.preventDefault();
      event.stopPropagation();
      removeMaterialItemUI(label);
      deleteMaterialFile(name, label);
    });

    label.appendChild(checkbox);
    label.appendChild(span);
    label.appendChild(delBtn);
    container.appendChild(label);
  });
}

// 馃啎 UI-only delete effect: instantly remove material from the interface
function removeMaterialItemUI(labelEl) {
  if (!labelEl) return;

  // 1) Remove DOM element
  if (typeof labelEl.remove === "function") {
    labelEl.remove();
  } else if (labelEl.parentNode) {
    labelEl.parentNode.removeChild(labelEl);
  }

  // 2) Update the "Current Knowledge Base Count"
  const container = document.getElementById("material-list");
  const countSpan = document.getElementById("kb-count");

  if (container && countSpan) {
    const current = container.querySelectorAll(".material-item").length;
    countSpan.innerText = current;

    // 3) If no materials remain, show empty message
    if (current === 0) {
      container.innerHTML =
        "<div class='empty-hint'>The knowledge base is currently empty. Please upload files above.</div>";
    }
  }
}


// Delete a knowledge base file 鈥?notify backend only, UI already handled
async function deleteMaterialFile(name) {
  if (!name) return;

  const sendBtn = document.getElementById("send-btn");
  const oldSendLabel = sendBtn ? sendBtn.innerText : "";

  // 鍒犻櫎鏈熼棿涔熻涓?KB 涓嶅彲鐢?
  kbReady = false;
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.innerText = t("kb_rebuilding");
  }


  try {
    const res = await fetch("/api/material/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: name }),
    });
    const data = await res.json();

    if (!data.ok) {
      // Backend failure fallback 鈥?UI will NOT revert
      alert(t("delete_failed") +  + (data.msg || (currentLang === "zh" ? "????" : "Unknown error")));
    }
  } catch (e) {
    console.error("Failed to delete file:", e);
    alert(t("delete_failed_server"));
  }
}


// ==========================
// 馃啎 Past Exam Question Bank: list / add / delete
// ==========================

// Load all past exam questions from backend
async function loadPastExamDb() {
  try {
    const res = await fetch("/api/past_exam/list");
    const data = await res.json();
    if (data.ok) {
      pastExamQuestions = data.questions || [];
      renderPastExamList();
    } else {
      console.error("Failed to load past exam database:", data.msg);
    }
  } catch (e) {
    console.error("Failed to load past exam database:", e);
  }
}

// Render pastExamQuestions into the right-side list (each question includes a checkbox)
function renderPastExamList() {
  const container = document.getElementById("previous-files-list");
  const countSpan = document.getElementById("past-exam-count");
  if (!container) return;

  container.innerHTML = "";

  if (!pastExamQuestions || pastExamQuestions.length === 0) {
    container.innerHTML = "";
    if (countSpan) countSpan.innerText = "0";
    return;
  }

  if (countSpan) {
    countSpan.innerText = String(pastExamQuestions.length);
  }

  pastExamQuestions.forEach((item) => {
    const row = document.createElement("div");
    row.className = "exam-db-item";

    // Row 1: checkbox + question text
    const headerRow = document.createElement("div");
    headerRow.className = "exam-db-item-header";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "past-exam-checkbox";
    if (item.id != null) {
      checkbox.value = String(item.id);
    } else {
      // If no id, use full question text as fallback
      checkbox.value = item.question || "";
    }
    checkbox.checked = true; // Default checked

    const textDiv = document.createElement("div");
    textDiv.className = "exam-db-text";
    textDiv.textContent = item.question || "";

    headerRow.appendChild(checkbox);
    headerRow.appendChild(textDiv);

    // Row 2: year / paper / type + delete button
    const metaLine = document.createElement("div");
    metaLine.className = "exam-db-meta-line";

    const metaSpan = document.createElement("span");
    const pieces = [];
    if (item.year) pieces.push(item.year);
    if (item.paper) pieces.push(item.paper);
    if (item.question_type) pieces.push(item.question_type);
    metaSpan.textContent = pieces.join(" 路 ") || t("no_metadata");

    const delBtn = document.createElement("button");
    delBtn.className = "exam-db-delete-btn";
    delBtn.type = "button";
    delBtn.textContent = t("delete_btn");
    delBtn.addEventListener("click", () => {
      deletePastExamQuestion(item.id, item.question);
    });

    metaLine.appendChild(metaSpan);
    metaLine.appendChild(delBtn);

    row.appendChild(headerRow);
    row.appendChild(metaLine);
    container.appendChild(row);
  });
}



// Read a question from the right-side form and call /api/past_exam/add to save it into the database
async function addPastExamQuestionFromForm() {
  const textarea = document.getElementById("past-exam-question-input");
  const typeSelect = document.getElementById("past-exam-question-type");
  const yearInput = document.getElementById("past-exam-year");
  const paperInput = document.getElementById("past-exam-paper");

  if (!textarea) return;

  const question = (textarea.value || "").trim();
  if (!question) {
    alert((currentLang === "zh" ? "????????????????" : "Please paste a past exam question into the text box first."));
    return;
  }

  const body = {
    question,
    question_type: typeSelect ? typeSelect.value : "short_answer",
    meta: {
      year: yearInput ? yearInput.value.trim() : "",
      paper: paperInput ? paperInput.value.trim() : "",
    },
  };

  try {
    const res = await fetch("/api/past_exam/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.ok) {
      // Clear input fields
      textarea.value = "";
      if (yearInput) yearInput.value = "";
      if (paperInput) paperInput.value = "";

      // Append new record to front-end cache and refresh list
      if (!pastExamQuestions) pastExamQuestions = [];
      pastExamQuestions.push(data.record);
      renderPastExamList();
    } else {
      alert("Save failed: " + (data.msg || (currentLang === "zh" ? "????" : "Unknown error")));
    }
  } catch (e) {
    console.error(e);
    alert("Save failed, please check if the server is running.");
  }
}

// Call /api/past_exam/delete to delete a specific question
async function deletePastExamQuestion(id, questionText) {
  if (!confirm("Are you sure you want to delete this question from the past exam library?")) {
    return;
  }

  try {
    const res = await fetch("/api/past_exam/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: id,
        question: questionText,
      }),
    });
    const data = await res.json();
    if (data.ok) {
      const deleted = data.deleted || 0;
      if (deleted > 0) {
        // Remove corresponding record from the front-end array
        pastExamQuestions = pastExamQuestions.filter((item) => {
          if (id != null && item.id === id) return false;
          if (id == null && questionText && item.question === questionText)
            return false;
          return true;
        });
        renderPastExamList();
      }
    } else {
      alert(t("delete_failed") +  + (data.msg || (currentLang === "zh" ? "????" : "Unknown error")));
    }
  } catch (e) {
    console.error(e);
    alert(t("delete_failed_server"));
  }
}

async function refreshKbStats() {
  try {
    // 馃憠 鏀逛负璋冪敤鏂扮殑 /api/kb_status
    const res = await fetch("/api/kb_status");
    const data = await res.json();
    if (!data.ok) return;

    const files = data.files || [];
    const kbCountEl = document.getElementById("kb-count");
    if (kbCountEl) {
      kbCountEl.innerText = data.total_files ?? files.length;
    }

    // 鏇存柊宸︿晶鏂囦欢鍒楄〃
    renderMaterialList(files);

    // 馃憠 鏍规嵁鍚庣杩斿洖鐨?ready 鐘舵€侊紝缁熶竴鎺у埗鍏ㄥ眬 kbReady 鍜屾寜閽?
    const sendBtn = document.getElementById("send-btn");
    const ready = !!data.ready;  // 鍚庣宸茬粡鎶娿€屾湁鏂囦欢 + 鍚戦噺搴撻潪绌恒€嶄竴璧峰垽鏂ソ浜?
    kbReady = ready;

    if (sendBtn) {
      sendBtn.disabled = !ready;
      if (ready) {
        sendBtn.innerText = t("generate_btn");
      } else if (files.length === 0) {
        sendBtn.innerText = t("upload_material_first");
      } else {
        sendBtn.innerText = t("kb_rebuilding");
      }
    }
  } catch (e) {
    console.error("Failed to get knowledge base stats:", e);
  }
}


// Send message (Generate questions)
async function sendMessage() {
  if (!kbReady) {
    const chatWindow = document.getElementById("chat-window");
    const msg = (currentLang === "zh" ? "???????????????????????????" : "The knowledge base is rebuilding the vector database. Please wait a few seconds before clicking 'Generate Questions'.");
    if (chatWindow) {
      chatWindow.innerHTML = "<div class='error-hint'>" + msg + "</div>";
    } else {
      alert(msg);
    }
    return;
  }

  const input = document.getElementById("user-input");
  const btn = document.getElementById("send-btn");
  const text = input.value.trim();

  // Question type: read from radio input
  const typeInput = document.querySelector('input[name="question-type"]:checked');
  const questionType = typeInput ? typeInput.value : "fill_blank";

  // Number of questions: read from number input
  const countInput = document.getElementById("question-count");
  let numQuestions = parseInt(countInput.value, 10);
  if (isNaN(numQuestions) || numQuestions <= 0) {
    numQuestions = 5;
  }

  // Selected document list
  const selectedDocs = Array.from(
    document.querySelectorAll(".material-checkbox:checked")
  ).map((cb) => cb.value);

  // Do not generate chat bubble on the left, only keep card-style question display
  input.value = "";

  btn.disabled = true;
  const oldLabel = btn.innerText;
  btn.innerText = t("generate_loading");

  try {
    // 馃啎 Collect selected question IDs from past exam question bank
    const selectedPastExamIds = Array.from(
      document.querySelectorAll(".past-exam-checkbox:checked")
    )
      .map((cb) => parseInt(cb.value, 10))
      .filter((id) => !Number.isNaN(id));

    if (selectedDocs.length === 0 && selectedPastExamIds.length === 0) {
      const chatWindow = document.getElementById("chat-window");
      const msg = t("checking_docs_before_generate");
      if (chatWindow) {
        chatWindow.innerHTML = "<div class='error-hint'>" + msg + "</div>";
      } else {
        alert(msg);
      }
      return;  // 鉀?End here, do not call backend
    }

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        history: chatHistory,
        question_type: questionType,
        num_questions: numQuestions,
        selected_docs: selectedDocs, // 猸?Send selected documents to backend
        selected_past_exam_ids: selectedPastExamIds,
      }),
    });

    const data = await res.json();
    if (data.ok) {
      // Parse returned questions into individual cards and render
      setQuestions(data.reply);

      // Update local history: only record when user typed something
      if (text) {
        chatHistory.push({ role: "user", content: text });
      }
      chatHistory.push({ role: "assistant", content: data.reply });
    } else {
      const chatWindow = document.getElementById("chat-window");
      const msg = t("error_prefix") +  + (data.msg || (currentLang === "zh" ? "????" : "Unknown error"));
      if (chatWindow) {
        chatWindow.innerHTML = "<div class='error-hint'>" + msg + "</div>";
      } else {
        alert(msg);
      }
    }
  } catch (e) {
    console.error(e);
    const chatWindow = document.getElementById("chat-window");
    const msg = t("request_failed");
    if (chatWindow) {
      chatWindow.innerHTML = "<div class='error-hint'>" + msg + "</div>";
    } else {
      alert(msg);
    }
  } finally {
    btn.disabled = false;
    btn.innerText = oldLabel || t("generate_btn");
  }
}



// Upload files to knowledge base
async function uploadFiles() {
  const fileInput = document.getElementById("file-input");
  const btn = document.getElementById("upload-btn");
  const resultDiv = document.getElementById("upload-result");
  const sendBtn = document.getElementById("send-btn");

  const files = fileInput.files;
  if (!files || files.length === 0) {
    resultDiv.innerText = t("select_file_first");
    return;
  }

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  // 猸?Record original button label
  const oldLabel = btn.innerText;
  const oldSendLabel = sendBtn ? sendBtn.innerText : "";

  // 猸?Mark: knowledge base enters "rebuilding" status and lock the generate button
  kbReady = false;
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.innerText = t("kb_rebuilding");
  }

  btn.disabled = true;
  btn.innerText = t("uploading");

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (data.ok) {
      resultDiv.innerText =
        "Uploaded files: " +
        data.saved.join(", ") +
        "\nCurrent knowledge base contains " +
        data.total_files +
        " document(s).";
      fileInput.value = "";
      // Refresh metadata and update document selection list
      refreshKbStats();
    } else {
      resultDiv.innerText = t("upload_failed") +  + (data.msg || (currentLang === "zh" ? "????" : "Unknown error"));
    }
  } catch (e) {
    console.error(e);
    resultDiv.innerText = t("upload_failed_server");
  } finally {
    // 涓婁紶鎸夐挳鎭㈠鐢辫嚜宸辨帶鍒?
    btn.disabled = false;
    btn.innerText = oldLabel || t("upload_kb_btn");
    // 馃憠 kbReady 鍜?sendBtn 鐨勭姸鎬佸畬鍏ㄤ氦缁?refreshKbStats()锛堝拰 /api/kb_status锛夌鐞?
  }
}


/// ==========================
// 馃啎 Past Exam Papers: File Upload + Auto Question Extraction
// ==========================
async function uploadPastExamFiles() {
  const fileInput = document.getElementById("past-exam-file-input");
  const btn = document.getElementById("past-exam-upload-btn");
  const resultDiv = document.getElementById("past-exam-upload-result");

  if (!fileInput || !btn || !resultDiv) return;

  const files = fileInput.files;
  if (!files || files.length === 0) {
    resultDiv.innerText = t("upload_exam_first");
    return;
  }

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);   // 鉁?Any file type allowed, no frontend validation
  }

  const oldLabel = btn.innerText;
  btn.disabled = true;
  btn.innerText = t("upload_parse_loading");
  resultDiv.innerText = "";

  try {
    const res = await fetch("/api/past_exam/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.ok) {
      // Clear selection
      fileInput.value = "";

      // Overwrite frontend cache with latest question bank from backend
      pastExamQuestions = data.questions || [];
      renderPastExamList();

      const savedCount = (data.saved_files || []).length;
      const importedCount = data.imported_count ?? 0;
      resultDiv.innerText = t("upload_exam_ok", { saved: savedCount, imported: importedCount });
    } else {
      resultDiv.innerText = t("upload_failed") + (data.msg || (currentLang === "zh" ? "????" : "Unknown error"));
    }
  } catch (e) {
    console.error(e);
    resultDiv.innerText = t("upload_failed_server");
  } finally {
    btn.disabled = false;
    btn.innerText = oldLabel || t("upload_past_btn");
  }
}


// ==========================
// Exercise Agent auth UI
// ==========================
function setAuthMode(mode) {
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const isRegister = mode === "register";

  document.body.classList.toggle("auth-register", isRegister);
  if (loginForm) loginForm.classList.toggle("hidden", isRegister);
  if (registerForm) registerForm.classList.toggle("hidden", !isRegister);

  const loginMsg = document.getElementById("login-message");
  const registerMsg = document.getElementById("register-message");
  if (loginMsg) loginMsg.textContent = "";
  if (registerMsg) registerMsg.textContent = "";
}

function showApp(username) {
  const authScreen = document.getElementById("auth-screen");
  const page = document.querySelector(".page");
  const accountChip = document.getElementById("account-chip");
  const accountName = document.getElementById("account-name");
  const guestLoginBtn = document.getElementById("guest-login-btn");

  document.body.classList.remove("auth-open", "auth-register");
  if (authScreen) authScreen.classList.add("hidden");
  if (page) page.classList.remove("app-hidden");
  if (accountChip) accountChip.classList.toggle("hidden", !username);
  if (accountName) accountName.textContent = username || "";
  if (guestLoginBtn) guestLoginBtn.classList.toggle("hidden", !!username);
  updateAccountAvatar(username);
  refreshKbStats();
  loadPastExamDb();
}

function showAuth() {
  const authScreen = document.getElementById("auth-screen");
  const page = document.querySelector(".page");
  const accountChip = document.getElementById("account-chip");
  const guestLoginBtn = document.getElementById("guest-login-btn");

  document.body.classList.add("auth-open");
  if (authScreen) authScreen.classList.remove("hidden");
  if (page) page.classList.add("app-hidden");
  if (accountChip) accountChip.classList.add("hidden");
  if (guestLoginBtn) guestLoginBtn.classList.add("hidden");
  setAuthMode("login");
}

async function postAuth(url, body = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(data.msg || "Authentication failed.");
  }
  return data;
}

function setAuthMessage(id, text, success = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("success", !!success);
}

function bindAuthUi() {
  document.querySelectorAll("[data-auth-mode]").forEach((btn) => {
    btn.addEventListener("click", () => setAuthMode(btn.dataset.authMode));
  });

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = loginForm.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.disabled = true;
      setAuthMessage("login-message", "");
      try {
        const data = await postAuth("/api/auth/login", {
          username: document.getElementById("login-username").value,
          password: document.getElementById("login-password").value,
        });
        setAuthMessage("login-message", "Signed in successfully.", true);
        showApp(data.username);
      } catch (err) {
        setAuthMessage("login-message", err.message);
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = registerForm.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.disabled = true;
      setAuthMessage("register-message", "");
      try {
        const data = await postAuth("/api/auth/register", {
          username: document.getElementById("register-username").value,
          email: document.getElementById("register-email").value,
          password: document.getElementById("register-password").value,
          confirm_password: document.getElementById("register-confirm").value,
        });
        setAuthMessage("register-message", "Account created.", true);
        showApp(data.username);
      } catch (err) {
        setAuthMessage("register-message", err.message);
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  const guestBtn = document.getElementById("guest-btn");
  if (guestBtn) {
    guestBtn.addEventListener("click", async () => {
      guestBtn.disabled = true;
      setAuthMessage("login-message", "");
      try {
        await postAuth("/api/auth/guest");
        showApp("");
      } catch (err) {
        setAuthMessage("login-message", err.message);
      } finally {
        guestBtn.disabled = false;
      }
    });
  }

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      logoutBtn.disabled = true;
      try {
        await postAuth("/api/auth/logout");
        showAuth();
      } catch (err) {
        alert(err.message);
      } finally {
        logoutBtn.disabled = false;
      }
    });
  }

  const guestLoginBtn = document.getElementById("guest-login-btn");
  if (guestLoginBtn) {
    guestLoginBtn.addEventListener("click", async () => {
      guestLoginBtn.disabled = true;
      try {
        await postAuth("/api/auth/logout");
        showAuth();
      } catch (err) {
        showAuth();
      } finally {
        guestLoginBtn.disabled = false;
      }
    });
  }
}

// 浜嬩欢缁戝畾
document.addEventListener("DOMContentLoaded", () => {
  bindAuthUi();

  const langBtn = ensureLangToggleButton();
  if (langBtn) {
    langBtn.addEventListener("click", () => {
      setLanguage(currentLang === "zh" ? "en" : "zh");
    });
  }
  const authLangBtn = document.getElementById("auth-lang-toggle-btn");
  if (authLangBtn) {
    authLangBtn.addEventListener("click", () => {
      setLanguage(currentLang === "zh" ? "en" : "zh");
    });
  }

  const sendBtn = document.getElementById("send-btn");
  const uploadBtn = document.getElementById("upload-btn");
  const input = document.getElementById("user-input");
  const selectAllBtn = document.getElementById("select-all-materials");
  const clearBtn = document.getElementById("clear-materials");
  const pastExamUploadBtn = document.getElementById("past-exam-upload-btn");
  const explainCloseBtn = document.getElementById("explain-close-btn");
  if (explainCloseBtn) {
    explainCloseBtn.addEventListener("click", closeExplainModal);
  }



  if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
  }
  if (uploadBtn) {
    uploadBtn.addEventListener("click", uploadFiles);
  }
  if (pastExamUploadBtn) {
    pastExamUploadBtn.addEventListener("click", uploadPastExamFiles);
  }

  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      document
        .querySelectorAll(".material-checkbox")
        .forEach((cb) => (cb.checked = true));
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      document
        .querySelectorAll(".material-checkbox")
        .forEach((cb) => (cb.checked = false));
    });
  }

  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // 鍒濇鍔犺浇鏃惰幏鍙栫煡璇嗗簱缁熻 + 鏂囩尞鍒楄〃
  refreshKbStats();
  // 馃啎 鍚屾椂鎶婅繃寰€璇曞嵎棰樺簱涔熷姞杞藉嚭鏉?
  loadPastExamDb();

  loadScoreHistory();
  renderScoreChart();
  renderQuestionCard();
  const accountName = document.getElementById("account-name");
  updateAccountAvatar(accountName ? accountName.textContent : "");
  setLanguage(localStorage.getItem(LANG_KEY) || "zh");
});

window.addEventListener("resize", () => {
  renderScoreChart();
});

document.addEventListener("DOMContentLoaded", () => {
  // ===== 鍘熸潵鐨勫悜 AI 鎻愰棶锛堜富闈㈡澘锛?=====
  const qaBtn = document.getElementById("qa-send-btn");
  const qaInput = document.getElementById("qa-input");

  if (qaBtn) {
    qaBtn.addEventListener("click", sendQaQuestion);
  }

  if (qaInput) {
    qaInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        sendQaQuestion();
      }
    });
  }

  // ===== 鎯呮櫙杩佺Щ寮圭獥鎸夐挳缁戝畾 =====
  const scenarioCloseBtn = document.getElementById("scenario-close-btn");
  const scenarioUnderstandBtn = document.getElementById("scenario-understand-btn");
  const scenarioSubmitBtn = document.getElementById("scenario-submit-btn");
  const scenarioDontUnderstandBtn = document.getElementById(
    "scenario-dont-understand-btn"
  );
  const scenarioNextBtn = document.getElementById("scenario-next-btn");
  const scenarioAnswerInput = document.getElementById("scenario-modal-answer");
  const scenarioQaBtn = document.getElementById("scenario-qa-send-btn");
  const scenarioQaInput = document.getElementById("scenario-qa-input");

  if (scenarioCloseBtn) {
    scenarioCloseBtn.addEventListener("click", closeScenarioModal);
  }

  if (scenarioUnderstandBtn) {
    scenarioUnderstandBtn.addEventListener("click", () => {
      // 鈥滄垜鐞嗚В浜嗏€?= 鐩存帴鍏抽棴鎯呮櫙缁冧範鐣岄潰
      closeScenarioModal();
    });
  }

  if (scenarioSubmitBtn) {
    scenarioSubmitBtn.addEventListener("click", () => {
      if (currentScenarioIndex == null) return;
      const idx = currentScenarioIndex;
      if (scenarioAnswerInput) {
        scenarioAnswers[idx] = scenarioAnswerInput.value || "";
      }
      const resultBox = document.getElementById("scenario-modal-result");
      gradeScenarioQuestion(idx, scenarioSubmitBtn, resultBox);
    });
  }

  if (scenarioAnswerInput) {
    scenarioAnswerInput.addEventListener("input", (e) => {
      if (currentScenarioIndex != null) {
        scenarioAnswers[currentScenarioIndex] = e.target.value;
      }
    });
  }

  if (scenarioDontUnderstandBtn) {
    scenarioDontUnderstandBtn.addEventListener(
      "click",
      handleScenarioDontUnderstand
    );
  }

  if (scenarioNextBtn) {
  scenarioNextBtn.addEventListener("click", () => {
    if (currentScenarioIndex == null) return;
    generateScenarioQuestion(currentScenarioIndex, scenarioNextBtn, true);
  });
}


  if (scenarioQaBtn) {
    scenarioQaBtn.addEventListener("click", sendScenarioQaQuestion);
  }

  if (scenarioQaInput) {
    scenarioQaInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        sendScenarioQaQuestion();
      }
    });
  }
});











