"use strict";

/* =========================================================
   Expense tracker dashboard
   Talks to the Flask API in app/app.py. No chart libraries:
   the charts are drawn as inline SVG.
   ========================================================= */

const BUDGET_KEY = "expense-tracker-budget";
const DEFAULT_BUDGET = 5000;

const PALETTE = ["#0e6b5e", "#d69a00", "#c4523a", "#3e5cb8", "#8a5fa8", "#5fa34e", "#d2739b", "#5b6b7a"];

const CURRENCY = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
const COMPACT = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });

const $ = (selector) => document.querySelector(selector);

const state = {
  month: null,       // "YYYY-MM" being viewed
  budget: DEFAULT_BUDGET,
  category: null,    // category filter for the table
  editingId: null,   // id of the expense being edited, or null
  categories: [],
  summary: null,
  expenses: [],
};

/* ---------- small helpers ---------- */

const money = (n) => CURRENCY.format(n);
const pad = (n) => String(n).padStart(2, "0");

function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function currentMonth() {
  return todayISO().slice(0, 7);
}

function monthLabel(month) {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

function shortMonthLabel(month) {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

function dayLabel(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function colorFor(category) {
  const index = state.categories.indexOf(category);
  return PALETTE[(index < 0 ? 0 : index) % PALETTE.length];
}

function loadBudget() {
  try {
    const saved = Number(localStorage.getItem(BUDGET_KEY));
    if (saved > 0) return saved;
  } catch (e) { /* storage unavailable, use the default */ }
  return DEFAULT_BUDGET;
}

function saveBudget(value) {
  try { localStorage.setItem(BUDGET_KEY, String(value)); } catch (e) { /* ignore */ }
}

/* ---------- API ---------- */

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (e) {
    throw new Error("Can't reach the server. Start it with `python app/app.py`, then open http://127.0.0.1:5000/ in your browser.");
  }

  let data = null;
  try { data = await response.json(); } catch (e) { /* no JSON body */ }

  if (!response.ok) {
    throw new Error((data && data.error) || `Request failed (${response.status}).`);
  }
  return data;
}

function showBanner(message) {
  const banner = $("#banner");
  banner.textContent = message;
  banner.hidden = false;
}

function hideBanner() {
  $("#banner").hidden = true;
}

let toastTimer = null;
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

/* ---------- loading ---------- */

async function refresh() {
  const summaryParams = new URLSearchParams({ month: state.month, budget: state.budget });
  const expenseParams = new URLSearchParams({ month: state.month });
  if (state.category) expenseParams.set("category", state.category);

  try {
    const [categories, summary, expenses] = await Promise.all([
      api("/api/categories"),
      api(`/api/summary?${summaryParams}`),
      api(`/api/expenses?${expenseParams}`),
    ]);
    hideBanner();
    state.categories = categories.slice().sort((a, b) => a.localeCompare(b));
    state.summary = summary;
    state.expenses = expenses;
    render();
  } catch (err) {
    showBanner(err.message);
  }
}

/* ---------- rendering ---------- */

function render() {
  const s = state.summary;
  renderControls(s);
  renderHero(s);
  renderStats(s);
  renderDonut(s);
  renderMonthly(s);
  renderDaily(s);
  renderTable();
  $("#category-list").innerHTML = state.categories.map((c) => `<option value="${esc(c)}"></option>`).join("");
}

function renderControls(s) {
  const months = new Set(s.monthly_summary.map((m) => m.month));
  months.add(state.month);
  months.add(currentMonth());
  const sorted = [...months].sort().reverse();

  const select = $("#month");
  select.innerHTML = sorted
    .map((m) => `<option value="${m}">${esc(monthLabel(m))}</option>`)
    .join("");
  select.value = state.month;

  $("#budget").value = state.budget;
}

function renderHero(s) {
  const b = s.budget;
  const hero = $("#hero");
  hero.dataset.status = b.status;

  $("#hero-month").textContent = monthLabel(b.month);

  if (b.remaining >= 0) {
    $("#hero-amount").textContent = money(b.remaining);
    $("#hero-word").textContent = "left to spend";
  } else {
    $("#hero-amount").textContent = money(-b.remaining);
    $("#hero-word").textContent = "over budget";
  }

  $("#hero-sub").textContent =
    `${money(b.spent)} spent of your ${money(b.budget)} budget (${Math.round(b.percent_used)}% used).`;

  // Bar segments: one per category, sized against the budget (or the spend, if over budget)
  const scale = Math.max(b.budget, b.spent) || 1;
  $("#meter-bar").innerHTML = s.category_breakdown
    .map((c) => {
      const width = (c.total / scale) * 100;
      return `<span style="width:${width.toFixed(2)}%;background:${colorFor(c.category)}" title="${esc(c.category)}: ${esc(money(c.total))}"></span>`;
    })
    .join("");

  const marker = $("#meter-marker");
  if (b.spent > b.budget) {
    marker.style.left = `${((b.budget / scale) * 100).toFixed(2)}%`;
    marker.hidden = false;
  } else {
    marker.hidden = true;
  }

  $("#meter").setAttribute("aria-label", `${money(b.spent)} spent of a ${money(b.budget)} budget`);

  const notes = {
    ok: "You're on track for this month.",
    warning: "You've used more than 80% of this month's budget.",
    critical: "You're close to this month's limit.",
    exceeded: "You've gone past this month's budget.",
  };
  let note = notes[b.status] || "";

  // Daily pace, only for the month that's still in progress
  if (b.month === currentMonth() && b.remaining > 0) {
    const now = new Date();
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const daysLeft = daysInMonth - now.getDate() + 1;
    const perDay = Math.floor(b.remaining / daysLeft);
    note += ` That's about ${money(perDay)} a day for the next ${daysLeft} ${daysLeft === 1 ? "day" : "days"}.`;
  }
  $("#hero-note").textContent = note;
}

function renderStats(s) {
  const top = s.top_category;
  const day = s.highest_spending_day;
  const items = [
    ["Spent this month", money(s.total_spent), ""],
    ["Expenses", String(s.expense_count), ""],
    ["Average expense", money(s.average_expense), ""],
    ["Biggest category", top ? esc(top.category) : "None yet", top ? money(top.total) : ""],
    ["Biggest day", day ? esc(dayLabel(day.date)) : "None yet", day ? money(day.total) : ""],
  ];
  $("#stats").innerHTML = items
    .map(([label, value, sub]) => `<div><dt>${esc(label)}</dt><dd>${value}${sub ? `<small>${esc(sub)}</small>` : ""}</dd></div>`)
    .join("");
}

function renderDonut(s) {
  const data = s.category_breakdown;
  const total = s.total_spent;
  const R = 70;
  const C = 2 * Math.PI * R;

  let segments = "";
  if (data.length && total > 0) {
    let offset = 0;
    segments = data
      .map((c) => {
        const len = (c.total / total) * C;
        const seg = `<circle cx="90" cy="90" r="${R}" fill="none" stroke="${colorFor(c.category)}" stroke-width="26"
          stroke-dasharray="${len.toFixed(3)} ${(C - len).toFixed(3)}" stroke-dashoffset="${(-offset).toFixed(3)}"
          transform="rotate(-90 90 90)"><title>${esc(c.category)}: ${esc(money(c.total))} (${c.percentage}%)</title></circle>`;
        offset += len;
        return seg;
      })
      .join("");
  }

  $("#donut").innerHTML = `
    <svg viewBox="0 0 180 180" role="img" aria-label="Spending by category">
      <circle cx="90" cy="90" r="${R}" fill="none" stroke="var(--track)" stroke-width="26"></circle>
      ${segments}
      <text class="center-label" x="90" y="84" text-anchor="middle">Total</text>
      <text class="center-value" x="90" y="104" text-anchor="middle">${esc(money(total))}</text>
    </svg>`;

  const legend = $("#legend");
  if (!data.length) {
    legend.innerHTML = `<li class="empty">Nothing spent in ${esc(monthLabel(state.month))} yet.</li>`;
    return;
  }
  legend.innerHTML = data
    .map((c) => `
      <li>
        <button type="button" class="legend-row" data-category="${esc(c.category)}" aria-pressed="${state.category === c.category}">
          <span class="chip" style="background:${colorFor(c.category)}"></span>
          <span>${esc(c.category)}</span>
          <span class="legend-pct">${c.percentage}%</span>
          <span class="legend-amt">${esc(money(c.total))}</span>
        </button>
      </li>`)
    .join("");
}

function renderMonthly(s) {
  const el = $("#monthly-chart");
  const data = s.monthly_summary.slice(-12);
  if (!data.length) {
    el.innerHTML = `<p class="empty">Monthly totals will show up here after your first expense.</p>`;
    return;
  }

  const W = 600, H = 210, top = 24, bottom = 30, side = 6;
  const plotH = H - top - bottom;
  const budget = s.budget.budget;
  const max = Math.max(...data.map((d) => d.total), budget) * 1.1;
  const slot = (W - side * 2) / data.length;
  const barW = Math.min(56, slot * 0.6);
  const y = (v) => top + plotH - (v / max) * plotH;

  const bars = data
    .map((d, i) => {
      const x = side + slot * i + (slot - barW) / 2;
      const barY = y(d.total);
      const h = Math.max(top + plotH - barY, 1);
      const selected = d.month === state.month;
      const label = `${monthLabel(d.month)}: ${money(d.total)} across ${d.count} ${d.count === 1 ? "expense" : "expenses"}`;
      return `
        <g class="bar${selected ? " is-selected" : ""}" data-month="${d.month}" tabindex="0" role="button" aria-label="${esc(label)}">
          <title>${esc(label)}</title>
          <rect x="${x.toFixed(1)}" y="${barY.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" rx="4"></rect>
          <text class="value" x="${(x + barW / 2).toFixed(1)}" y="${(barY - 6).toFixed(1)}" text-anchor="middle">${esc(COMPACT.format(d.total))}</text>
          <text x="${(x + barW / 2).toFixed(1)}" y="${H - 10}" text-anchor="middle">${esc(shortMonthLabel(d.month))}</text>
        </g>`;
    })
    .join("");

  el.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" role="group" aria-label="Total spending for each month">
      <line class="axis" x1="0" x2="${W}" y1="${top + plotH}" y2="${top + plotH}"></line>
      <line class="budget-line" x1="0" x2="${W}" y1="${y(budget).toFixed(1)}" y2="${y(budget).toFixed(1)}"></line>
      ${bars}
    </svg>`;
}

function renderDaily(s) {
  const el = $("#daily-chart");
  if (!s.daily_spending.length) {
    el.innerHTML = `<p class="empty">No spending recorded in ${esc(monthLabel(state.month))}.</p>`;
    return;
  }

  const [year, month] = state.month.split("-").map(Number);
  const days = new Date(year, month, 0).getDate();
  const byDay = {};
  s.daily_spending.forEach((d) => { byDay[Number(d.date.slice(8, 10))] = d.total; });
  const topDay = s.highest_spending_day ? Number(s.highest_spending_day.date.slice(8, 10)) : null;

  const W = 600, H = 150, top = 12, bottom = 24, side = 6;
  const plotH = H - top - bottom;
  const max = Math.max(...Object.values(byDay), 1);
  const slot = (W - side * 2) / days;
  const barW = slot * 0.7;

  let bars = "";
  for (let d = 1; d <= days; d++) {
    const total = byDay[d] || 0;
    const x = side + slot * (d - 1) + (slot - barW) / 2;
    const h = total ? Math.max((total / max) * plotH, 2) : 0;
    const iso = `${state.month}-${pad(d)}`;
    if (total) {
      bars += `
        <g class="day${d === topDay ? " is-top" : ""}">
          <title>${esc(dayLabel(iso))}: ${esc(money(total))}</title>
          <rect x="${x.toFixed(1)}" y="${(top + plotH - h).toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" rx="2"></rect>
        </g>`;
    }
    if (d === 1 || d % 5 === 0) {
      bars += `<text x="${(x + barW / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${d}</text>`;
    }
  }

  el.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Spending for each day of ${esc(monthLabel(state.month))}">
      <line class="axis" x1="0" x2="${W}" y1="${top + plotH}" y2="${top + plotH}"></line>
      ${bars}
    </svg>`;
}

function renderTable() {
  $("#table-title").textContent = `Expenses in ${monthLabel(state.month)}`;

  const meta = $("#table-meta");
  const count = state.expenses.length;
  if (state.category) {
    meta.innerHTML = `Showing ${esc(state.category)} only. <button type="button" class="link-btn" id="clear-filter">Show all</button>`;
  } else {
    meta.textContent = `${count} ${count === 1 ? "expense" : "expenses"}`;
  }

  const body = $("#expense-rows");
  if (!count) {
    body.innerHTML = `<tr><td colspan="5" class="muted">No expenses here yet. Add one using the form.</td></tr>`;
    return;
  }

  body.innerHTML = state.expenses
    .map((e) => {
      const what = `${e.category} expense of ${money(e.amount)} on ${dayLabel(e.date)}`;
      return `
        <tr>
          <td class="date">${esc(dayLabel(e.date))}</td>
          <td${e.description ? "" : ' class="muted"'}>${e.description ? esc(e.description) : "No description"}</td>
          <td><span class="cat-cell"><span class="chip" style="background:${colorFor(e.category)}"></span>${esc(e.category)}</span></td>
          <td class="num">${esc(money(e.amount))}</td>
          <td class="actions">
            <button type="button" class="link-btn" data-action="edit" data-id="${e.id}" aria-label="Edit ${esc(what)}">Edit</button>
            <button type="button" class="link-btn danger" data-action="delete" data-id="${e.id}" aria-label="Delete ${esc(what)}">Delete</button>
          </td>
        </tr>`;
    })
    .join("");
}

/* ---------- form: add and edit ---------- */

const form = $("#expense-form");

function showFormError(message) {
  const el = $("#form-error");
  el.textContent = message;
  el.hidden = !message;
}

function resetForm() {
  state.editingId = null;
  form.reset();
  form.elements.date.value = todayISO();
  $("#form-title").textContent = "Add an expense";
  $("#form-submit").textContent = "Add expense";
  $("#form-cancel").hidden = true;
  showFormError("");
}

function startEdit(id) {
  const expense = state.expenses.find((e) => e.id === id);
  if (!expense) return;
  state.editingId = id;
  form.elements.amount.value = expense.amount;
  form.elements.date.value = expense.date;
  form.elements.category.value = expense.category;
  form.elements.description.value = expense.description || "";
  $("#form-title").textContent = "Edit expense";
  $("#form-submit").textContent = "Save changes";
  $("#form-cancel").hidden = false;
  showFormError("");
  form.scrollIntoView({ block: "nearest" });
  form.elements.amount.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showFormError("");

  const payload = {
    amount: form.elements.amount.value,
    date: form.elements.date.value,
    category: form.elements.category.value,
    description: form.elements.description.value,
  };

  const submit = $("#form-submit");
  submit.disabled = true;
  const editing = state.editingId;

  try {
    const result = editing
      ? await api(`/api/expenses/${editing}`, { method: "PUT", body: JSON.stringify(payload) })
      : await api("/api/expenses", { method: "POST", body: JSON.stringify(payload) });

    const saved = result.expense;
    toast(editing ? "Changes saved" : `Added ${money(saved.amount)} to ${saved.category}`);

    state.month = saved.date.slice(0, 7); // jump to the month the expense belongs to
    state.category = null;
    resetForm();
    await refresh();
    form.elements.amount.focus();
  } catch (err) {
    showFormError(err.message);
  } finally {
    submit.disabled = false;
  }
});

$("#form-cancel").addEventListener("click", resetForm);

/* ---------- other events ---------- */

$("#month").addEventListener("change", (event) => {
  state.month = event.target.value;
  state.category = null;
  resetForm();
  refresh();
});

$("#budget").addEventListener("change", (event) => {
  const value = Number(event.target.value);
  if (!(value > 0)) {
    event.target.value = state.budget;
    toast("Enter a budget above 0");
    return;
  }
  state.budget = value;
  saveBudget(value);
  refresh();
});

$("#legend").addEventListener("click", (event) => {
  const row = event.target.closest("[data-category]");
  if (!row) return;
  const category = row.dataset.category;
  state.category = state.category === category ? null : category;
  refresh();
});

function openMonth(node) {
  if (!node) return;
  state.month = node.dataset.month;
  state.category = null;
  resetForm();
  refresh();
}

$("#monthly-chart").addEventListener("click", (event) => openMonth(event.target.closest(".bar")));
$("#monthly-chart").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openMonth(event.target.closest(".bar"));
  }
});

$("#table-meta").addEventListener("click", (event) => {
  if (event.target.id === "clear-filter") {
    state.category = null;
    refresh();
  }
});

$("#expense-rows").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);

  if (button.dataset.action === "edit") {
    startEdit(id);
    return;
  }

  const expense = state.expenses.find((e) => e.id === id);
  if (!expense) return;
  const question = `Delete the ${money(expense.amount)} ${expense.category} expense from ${dayLabel(expense.date)}?`;
  if (!confirm(question)) return;

  try {
    await api(`/api/expenses/${id}`, { method: "DELETE" });
    toast("Expense deleted");
    if (state.editingId === id) resetForm();
    await refresh();
  } catch (err) {
    showBanner(err.message);
  }
});

/* ---------- start ---------- */

async function init() {
  state.budget = loadBudget();
  state.month = currentMonth();
  resetForm();

  // If this month has no expenses yet, open the latest month that does
  try {
    const first = await api(`/api/summary?month=${state.month}&budget=${state.budget}`);
    if (first.expense_count === 0 && first.monthly_summary.length) {
      state.month = first.monthly_summary[first.monthly_summary.length - 1].month;
    }
  } catch (err) {
    showBanner(err.message);
    return;
  }
  await refresh();
}

init();