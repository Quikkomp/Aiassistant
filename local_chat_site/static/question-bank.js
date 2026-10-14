/* Saved question library and the create/practice workspace. Uses the existing grader. */
(() => {
  const $ = id => document.getElementById(id);
  let banks = [];
  let activeBank = null;
  let timer;
  let saveChain = Promise.resolve();
  let resetEpoch = 0;
  let viewAnimation;
  function revealWorkspace(id) {
    viewAnimation?.cancel();
    const view = $(id);
    // Animate only the visible content; navigation and inputs stay usable immediately.
    if (!view?.animate || !view.getClientRects().length || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    viewAnimation = view.animate([
      { opacity: 0.55, transform: "translateY(3px)" },
      { opacity: 1, transform: "translateY(0)" },
    ], { duration: 180, easing: "cubic-bezier(.22,.7,.3,1)" });
    viewAnimation.id = "workspace-transition";
  }
  const zh = () => currentLang === "zh";
  const words = {
    library: ["题库", "Question library"], practice: ["练习", "Practice"], profile: ["个人中心", "Profile"],
    capacityHelp: ["最多保存 10 组题目，删除旧题组可释放位置。", "Save up to 10 question sets. Delete an old set to free a slot."],
    librarySubtitle: ["把每一次灵感，变成可以反复练习的题目。", "Turn your ideas into questions you can come back to."],
    create: ["创建题库", "Create question set"], createCaption: ["从资料或想法开始", "Start with materials or an idea"],
    emptyNote: ["你的题库从这里开始。创建一组题目，随时回来继续练习。", "Your library starts here. Create a set and return whenever you want to practise."],
    back: ["← 返回题库", "← Back to library"], scoreHistory: ["练习成绩记录", "Practice scores"],
    aiCreate: ["AI 智能创建", "Create with AI"], creatorTitle: ["AI 智能创建题库", "Create your next question set"],
    creatorSubtitle: ["告诉我们你想练什么，让学习从一个想法开始。", "Tell us what you want to practise. Start with an idea."],
    bankName: ["题库名称（选填）", "Question set name (optional)"], requirements: ["出题要求", "Question requirements"],
    import: ["导入文档", "Import documents"], settings: ["详细设置", "Detailed settings"],
    settingsHint: ["题型、数量、难度与试卷风格", "Type, count, difficulty and paper style"],
    priorityHint: ["文字中的具体要求优先；未说明的项目使用下方设置。", "Your written requirements take priority. These settings supply any unspecified values."],
    tryPrompt: ["试试这样描述", "Try a prompt"],
    promptBasics: ["基础概念 · 5 道填空", "Basics · 5 blanks"],
    promptExam: ["考前复习 · 10 道混合题", "Review · 10 mixed"],
    promptChallenge: ["深入理解 · 5 道简答", "Analysis · 5 answers"],
    creatorFootnote: ["生成后自动保存到个人题库，可随时继续作答。", "Automatically saved to your personal library, ready to practise anytime."],
    generatingTitle: ["正在生成题目", "Generating your questions"],
    generatingHint: ["请稍候，完成后会自动保存到题库。", "Please wait. Your question set will be saved automatically."],
  };
  const text = key => words[key]?.[zh() ? 0 : 1] || key;
  const say = (message, error = false, where = "creator-message") => {
    const node = $(where);
    node.textContent = message;
    node.classList.toggle("is-error", error);
  };
  async function api(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.msg || (zh() ? "请求失败，请重试。" : "Request failed. Please retry."));
    return data;
  }
  function renderLibrary() {
    const name = $("account-name").textContent.trim();
    $("bank-profile-name").textContent = name;
    $("bank-profile-avatar").textContent = (name || "U").slice(0, 1).toUpperCase();
    document.querySelector(".bank-profile-link").setAttribute("aria-label", text("profile"));
    $("bank-grid").querySelectorAll(".saved-bank-tile").forEach(el => el.remove());
    const full = banks.length >= 10;
    const nearFull = banks.length === 9;
    const capacity = $("bank-capacity");
    capacity.textContent = zh() ? `已保存 ${banks.length} / 10 组` : `${banks.length} / 10 sets saved`;
    capacity.classList.toggle("is-near-full", nearFull);
    capacity.classList.toggle("is-full", full);
    const warning = $("bank-capacity-warning");
    warning.hidden = !nearFull && !full;
    warning.classList.toggle("is-full", full);
    warning.textContent = full ? (zh() ? "题库已满，请删除旧题组后再创建。" : "Library full. Delete an old set before creating another.")
      : nearFull ? (zh() ? "还可创建 1 组题目。" : "You can create 1 more question set.") : "";
    $("creator-capacity-hint").classList.toggle("is-near-full", nearFull || full);
    $("creator-capacity-hint").textContent = full ? warning.textContent : nearFull
      ? (zh() ? "已保存 9 / 10 组，这是最后一个可用位置。" : "9 / 10 sets saved. This is your last available slot.")
      : (zh() ? `已保存 ${banks.length} / 10 组 · 生成后自动入库` : `${banks.length} / 10 sets saved · New sets save automatically`);
    $("sidebar-bank-count").textContent = banks.length;
    $("bank-empty-note").hidden = banks.length > 0;
    banks.forEach((bank, index) => {
      const tile = document.createElement("div");
      tile.className = "bank-tile saved-bank-tile";
      const open = document.createElement("button");
      open.type = "button";
      open.className = "bank-open-btn";
      open.style.setProperty("--book-color", ["#a7c990", "#b0c6e7", "#d9b4a8", "#c4b3dc"][index % 4]);
      const cover = document.createElement("span");
      cover.className = "bank-book-cover";
      const motif = document.createElement("span"); motif.className = "book-motif";
      const count = document.createElement("span"); count.className = "book-question-count";
      count.textContent = `${bank.questions.length} ${zh() ? "题" : "questions"}`;
      cover.append(motif, count);
      const title = document.createElement("strong"); title.textContent = bank.title;
      const caption = document.createElement("small");
      const answered = (bank.progress.answeredFlags || []).filter(Boolean).length;
      caption.textContent = `${answered} / ${bank.questions.length} ${zh() ? "已完成" : "completed"}`;
      open.append(cover, title, caption);
      open.title = `${bank.title} · ${new Date(bank.created_at).toLocaleDateString()}`;
      open.addEventListener("click", () => openBank(bank));
      const remove = document.createElement("button");
      remove.type = "button"; remove.className = "bank-delete-btn"; remove.textContent = "×";
      remove.setAttribute("aria-label", (zh() ? "删除题组：" : "Delete set: ") + bank.title);
      remove.addEventListener("click", async () => {
        if (!confirm(zh() ? `删除「${bank.title}」？该题组和作答记录将被移除。` : `Delete “${bank.title}” and its saved answers?`)) return;
        try {
          await api(`/api/question_sets/${bank.id}`, { method: "DELETE" });
          banks = banks.filter(item => item.id !== bank.id);
          if (activeBank?.id === bank.id) activeBank = null;
          renderLibrary();
          say(zh() ? "题组已删除。" : "Question set deleted.", false, "bank-page-message");
        } catch (err) { say(err.message, true, "bank-page-message"); }
      });
      tile.append(open, remove); $("bank-grid").appendChild(tile);
    });
    $("create-bank-btn").classList.toggle("at-capacity", full);
    $("create-bank-btn").title = full ? warning.textContent : "";
    updateGenerateAvailability();
  }
  async function loadLibrary() {
    const epoch = resetEpoch;
    try {
      const data = await api("/api/question_sets");
      if (epoch !== resetEpoch) return;
      banks = data.banks; renderLibrary();
    } catch (err) { if (epoch === resetEpoch) say(err.message, true, "bank-page-message"); }
  }
  function showLibrary() {
    window.groupUI?.leave();
    window.examUI?.leave();
    scheduleSave(true);
    $("bank-library-view").hidden = false;
    $("bank-practice-view").hidden = true;
    $("nav-library").classList.add("active"); $("nav-library").setAttribute("aria-current", "page");
    $("nav-practice").classList.remove("active"); $("nav-practice").removeAttribute("aria-current");
    renderLibrary();
    revealWorkspace("bank-library-view");
  }
  function restoreMaterialSelection() {
    if (!activeBank || $("create-bank-dialog").open) return;
    const selected = activeBank.settings.selected_docs || [];
    document.querySelectorAll(".material-checkbox").forEach(cb => { cb.checked = selected.includes(cb.value); });
  }
  async function openBank(bank) {
    window.groupUI?.leave();
    window.examUI?.leave();
    scheduleSave(true);
    try { await saveChain; } catch (_) {
      say(zh() ? "上一题组的作答尚未保存，暂时无法切换，请重试。" : "Your previous answers have not saved. Retry before switching sets.", true, "bank-page-message");
      return;
    }
    activeBank = null;
    activeQuestionType = bank.settings.question_type?.includes(",") ? "mixed" : (bank.settings.question_type || "fill_blank");
    setQuestions(bank.reply);
    // Use the server's canonical split, shared by all browsers.
    questionList = bank.questions.slice();
    const saved = bank.progress;
    const array = (key, defaultValue) => questionList.map((_, i) => saved[key]?.[i] ?? defaultValue);
    questionAnswers = array("questionAnswers", ""); questionEvaluations = array("questionEvaluations", "");
    answeredFlags = array("answeredFlags", false); questionExplainText = array("questionExplainText", "");
    questionExplainStage = array("questionExplainStage", 0);
    scenarioQuestionTexts = array("scenarioQuestionTexts", ""); scenarioAnswers = array("scenarioAnswers", "");
    scenarioEvaluations = array("scenarioEvaluations", "");
    scenarioExplainStage = array("scenarioExplainStage", 0); scenarioExplainText = array("scenarioExplainText", "");
    qaHistory = []; scenarioQaHistory = []; currentScenarioIndex = null; chatHistory = [];
    currentQuestionIndex = Math.min(Math.max(Number(saved.currentQuestionIndex) || 0, 0), questionList.length - 1);
    currentRoundId = saved.currentRoundId || null; hasShownRoundFeedback = Boolean(saved.hasShownRoundFeedback);
    showCompletionOverview = false;
    wrongQuestions = buildFullRoundItems().filter(item => item.verdict === "wrong").map(item => ({ ...item, feedback: item.evaluation }));
    activeBank = bank;
    restoreMaterialSelection();
    $("active-bank-title").textContent = bank.title;
    $("exam-feedback").textContent = saved.examFeedback || t("feedback_default");
    $("bank-library-view").hidden = true; $("bank-practice-view").hidden = false;
    $("nav-library").classList.remove("active"); $("nav-library").removeAttribute("aria-current");
    $("nav-practice").classList.add("active"); $("nav-practice").setAttribute("aria-current", "page");
    renderQuestionCard(); renderScoreChart();
    revealWorkspace("bank-practice-view");
    $("bank-save-status").textContent = zh() ? "作答自动保存" : "Answers save automatically";
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }
  function snapshot() {
    return JSON.parse(JSON.stringify({ questionAnswers, questionEvaluations, answeredFlags, currentQuestionIndex,
      questionExplainText, questionExplainStage, scenarioQuestionTexts, scenarioAnswers, scenarioEvaluations,
      scenarioExplainStage, scenarioExplainText, currentRoundId, hasShownRoundFeedback,
      examFeedback: $("exam-feedback").textContent }));
  }
  function scheduleSave(immediate = false) {
    clearTimeout(timer);
    if (!activeBank) return;
    const bank = activeBank;
    const progress = snapshot();
    bank.progress = progress;
    const epoch = resetEpoch;
    const save = () => {
      saveChain = saveChain.catch(() => {}).then(async () => {
        if (epoch !== resetEpoch) return;
        $("bank-save-status").textContent = zh() ? "正在保存…" : "Saving…";
        try {
          const data = await api(`/api/question_sets/${bank.id}/progress`, {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ progress, version: bank.version }),
          });
          bank.version = data.version;
          if (epoch === resetEpoch) $("bank-save-status").textContent = zh() ? "已保存" : "Saved";
        } catch (err) {
          if (epoch === resetEpoch) $("bank-save-status").textContent = (zh() ? "保存失败：" : "Save failed: ") + err.message;
          throw err;
        }
      });
      // Preserve the rejected chain for the next save while preventing unhandled rejections.
      saveChain.catch(() => {});
    };
    if (immediate) save(); else timer = setTimeout(save, 650);
  }
  function renderProgress() {
    if (!activeBank) return;
    const done = answeredFlags.filter(Boolean).length;
    $("active-bank-meta").textContent = zh()
      ? `共 ${questionList.length} 题 · 已完成 ${done} 题`
      : `${questionList.length} questions · ${done} completed`;
    scheduleSave();
  }
  function updateGenerateAvailability() {
    const prompt = $("user-input").value.trim();
    const selected = document.querySelectorAll(".material-checkbox:checked").length;
    const inputFiles = $("file-input").files?.length || 0;
    $("creator-source-summary").textContent = selected
      ? (zh() ? `${selected} 份资料` : `${selected} materials`)
      : (inputFiles ? (zh() ? "资料上传中…" : "Uploading…") : "");
    $("send-btn").disabled = ui.busy || banks.length >= 10 || (!prompt && !selected) || (selected > 0 && !kbReady);
    if (!ui.busy) $("send-btn").textContent = zh() ? "生成题库" : "Generate set";
  }
  function translate() {
    document.querySelectorAll("[data-bank-i18n]").forEach(el => { el.textContent = text(el.dataset.bankI18n); });
    $("user-input").placeholder = zh()
      ? "在这里输入出题要求，或粘贴学习内容。例如：根据第三讲生成 10 道中等难度选择题，重点考查基本概念和实际应用。"
      : "Describe your requirements or paste study text. For example: create 10 medium-difficulty multiple-choice questions from Lecture 3, focusing on core concepts and applications.";
    $("bank-title-input").placeholder = zh() ? "例如：第三讲 · 考前练习" : "e.g. Lecture 3 · Exam practice";
    $("close-creator-btn").setAttribute("aria-label", zh() ? "关闭创建窗口" : "Close creator");
    const hints = document.querySelectorAll(".hint");
    if (hints[1]) hints[1].textContent = zh() ? "上传模拟卷，学习其题型顺序和措辞风格。模板中的知识不作为出题来源。" : "Upload a model paper to follow its question sequence and wording. Template knowledge is not used as question content.";
    renderLibrary(); updateGenerateAvailability(); renderProgress();
  }
  function openCreator() {
    if (banks.length >= 10) return say(zh() ? "题库已满（10 组），请先删除一组后再创建。" : "Your library is full (10 sets). Delete a set before creating another.", true, "bank-page-message");
    const dialog = $("create-bank-dialog");
    if (dialog.open) return;
    say(""); dialog.showModal();
    updateGenerateAvailability(); $("user-input").focus();
  }
  const ui = window.bankUI = {
    busy: false, message: say, translate, renderProgress, scheduleSave, restoreMaterialSelection, updateGenerateAvailability,
    setBusy(value) {
      this.busy = value;
      $("close-creator-btn").disabled = value;
      $("create-bank-dialog").classList.toggle("is-generating", value);
      $("create-bank-dialog").setAttribute("aria-busy", String(value));
      $("creator-dialog-scroll").inert = value;
      $("creator-generation-overlay").hidden = !value;
      if (value) $("creator-generation-overlay").focus({ preventScroll:true });
      else if ($("create-bank-dialog").open) $("user-input").focus({ preventScroll:true });
    },
    async created(bank) {
      banks.unshift(bank);
      $("create-bank-dialog").close();
      showLibrary();
      say(zh() ? `「${bank.title}」已保存，点击题组开始练习。` : `“${bank.title}” saved. Open the set to start practising.`, false, "bank-page-message");
      const tile = $("bank-grid").querySelector(".saved-bank-tile");
      tile?.classList.add("just-created"); tile?.querySelector("button")?.focus();
    },
    reset() {
      window.groupUI?.reset();
      window.examUI?.reset();
      resetEpoch += 1; clearTimeout(timer); activeBank = null; banks = [];
      this.setBusy(false);
      $("create-bank-dialog").close(); showLibrary();
      say("", false, "bank-page-message");
      $("user-input").value = ""; $("bank-title-input").value = "";
      loadLibrary();
    },
  };
  document.addEventListener("DOMContentLoaded", () => {
    $("create-bank-btn").addEventListener("click", openCreator);
    $("nav-library").addEventListener("click", showLibrary);
    $("back-to-bank-btn").addEventListener("click", showLibrary);
    $("nav-practice").addEventListener("click", () => {
      if (activeBank) openBank(activeBank);
      else if (banks.length) openBank(banks[0]);
      else { showLibrary(); say(zh() ? "先创建一组题目，再开始练习。" : "Create a question set to start practising.", false, "bank-page-message"); }
    });
    $("close-creator-btn").addEventListener("click", () => { if (!ui.busy) $("create-bank-dialog").close(); });
    $("create-bank-dialog").addEventListener("cancel", event => { if (ui.busy) event.preventDefault(); });
    $("create-bank-dialog").addEventListener("close", restoreMaterialSelection);
    $("import-materials-btn").addEventListener("click", () => $("file-input").click());
    $("file-input").addEventListener("change", async () => {
      if (!$("file-input").files.length) return;
      kbReady = false; updateGenerateAvailability();
      await uploadFiles(); updateGenerateAvailability();
    });
    $("user-input").addEventListener("input", updateGenerateAvailability);
    $("create-bank-dialog").addEventListener("change", updateGenerateAvailability);
    $("bank-practice-view").addEventListener("input", () => scheduleSave());
    $("bank-practice-view").addEventListener("click", () => queueMicrotask(() => scheduleSave()));
    document.addEventListener("visibilitychange", () => { if (document.hidden) scheduleSave(true); });
    document.querySelectorAll("[data-prompt-example]").forEach(button => {
      button.addEventListener("click", () => {
        const prompts = {
          basics: ["根据所选资料生成 5 道基础概念填空题，难度偏低。", "Create 5 easy fill-in-the-blank questions about core concepts in the selected materials."],
          exam: ["根据所选资料生成 10 道中等难度的考前复习题，包含选择、填空和简答。", "Create 10 medium exam-review questions from the selected materials, mixing multiple choice, fill-in-the-blank and short answer."],
          challenge: ["根据所选资料生成 5 道高难度简答题，考查比较、分析与实际应用。", "Create 5 challenging short-answer questions about comparison, analysis and application using the selected materials."],
        };
        $("user-input").value = prompts[button.dataset.promptExample][zh() ? 0 : 1];
        updateGenerateAvailability(); $("user-input").focus();
      });
    });
    translate(); loadLibrary();
    revealWorkspace("bank-library-view");
  });
})();
