function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value == null || value === "" ? "--" : String(value);
}

function verdictLabel(verdict) {
  if (verdict === "correct") return "Correct";
  if (verdict === "partial") return "Partially correct";
  if (verdict === "wrong") return "Incorrect";
  return "Unknown";
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!data.ok) throw new Error(data.msg || "Request failed.");
  return data;
}

async function loadProfile() {
  const data = await fetchJson("/api/profile");
  const user = data.user || {};
  const initial = (user.username || "U").slice(0, 1).toUpperCase();

  setText("profile-avatar", initial);
  setText("profile-username", user.username);
  setText("profile-email", user.email);
  setText("profile-info-username", user.username);
  setText("profile-info-email", user.email);
  setText("profile-info-id", user.public_user_id);
  setText("profile-info-rounds", data.total_rounds || 0);
}

async function loadRounds() {
  const data = await fetchJson("/api/profile/rounds");
  const rounds = data.rounds || [];
  const list = document.getElementById("round-list");
  const count = document.getElementById("history-count");
  if (count) count.textContent = `${rounds.length} round${rounds.length === 1 ? "" : "s"}`;
  if (!list) return;

  list.innerHTML = "";
  if (!rounds.length) {
    list.innerHTML = "<div class='profile-empty'>No completed question history yet.</div>";
    return;
  }

  rounds.forEach((round) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "round-item";
    item.innerHTML = `
      <div>
        <strong>Round #${round.id}</strong>
        <span>${round.created_at || ""}</span>
      </div>
      <div class="round-item-meta">
        <span>${round.total_questions || 0} questions</span>
        <span>${round.round_score ?? "--"} points</span>
        <span>${round.has_analysis ? "Analysis saved" : "No analysis"}</span>
      </div>
    `;
    item.addEventListener("click", () => loadRoundDetail(round.id));
    list.appendChild(item);
  });
}

async function loadRoundDetail(roundId) {
  const data = await fetchJson(`/api/profile/rounds/${roundId}`);
  const detail = document.getElementById("round-detail");
  const title = document.getElementById("round-detail-title");
  const meta = document.getElementById("round-detail-meta");
  const analysis = document.getElementById("round-analysis");
  const answers = document.getElementById("round-answers");
  const round = data.round || {};

  if (title) title.textContent = `Round #${round.id}`;
  if (meta) {
    meta.textContent = `${round.created_at || ""} | Score: ${round.round_score ?? "--"} | Correct: ${round.correct_count ?? 0}, Partial: ${round.partial_count ?? 0}, Wrong: ${round.wrong_count ?? 0}`;
  }
  if (analysis) {
    analysis.innerHTML = `
      <h3>Round Analysis</h3>
      <div>${round.analysis ? escapeHtml(round.analysis) : "No saved analysis for this round yet."}</div>
    `;
  }
  if (answers) {
    answers.innerHTML = "";
    (data.answers || []).forEach((item, idx) => {
      const card = document.createElement("article");
      card.className = "round-answer-card";
      card.innerHTML = `
        <div class="round-answer-header">
          <strong>Question ${idx + 1}</strong>
          <span class="verdict-pill verdict-${item.verdict || "unknown"}">${verdictLabel(item.verdict)}</span>
        </div>
        <div class="round-question">${escapeHtml(item.question || "")}</div>
        <div class="round-answer-block"><span>Your answer</span>${escapeHtml(item.student_answer || "(empty)")}</div>
        <div class="round-answer-block"><span>Feedback</span>${escapeHtml(item.evaluation || "(no feedback)")}</div>
      `;
      answers.appendChild(card);
    });
  }
  if (detail) {
    detail.classList.remove("hidden");
    detail.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
    .replaceAll("\n", "<br>");
}

function bindPasswordForm() {
  const toggle = document.getElementById("change-password-toggle");
  const form = document.getElementById("password-form");
  const message = document.getElementById("password-message");

  if (toggle && form) {
    toggle.addEventListener("click", () => form.classList.toggle("hidden"));
  }

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const btn = form.querySelector("button[type='submit']");
      if (btn) btn.disabled = true;
      if (message) message.textContent = "";
      try {
        await fetchJson("/api/profile/change_password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            current_password: document.getElementById("current-password").value,
            new_password: document.getElementById("new-password").value,
            confirm_password: document.getElementById("confirm-password").value,
          }),
        });
        form.reset();
        if (message) {
          message.textContent = "Password updated successfully.";
          message.classList.add("success");
        }
      } catch (err) {
        if (message) {
          message.textContent = err.message;
          message.classList.remove("success");
        }
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  bindPasswordForm();
  const closeBtn = document.getElementById("close-round-detail");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      const detail = document.getElementById("round-detail");
      if (detail) detail.classList.add("hidden");
    });
  }

  try {
    await loadProfile();
    await loadRounds();
  } catch (err) {
    if (err.message.includes("sign in")) {
      window.location.href = "/";
    } else {
      console.error(err);
    }
  }
});
