/* Profile workspace: existing account/history APIs, shared language and theme. */
const $ = id => document.getElementById(id);
let language = localStorage.getItem("ui_lang") === "en" ? "en" : "zh";
let currentView = "info";
let savedRounds = [];
let detailData = null;
let detailRequest = 0;
let historyError = false;
const words = {
  center:["个人中心","Personal center"], info:["个人资料","Profile"], history:["学习记录","Learning history"], security:["账号安全","Account security"],
  back:["返回题库","Back to library"], logout:["退出登录","Sign out"], basic:["基本信息","Basic information"],
  username:["用户名","Username"], email:["电子邮箱","Email"], userId:["用户 ID","User ID"], rounds:["完成练习轮次","Completed practice rounds"],
  changePassword:["修改密码","Change password"], review:["回顾学习记录","Review your learning"], reviewHint:["查看历次作答、批改结果与学习反馈。","Review your answers, grading results and learning feedback."],
  completed:["已完成的练习","Completed practice"], retry:["重新加载","Retry"], backHistory:["返回记录","Back to history"],
  passwordHint:["新密码应为 8–128 个字符，建议使用不重复的字母、数字与符号组合。","Use 8–128 characters. A unique mix of letters, numbers and symbols is recommended."],
  currentPassword:["当前密码","Current password"], newPassword:["新密码","New password"], confirmPassword:["确认新密码","Confirm new password"],
  savePassword:["更新密码","Update password"], clear:["清空","Clear"], saved:["密码修改成功。","Password updated successfully."],
  infoSubtitle:["查看账号信息，回顾你的学习历程。","Your account information and learning journey."],
  historySubtitle:["每一次练习，都留下可以回顾的进步。","Return to your answers and feedback from completed practice."],
  securitySubtitle:["管理登录密码，保护你的账号。","Manage your password and protect your account."],
  loading:["正在加载，请稍候…","Loading, please wait…"], empty:["还没有已完成的练习记录。完成一轮练习后，可以在这里回顾作答和反馈。","No completed practice yet. Finish a round to review your answers and feedback here."],
  analysis:["本轮学习反馈","Round analysis"], noAnalysis:["这一轮暂未保存学习反馈。","No analysis saved for this round."],
  yourAnswer:["你的答案","Your answer"], feedback:["批改反馈","Feedback"], noAnswer:["未填写","No answer"], noFeedback:["暂无反馈","No feedback"],
  correct:["正确","Correct"], partial:["部分正确","Partially correct"], wrong:["错误","Incorrect"], unknown:["未判定","Unknown"],
  mismatch:["两次输入的新密码不一致。","The new passwords do not match."],
  historyFailed:["学习记录加载失败，请重试。","Could not load learning history. Please retry."],
  requestFailed:["请求失败，请重试。","Request failed. Please retry."]
};
const t = key => words[key]?.[language === "zh" ? 0 : 1] || key;
function setText(id, value) { $(id).textContent = value == null || value === "" ? "--" : String(value); }
function node(tag, className, content) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (content != null) el.textContent = String(content);
  return el;
}
function pageMessage(message = "", loading = false) {
  $("profile-page-message").textContent = message;
  $("profile-page-message").hidden = !message;
  $("profile-page-message").classList.toggle("is-loading", loading);
}
async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok || !data.ok) {
    const error = new Error(data.msg || t("requestFailed"));
    error.status = res.status;
    throw error;
  }
  return data;
}
function applyLanguage() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = t("center") + (language === "zh" ? " - 智练 WizPractice" : " - WizPractice");
  document.querySelectorAll("[data-profile-i18n]").forEach(el => { el.textContent = t(el.dataset.profileI18n); });
  document.querySelector(".profile-navigation").setAttribute("aria-label", t("center"));
  $("profile-lang-btn").textContent = language === "zh" ? "EN" : "中文";
  $("profile-section-title").textContent = t(currentView);
  $("profile-section-subtitle").textContent = t(currentView + "Subtitle");
  if (savedRounds.length || !historyError) renderRounds();
  if (detailData) renderDetail(detailData);
  applyTheme(document.body.classList.contains("dark-theme"));
}
function applyTheme(dark) {
  document.body.classList.toggle("dark-theme", dark);
  $("profile-theme-btn").textContent = dark ? "☀" : "☾";
  $("profile-theme-btn").setAttribute("aria-label", language === "zh" ? (dark ? "切换为浅色模式" : "切换为深色模式") : (dark ? "Use light theme" : "Use dark theme"));
}
function showView(view, focus = true) {
  if (!["info", "history", "security"].includes(view)) view = "info";
  if (currentView === "security" && view !== "security") {
    $("password-form").reset();
    $("password-message").textContent = "";
  }
  if (view !== "history") {
    detailRequest++;
    pageMessage();
  }
  currentView = view;
  document.querySelectorAll(".profile-view").forEach(el => { el.hidden = el.id !== "profile-" + view + "-view"; });
  document.querySelectorAll(".profile-navigation [data-profile-view]").forEach(button => {
    const active = button.dataset.profileView === view;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  $("profile-section-title").textContent = t(view);
  $("profile-section-subtitle").textContent = t(view + "Subtitle");
  if (view === "history" && historyError) pageMessage(t("historyFailed"));
  window.history.replaceState(null, "", "#" + view);
  if (focus) $("profile-section-title").focus({ preventScroll:true });
}
async function loadProfile() {
  const data = await fetchJson("/api/profile");
  const user = data.user || {};
  setText("profile-avatar", (user.username || "U").slice(0, 1).toUpperCase());
  ["profile-username","profile-info-username"].forEach(id => setText(id, user.username));
  ["profile-email","profile-info-email"].forEach(id => setText(id, user.email));
  setText("profile-info-id", user.public_user_id);
  setText("profile-info-rounds", data.total_rounds || 0);
}
function renderRounds() {
  $("history-count").textContent = language === "zh" ? savedRounds.length + " 轮练习" : savedRounds.length + " rounds";
  $("profile-nav-rounds").textContent = savedRounds.length;
  $("round-list").replaceChildren();
  if (!savedRounds.length) {
    $("round-list").appendChild(node("div", "profile-empty", t("empty")));
    return;
  }
  savedRounds.forEach(round => {
    const item = node("button", "round-item");
    item.type = "button";
    const heading = node("div");
    heading.append(node("strong", "", (language === "zh" ? "练习 #" : "Round #") + round.id), node("span", "", round.created_at || ""));
    const meta = node("div", "round-item-meta");
    [round.total_questions + (language === "zh" ? " 道题" : " questions"), (round.round_score ?? "--") + (language === "zh" ? " 分" : " points"),
      language === "zh" ? (round.has_analysis ? "已有学习反馈" : "暂无学习反馈") : (round.has_analysis ? "Analysis saved" : "No analysis")].forEach(label => meta.appendChild(node("span", "", label)));
    item.append(heading, meta);
    item.addEventListener("click", () => loadRoundDetail(round.id));
    $("round-list").appendChild(item);
  });
}
async function loadRounds() {
  $("retry-history-btn").disabled = true;
  try {
    const data = await fetchJson("/api/profile/rounds");
    savedRounds = data.rounds || [];
    historyError = false;
    $("retry-history-btn").hidden = true;
    renderRounds();
    if (currentView === "history") pageMessage();
  } catch (error) {
    if (error.status === 401) { window.location.href = "/"; return; }
    historyError = true;
    $("round-list").replaceChildren(node("div", "profile-empty", t("historyFailed")));
    $("history-count").textContent = "--";
    $("retry-history-btn").hidden = false;
    if (currentView === "history") pageMessage(t("historyFailed"));
  } finally { $("retry-history-btn").disabled = false; }
}
function renderDetail(data) {
  const round = data.round || {};
  setText("round-detail-title", (language === "zh" ? "练习 #" : "Round #") + round.id);
  $("round-detail-meta").textContent = round.created_at + " · " + (round.round_score ?? "--") + (language === "zh" ? " 分" : " points") + " · "
    + t("correct") + " " + (round.correct_count || 0) + " / " + t("partial") + " " + (round.partial_count || 0) + " / " + t("wrong") + " " + (round.wrong_count || 0);
  $("round-analysis").replaceChildren(node("h3", "", t("analysis")), node("div", "", round.analysis || t("noAnalysis")));
  $("round-answers").replaceChildren();
  (data.answers || []).forEach((answer, index) => {
    const card = node("article", "round-answer-card");
    const header = node("div", "round-answer-header");
    const verdict = ["correct","partial","wrong"].includes(answer.verdict) ? answer.verdict : "unknown";
    header.append(node("strong", "", (language === "zh" ? "第 " + (index + 1) + " 题" : "Question " + (index + 1))), node("span", "verdict-pill verdict-" + verdict, t(verdict)));
    const block = (label, content) => { const el = node("div", "round-answer-block"); el.append(node("span", "", label), document.createTextNode(content)); return el; };
    card.append(header, node("div", "round-question", answer.question || ""), block(t("yourAnswer"), answer.student_answer || t("noAnswer")), block(t("feedback"), answer.evaluation || t("noFeedback")));
    $("round-answers").appendChild(card);
  });
  window.mathUI.render($("round-analysis"));
  window.mathUI.render($("round-answers"));
}
async function loadRoundDetail(id) {
  const token = ++detailRequest;
  pageMessage(t("loading"), true);
  try {
    const data = await fetchJson("/api/profile/rounds/" + encodeURIComponent(id));
    if (token !== detailRequest || currentView !== "history") return;
    detailData = data;
    renderDetail(data);
    $("profile-history-list-card").hidden = true;
    $("round-detail").hidden = false;
    pageMessage();
    $("close-round-detail").focus({ preventScroll:true });
  } catch (error) {
    if (token === detailRequest && currentView === "history") pageMessage(error.message);
  }
}
function bindPasswordForm() {
  $("change-password-toggle").addEventListener("click", () => { showView("security"); $("current-password").focus(); });
  $("clear-password-btn").addEventListener("click", () => { $("password-form").reset(); $("password-message").textContent = ""; });
  $("password-form").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget, submit = form.querySelector("[type=submit]");
    const message = $("password-message");
    message.classList.remove("success");
    message.textContent = "";
    if ($("new-password").value !== $("confirm-password").value) { message.textContent = t("mismatch"); return; }
    submit.disabled = true;
    $("clear-password-btn").disabled = true;
    try {
      await fetchJson("/api/profile/change_password", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({
        current_password:$("current-password").value, new_password:$("new-password").value, confirm_password:$("confirm-password").value
      }) });
      form.reset();
      message.textContent = t("saved");
      message.classList.add("success");
    } catch (error) { message.textContent = error.message; }
    finally { submit.disabled = false; $("clear-password-btn").disabled = false; }
  });
}
document.addEventListener("DOMContentLoaded", async () => {
  applyTheme(localStorage.getItem("ui_theme") === "dark");
  applyLanguage();
  showView(window.location.hash.slice(1), false);
  window.addEventListener("hashchange", () => showView(window.location.hash.slice(1), false));
  document.querySelectorAll("[data-profile-view]").forEach(button => button.addEventListener("click", () => showView(button.dataset.profileView)));
  $("profile-lang-btn").addEventListener("click", () => { language = language === "zh" ? "en" : "zh"; localStorage.setItem("ui_lang", language); applyLanguage(); });
  $("profile-theme-btn").addEventListener("click", () => { const dark = !document.body.classList.contains("dark-theme"); localStorage.setItem("ui_theme", dark ? "dark" : "light"); applyTheme(dark); });
  $("profile-logout-btn").addEventListener("click", async () => {
    $("profile-logout-btn").disabled = true;
    try { await fetchJson("/api/auth/logout", { method:"POST" }); window.location.href = "/"; }
    catch (error) { pageMessage(error.message); $("profile-logout-btn").disabled = false; }
  });
  $("close-round-detail").addEventListener("click", () => {
    detailRequest++;
    $("round-detail").hidden = true;
    $("profile-history-list-card").hidden = false;
    detailData = null;
    $("round-list").querySelector("button")?.focus({ preventScroll:true });
  });
  $("retry-history-btn").addEventListener("click", loadRounds);
  bindPasswordForm();
  const [profileResult] = await Promise.allSettled([loadProfile(), loadRounds()]);
  if (profileResult.status === "rejected") {
    if (profileResult.reason.status === 401) window.location.href = "/";
    else pageMessage(profileResult.reason.message);
  }
});
