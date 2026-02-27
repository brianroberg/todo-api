from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def serve_dashboard():
    """Serve read-only GTD dashboard as a single HTML page."""
    return HTMLResponse(content=HTML_CONTENT)


HTML_CONTENT = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GTD Dashboard</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --blue: #2563eb;
  --blue-light: #eff6ff;
  --green: #059669;
  --green-light: #ecfdf5;
  --orange: #d97706;
  --orange-light: #fffbeb;
  --red: #dc2626;
  --red-light: #fef2f2;
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;
  --radius: 8px;
  --shadow: 0 1px 3px rgb(0 0 0 / .1);
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

body {
  font-family: var(--font);
  color: var(--gray-800);
  background: var(--gray-50);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgb(0 0 0 / .5);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal {
  background: #fff;
  border-radius: var(--radius);
  padding: 2rem;
  width: 90%; max-width: 400px;
  box-shadow: 0 20px 60px rgb(0 0 0 / .3);
}
.modal h2 { margin-bottom: .25rem; font-size: 1.25rem; }
.modal p { color: var(--gray-500); font-size: .875rem; margin-bottom: 1.25rem; }
.modal input {
  width: 100%; padding: .625rem .75rem;
  border: 1px solid var(--gray-300);
  border-radius: var(--radius);
  font-size: .9375rem; font-family: var(--font);
  outline: none; transition: border-color .15s;
}
.modal input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgb(37 99 235 / .15); }
.modal-error { color: var(--red); font-size: .8125rem; margin-top: .5rem; display: none; }
.modal-btn {
  margin-top: 1rem; width: 100%; padding: .625rem;
  background: var(--blue); color: #fff; border: none;
  border-radius: var(--radius); font-size: .9375rem; font-weight: 500;
  cursor: pointer; transition: background .15s;
}
.modal-btn:hover { background: #1d4ed8; }
.modal-btn:disabled { opacity: .6; cursor: not-allowed; }

/* Layout */
.app { display: none; }
.app.visible { display: flex; flex-direction: column; min-height: 100vh; }

header {
  background: #fff; border-bottom: 1px solid var(--gray-200);
  position: sticky; top: 0; z-index: 50;
}
.header-inner {
  max-width: 1100px; margin: 0 auto;
  padding: .75rem 1rem;
  display: flex; align-items: center; gap: 1rem;
}
.header-inner h1 { font-size: 1.125rem; white-space: nowrap; }

nav {
  display: flex; gap: .25rem;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
  scrollbar-width: none; flex: 1;
}
nav::-webkit-scrollbar { display: none; }
nav a {
  padding: .375rem .75rem;
  border-radius: var(--radius);
  font-size: .8125rem; font-weight: 500;
  color: var(--gray-600); text-decoration: none;
  white-space: nowrap; transition: all .15s;
}
nav a:hover { background: var(--gray-100); color: var(--gray-900); }
nav a.active { background: var(--blue-light); color: var(--blue); }

.header-actions {
  display: flex; align-items: center; gap: .5rem;
  margin-left: auto; white-space: nowrap;
}
.key-badge {
  font-size: .75rem; color: var(--gray-400);
  font-family: monospace;
}
.btn-icon {
  background: none; border: none; padding: .25rem;
  cursor: pointer; color: var(--gray-400);
  border-radius: var(--radius); transition: all .15s;
  font-size: 1rem; line-height: 1;
}
.btn-icon:hover { color: var(--gray-700); background: var(--gray-100); }

main {
  max-width: 1100px; width: 100%;
  margin: 0 auto; padding: 1.5rem 1rem;
  flex: 1;
}

/* View header */
.view-header {
  display: flex; align-items: center; gap: .75rem;
  margin-bottom: 1.25rem; flex-wrap: wrap;
}
.view-header h2 { font-size: 1.375rem; font-weight: 600; }
.count-badge {
  background: var(--gray-200); color: var(--gray-600);
  font-size: .75rem; font-weight: 600;
  padding: .125rem .5rem; border-radius: 999px;
}

/* Breadcrumb */
.breadcrumb {
  font-size: .8125rem; color: var(--gray-500); margin-bottom: 1rem;
}
.breadcrumb a { color: var(--blue); text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }

/* Cards */
.card {
  background: #fff; border: 1px solid var(--gray-200);
  border-radius: var(--radius); padding: 1rem;
  margin-bottom: .5rem; transition: box-shadow .15s;
}
.card:hover { box-shadow: var(--shadow); }
.card-title { font-size: .9375rem; font-weight: 500; margin-bottom: .25rem; }
.card-notes {
  font-size: .8125rem; color: var(--gray-500);
  margin-bottom: .5rem;
  display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden;
}
.card-meta {
  display: flex; flex-wrap: wrap; gap: .375rem;
  align-items: center; font-size: .75rem;
}

/* Clickable card */
a.card { text-decoration: none; color: inherit; display: block; cursor: pointer; }

/* Tags */
.tag {
  display: inline-flex; align-items: center;
  padding: .125rem .5rem; border-radius: 999px;
  font-size: .6875rem; font-weight: 500;
  background: var(--gray-100); color: var(--gray-600);
}
.tag-dot {
  width: 6px; height: 6px; border-radius: 50%;
  margin-right: .25rem; flex-shrink: 0;
}

/* Badges */
.badge {
  display: inline-flex; align-items: center;
  padding: .125rem .5rem; border-radius: 999px;
  font-size: .6875rem; font-weight: 500;
}
.badge-blue { background: var(--blue-light); color: var(--blue); }
.badge-green { background: var(--green-light); color: var(--green); }
.badge-orange { background: var(--orange-light); color: var(--orange); }
.badge-red { background: var(--red-light); color: var(--red); }
.badge-gray { background: var(--gray-100); color: var(--gray-500); }

/* Due date */
.due { font-weight: 500; }
.due-overdue { color: var(--red); }
.due-soon { color: var(--orange); }
.due-ok { color: var(--gray-500); }

/* Tabs */
.tabs {
  display: flex; gap: .25rem;
  border-bottom: 1px solid var(--gray-200);
  margin-bottom: 1rem;
}
.tab {
  padding: .5rem .75rem;
  font-size: .8125rem; font-weight: 500;
  color: var(--gray-500); cursor: pointer;
  border: none; background: none;
  border-bottom: 2px solid transparent;
  transition: all .15s;
}
.tab:hover { color: var(--gray-700); }
.tab.active { color: var(--blue); border-bottom-color: var(--blue); }

/* Filter bar */
.filter-bar {
  display: flex; flex-wrap: wrap; gap: .5rem;
  margin-bottom: 1rem;
}
.filter-bar select {
  padding: .375rem .625rem;
  border: 1px solid var(--gray-300);
  border-radius: var(--radius);
  font-size: .8125rem; font-family: var(--font);
  color: var(--gray-700); background: #fff;
  cursor: pointer; outline: none;
}
.filter-bar select:focus { border-color: var(--blue); }

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: .75rem; margin-bottom: 1rem;
}
.stat-card {
  background: #fff; border: 1px solid var(--gray-200);
  border-radius: var(--radius); padding: 1rem;
}
.stat-card h3 {
  font-size: .8125rem; font-weight: 600;
  color: var(--gray-500); text-transform: uppercase;
  letter-spacing: .03em; margin-bottom: .5rem;
}
.stat-number {
  font-size: 2rem; font-weight: 700;
  line-height: 1.1;
}
.stat-list { list-style: none; }
.stat-list li {
  padding: .375rem 0;
  border-bottom: 1px solid var(--gray-100);
  font-size: .8125rem;
  display: flex; justify-content: space-between; align-items: center;
}
.stat-list li:last-child { border-bottom: none; }

/* Progress bar */
.progress {
  height: 4px; background: var(--gray-200);
  border-radius: 2px; overflow: hidden;
  margin-top: .375rem;
}
.progress-fill {
  height: 100%; background: var(--blue);
  border-radius: 2px; transition: width .3s;
}

/* Detail header */
.detail-header {
  background: #fff; border: 1px solid var(--gray-200);
  border-radius: var(--radius); padding: 1.25rem;
  margin-bottom: 1rem;
}
.detail-header h2 { font-size: 1.25rem; margin-bottom: .5rem; }
.detail-meta {
  display: flex; flex-wrap: wrap; gap: .5rem .75rem;
  font-size: .8125rem; color: var(--gray-500);
}

/* Empty + loading + error */
.empty {
  text-align: center; padding: 3rem 1rem;
  color: var(--gray-400);
}
.empty-icon { font-size: 2rem; margin-bottom: .5rem; }
.empty p { font-size: .9375rem; }

.loader {
  display: flex; justify-content: center; padding: 3rem;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-box {
  background: var(--red-light); border: 1px solid #fecaca;
  border-radius: var(--radius); padding: 1rem;
  color: var(--red); font-size: .875rem;
}
.error-box button {
  margin-top: .5rem; padding: .375rem .75rem;
  background: var(--red); color: #fff; border: none;
  border-radius: var(--radius); cursor: pointer;
  font-size: .8125rem;
}

/* Section divider */
.section-label {
  font-size: .75rem; font-weight: 600;
  color: var(--gray-400); text-transform: uppercase;
  letter-spacing: .05em;
  padding: .75rem 0 .375rem;
}

/* Energy */
.energy { font-size: .6875rem; font-weight: 500; }
.energy-low { color: var(--blue); }
.energy-medium { color: var(--orange); }
.energy-high { color: var(--red); }

/* Responsive */
@media (max-width: 640px) {
  .header-inner { flex-wrap: wrap; }
  nav { order: 3; width: 100%; }
  .stats-grid { grid-template-columns: 1fr; }
}

/* Form modal fields */
.cm-field { margin-bottom: 1rem; }
.cm-field label {
  display: block; font-size: .8125rem; font-weight: 500;
  color: var(--gray-700); margin-bottom: .375rem;
}
.cm-field input, .cm-field textarea, .cm-field select {
  width: 100%; padding: .5rem .75rem;
  border: 1px solid var(--gray-300); border-radius: var(--radius);
  font-size: .9375rem; font-family: var(--font);
  outline: none; transition: border-color .15s;
}
.cm-field input:focus, .cm-field textarea:focus, .cm-field select:focus {
  border-color: var(--blue); box-shadow: 0 0 0 3px rgb(37 99 235 / .15);
}
.cm-field textarea { resize: vertical; min-height: 80px; }
.cm-multiselect {
  border: 1px solid var(--gray-300); border-radius: var(--radius);
  padding: .5rem; max-height: 140px; overflow-y: auto;
}
.cm-multiselect label {
  display: flex; align-items: center; gap: .5rem;
  padding: .25rem 0; font-weight: 400; cursor: pointer;
}
.cm-multiselect input[type=checkbox] { width: auto; }
.modal-cancel {
  margin-top: .5rem; width: 100%; padding: .625rem;
  background: none; color: var(--gray-600);
  border: 1px solid var(--gray-300);
  border-radius: var(--radius); font-size: .9375rem;
  cursor: pointer; transition: all .15s;
}
.modal-cancel:hover { background: var(--gray-100); }

/* Card action buttons */
.card-actions {
  display: flex; gap: .375rem;
  margin-top: .5rem; flex-wrap: wrap;
}
.btn-action {
  padding: .25rem .625rem; border-radius: var(--radius);
  font-size: .75rem; font-weight: 500; border: 1px solid;
  cursor: pointer; transition: all .15s; line-height: 1.4;
}
.btn-complete {
  background: var(--green-light); color: var(--green);
  border-color: #a7f3d0;
}
.btn-complete:hover { background: #d1fae5; }
.btn-edit {
  background: var(--blue-light); color: var(--blue);
  border-color: #bfdbfe;
}
.btn-edit:hover { background: #dbeafe; }
.btn-delete {
  background: var(--red-light); color: var(--red);
  border-color: #fecaca;
}
.btn-delete:hover { background: #fee2e2; }
.btn-new {
  margin-left: auto; padding: .375rem .875rem;
  background: var(--blue); color: #fff; border: none;
  border-radius: var(--radius); font-size: .8125rem; font-weight: 500;
  cursor: pointer; transition: background .15s;
}
.btn-new:hover { background: #1d4ed8; }

/* Confirm dialog */
.confirm-msg {
  color: var(--gray-600); font-size: .9375rem;
  margin-bottom: 1.25rem; line-height: 1.5;
}
.confirm-btns { display: flex; gap: .5rem; }
.confirm-btns button { flex: 1; }
.card > a { display: block; text-decoration: none; color: inherit; }
</style>
</head>
<body>

<div id="api-key-modal" class="modal-overlay">
  <div class="modal">
    <h2>GTD Dashboard</h2>
    <p>Enter your API key to view your GTD data.</p>
    <input type="text" id="key-input" placeholder="Your API key" autocomplete="off" spellcheck="false">
    <div id="key-error" class="modal-error"></div>
    <button id="key-submit" class="modal-btn">Connect</button>
  </div>
</div>

<div id="app" class="app">
  <header>
    <div class="header-inner">
      <h1>GTD</h1>
      <nav id="main-nav">
        <a href="#inbox">Inbox</a>
        <a href="#next-actions">Next Actions</a>
        <a href="#projects">Projects</a>
        <a href="#someday">Someday</a>
        <a href="#tickler">Tickler</a>
        <a href="#areas">Areas</a>
        <a href="#tags">Tags</a>
        <a href="#review">Review</a>
      </nav>
      <div class="header-actions">
        <span id="key-badge" class="key-badge"></span>
        <button class="btn-icon" id="btn-refresh" title="Refresh">&#x21bb;</button>
        <button class="btn-icon" id="btn-logout" title="Change API key">&#x2715;</button>
      </div>
    </div>
  </header>
  <main id="view"></main>
</div>

<div id="crud-modal" class="modal-overlay" style="display:none">
  <div class="modal" style="max-width:520px">
    <h2 id="cm-title"></h2>
    <div id="cm-body"></div>
    <div id="cm-err" class="modal-error"></div>
    <button id="cm-submit" class="modal-btn"></button>
    <button id="cm-cancel" class="modal-cancel">Cancel</button>
  </div>
</div>

<div id="confirm-modal" class="modal-overlay" style="display:none">
  <div class="modal" style="max-width:380px">
    <h2>Confirm</h2>
    <p id="confirm-msg" class="confirm-msg"></p>
    <div class="confirm-btns">
      <button id="confirm-cancel" class="modal-cancel">Cancel</button>
      <button id="confirm-ok" class="modal-btn" style="background:var(--red)">Delete</button>
    </div>
  </div>
</div>

<script>
// GTD Dashboard - Read-only frontend
// All user-provided data is escaped via esc() before DOM insertion.
(function() {
"use strict";

// ── Utilities ──────────────────────────────────────────────────
// Escape HTML to prevent XSS - uses textContent assignment for safe escaping
function esc(s) {
  if (!s) return "";
  var d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function daysUntil(iso) {
  if (!iso) return Infinity;
  return Math.ceil((new Date(iso) - new Date()) / 86400000);
}

function dueBadge(iso, hard) {
  if (!iso) return "";
  var d = daysUntil(iso);
  var cls = d < 0 ? "due-overdue" : d <= 3 ? "due-soon" : "due-ok";
  var label = d < 0 ? Math.abs(d) + "d overdue" : d === 0 ? "due today" : d + "d left";
  return '<span class="due ' + cls + '">' + (hard ? "! " : "") + label + "</span>";
}

function lsGet(k) { try { return localStorage.getItem(k); } catch(e) { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); } catch(e) {} }
function lsDel(k) { try { localStorage.removeItem(k); } catch(e) {} }

function validColor(c) {
  return c && /^#[0-9A-Fa-f]{6}$/.test(c) ? c : null;
}

function tagHtml(t) {
  var color = validColor(t.color);
  var dot = color ? '<span class="tag-dot" style="background:' + color + '"></span>' : "";
  return '<span class="tag">' + dot + esc(t.name) + "</span>";
}

function energyHtml(e) {
  if (!e) return "";
  return '<span class="energy energy-' + esc(e) + '">' + esc(e) + " energy</span>";
}

function timeHtml(m) {
  if (!m) return "";
  return '<span class="badge badge-gray">' + (m >= 60 ? Math.round(m / 60) + "h" : m + "m") + "</span>";
}

function loader() { return '<div class="loader"><div class="spinner"></div></div>'; }
function emptyMsg(icon, msg) { return '<div class="empty"><div class="empty-icon">' + icon + "</div><p>" + esc(msg) + "</p></div>"; }

function progressBar(done, total) {
  var pct = total > 0 ? Math.round(done / total * 100) : 0;
  return '<div class="progress"><div class="progress-fill" style="width:' + pct + '%"></div></div>';
}

function groupBy(arr, fn) {
  var m = {};
  arr.forEach(function(item) {
    var k = fn(item);
    if (!m[k]) m[k] = [];
    m[k].push(item);
  });
  return m;
}

// ── API Client ─────────────────────────────────────────────────
var api = {
  key: null,

  async request(path) {
    var resp = await fetch(path, { headers: { "X-API-Key": this.key } });
    if (resp.status === 401 || resp.status === 403) {
      this.key = null;
      lsDel("gtd_api_key");
      disconnectSSE();
      showModal();
      throw new Error("auth");
    }
    if (!resp.ok) throw new Error(resp.status + " " + resp.statusText);
    return resp.json();
  },

  getInbox()                { return this.request("/inbox"); },
  getNextActions(q)         { return this.request("/next-actions" + (q || "")); },
  getProjects(q)            { return this.request("/projects" + (q || "")); },
  getProjectActions(id, c)  { return this.request("/projects/" + id + "/actions" + (c ? "?include_completed=true" : "")); },
  getProject(id)            { return this.request("/projects/" + id); },
  getSomeday()              { return this.request("/someday-maybe"); },
  getTickler()              { return this.request("/tickler"); },
  getTicklerToday()         { return this.request("/tickler/today"); },
  getAreas()                { return this.request("/areas"); },
  getArea(id)               { return this.request("/areas/" + id); },
  getAreaProjects(id)       { return this.request("/areas/" + id + "/projects"); },
  getAreaActions(id)        { return this.request("/areas/" + id + "/actions"); },
  getTags()                 { return this.request("/tags"); },
  getTagItems(id)           { return this.request("/tags/" + id + "/items"); },
  getTag(id)                { return this.request("/tags/" + id); },
  reviewInbox()             { return this.request("/review/inbox-count"); },
  reviewStale()             { return this.request("/review/stale-projects"); },
  reviewDeadlines(d)        { return this.request("/review/upcoming-deadlines?days=" + (d || 7)); },
  reviewWaiting()           { return this.request("/review/waiting-for"); },
  reviewOverdue()           { return this.request("/review/overdue"); },
  validateKey()             { return this.request("/auth/keys/current"); }
};

// ── API Mutations ───────────────────────────────────────────────
api.mutate = async function(method, path, body) {
  var opts = { method: method, headers: { "X-API-Key": this.key } };
  if (body !== null && body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  var resp = await fetch(path, opts);
  if (resp.status === 401 || resp.status === 403) {
    this.key = null; lsDel("gtd_api_key"); disconnectSSE(); showModal();
    throw new Error("auth");
  }
  if (resp.status === 204) return null;
  if (!resp.ok) {
    var err;
    try { err = (await resp.json()).detail; } catch(ex) { err = resp.statusText; }
    throw new Error(err || resp.status);
  }
  return resp.json();
};

function statusToPath(status) {
  if (status === "inbox") return "/inbox";
  if (status === "next_action") return "/next-actions";
  if (status === "someday_maybe") return "/someday-maybe";
  return "/" + status;
}

api.createItem = function(status, body) { return this.mutate("POST", statusToPath(status), body); };
api.updateItem = function(status, id, body) { return this.mutate("PATCH", statusToPath(status) + "/" + id, body); };
api.deleteItem = function(status, id) { return this.mutate("DELETE", statusToPath(status) + "/" + id, null); };
api.completeItem = function(status, id) { return this.mutate("POST", statusToPath(status) + "/" + id + "/complete", {}); };
api.createProject = function(body) { return this.mutate("POST", "/projects", body); };
api.updateProject = function(id, body) { return this.mutate("PATCH", "/projects/" + id, body); };
api.deleteProject = function(id) { return this.mutate("DELETE", "/projects/" + id, null); };
api.createTag = function(body) { return this.mutate("POST", "/tags", body); };
api.updateTag = function(id, body) { return this.mutate("PATCH", "/tags/" + id, body); };
api.deleteTag = function(id) { return this.mutate("DELETE", "/tags/" + id, null); };

// ── DOM refs ───────────────────────────────────────────────────
var $modal   = document.getElementById("api-key-modal");
var $keyIn   = document.getElementById("key-input");
var $keyErr  = document.getElementById("key-error");
var $keyBtn  = document.getElementById("key-submit");
var $app     = document.getElementById("app");
var $view    = document.getElementById("view");
var $nav     = document.getElementById("main-nav");
var $badge   = document.getElementById("key-badge");

// ── Auth flow ──────────────────────────────────────────────────
function showModal() {
  $modal.style.display = "flex";
  $app.classList.remove("visible");
  $keyIn.value = "";
  $keyErr.style.display = "none";
  $keyIn.focus();
}

function hideModal() {
  $modal.style.display = "none";
  $app.classList.add("visible");
  var k = api.key || "";
  $badge.textContent = k.length > 12 ? k.slice(0, 6) + "..." + k.slice(-4) : k;
}

$keyBtn.addEventListener("click", tryConnect);
$keyIn.addEventListener("keydown", function(e) { if (e.key === "Enter") tryConnect(); });

async function tryConnect() {
  var k = $keyIn.value.trim();
  if (!k) return;
  $keyBtn.disabled = true;
  $keyErr.style.display = "none";
  try {
    api.key = k;
    await api.validateKey();
    lsSet("gtd_api_key", k);
    hideModal();
    connectSSE();
    route();
  } catch (e) {
    if (e.message !== "auth") {
      $keyErr.textContent = "Could not connect. Check your API key.";
      $keyErr.style.display = "block";
    }
    api.key = null;
  } finally {
    $keyBtn.disabled = false;
  }
}

document.getElementById("btn-logout").addEventListener("click", function() {
  disconnectSSE();
  api.key = null;
  lsDel("gtd_api_key");
  cache = {};
  showModal();
});

document.getElementById("btn-refresh").addEventListener("click", function() {
  cache = {};
  route();
});

// ── SSE ─────────────────────────────────────────────────────────
var sse = null;

function connectSSE() {
  disconnectSSE();
  if (!api.key) return;
  sse = new EventSource("/events?key=" + encodeURIComponent(api.key));
  sse.addEventListener("change", function() {
    cache = {};
    route();
  });
  sse.onerror = function() {
    disconnectSSE();
    if (api.key) setTimeout(connectSSE, 5000);
  };
}

function disconnectSSE() {
  if (sse) { sse.close(); sse = null; }
}

// ── CRUD Modal refs ─────────────────────────────────────────────
var $crudModal    = document.getElementById("crud-modal");
var $cmTitle      = document.getElementById("cm-title");
var $cmBody       = document.getElementById("cm-body");
var $cmErr        = document.getElementById("cm-err");
var $cmSubmit     = document.getElementById("cm-submit");
var $cmCancel     = document.getElementById("cm-cancel");
var $confirmModal = document.getElementById("confirm-modal");
var $confirmMsg   = document.getElementById("confirm-msg");
var $confirmOk    = document.getElementById("confirm-ok");
var $confirmCancel = document.getElementById("confirm-cancel");

// ── CRUD Modal ──────────────────────────────────────────────────
// Note: innerHTML usage in _buildFields is safe because all user data passes
// through esc() (DOM-based textContent escaping) before insertion.
// The esc() function at line 394 prevents XSS by design.
var modal = {
  _onSubmit: null,
  _submitLabel: "Save",

  open: function(title, fields, submitLabel, onSubmit) {
    $cmTitle.textContent = title;
    this._submitLabel = submitLabel || "Save";
    $cmSubmit.textContent = this._submitLabel;
    this._onSubmit = onSubmit;
    this._buildFields(fields);
    $cmErr.style.display = "none";
    $cmErr.textContent = "";
    $cmSubmit.disabled = false;
    $crudModal.style.display = "flex";
    var first = $cmBody.querySelector("input,textarea,select");
    if (first) first.focus();
  },

  close: function() {
    $crudModal.style.display = "none";
    $cmBody.textContent = "";
    this._onSubmit = null;
  },

  _buildFields: function(fields) {
    // All user-provided values are escaped via esc() before DOM insertion
    var html = fields.map(function(f) {
      var id = "cm-f-" + f.name;
      var inner = "";
      if (f.type === "text" || f.type === "color") {
        inner = '<input type="' + f.type + '" id="' + id + '" name="' + f.name + '"' +
          (f.required ? " required" : "") +
          ' value="' + esc(f.value || "") + '">';
      } else if (f.type === "date") {
        inner = '<input type="date" id="' + id + '" name="' + f.name + '" value="' + esc(f.value || "") + '">';
      } else if (f.type === "textarea") {
        inner = '<textarea id="' + id + '" name="' + f.name + '">' + esc(f.value || "") + "</textarea>";
      } else if (f.type === "select") {
        inner = '<select id="' + id + '" name="' + f.name + '">' +
          (f.options || []).map(function(o) {
            return '<option value="' + esc(String(o.value)) + '"' +
              (String(o.value) === String(f.value) ? " selected" : "") + '>' + esc(o.label) + "</option>";
          }).join("") + "</select>";
      } else if (f.type === "multiselect") {
        var selected = f.value || [];
        inner = '<div class="cm-multiselect">' +
          (f.options || []).map(function(o) {
            var chk = selected.indexOf(o.value) !== -1 ? " checked" : "";
            var dot = o.color ? '<span class="tag-dot" style="background:' + o.color + '"></span>' : "";
            return '<label><input type="checkbox" name="' + f.name + '" value="' + parseInt(o.value) + '"' + chk + '>' + dot + esc(o.label) + "</label>";
          }).join("") + "</div>";
      }
      return '<div class="cm-field"><label for="' + id + '">' + esc(f.label) + (f.required ? ' <span style="color:var(--red)">*</span>' : "") + "</label>" + inner + "</div>";
    }).join("");
    $cmBody.textContent = "";
    $cmBody.insertAdjacentHTML("afterbegin", html);
  },

  getValues: function() {
    var out = {};
    var els = $cmBody.querySelectorAll("[name]");
    var multis = {};
    els.forEach(function(el) {
      if (el.type === "checkbox") {
        if (!multis[el.name]) multis[el.name] = [];
        if (el.checked) multis[el.name].push(parseInt(el.value));
      } else if (el.type === "date") {
        out[el.name] = el.value ? el.value + "T00:00:00" : null;
      } else {
        out[el.name] = el.value || null;
      }
    });
    Object.keys(multis).forEach(function(k) { out[k] = multis[k]; });
    if (out.project_id) out.project_id = parseInt(out.project_id) || null;
    return out;
  },

  showError: function(msg) {
    $cmErr.textContent = msg;
    $cmErr.style.display = "block";
  },

  setLoading: function(on) {
    $cmSubmit.disabled = on;
    $cmSubmit.textContent = on ? "Saving..." : this._submitLabel;
  }
};

$cmCancel.addEventListener("click", function() { modal.close(); });
$crudModal.addEventListener("click", function(e) { if (e.target === $crudModal) modal.close(); });
$cmSubmit.addEventListener("click", async function() {
  if (!modal._onSubmit) return;
  var required = $cmBody.querySelectorAll("[required]");
  var missing = false;
  required.forEach(function(el) {
    if (!el.value.trim()) { el.style.borderColor = "var(--red)"; missing = true; }
    else { el.style.borderColor = ""; }
  });
  if (missing) { modal.showError("Please fill in all required fields"); return; }
  var vals = modal.getValues();
  $cmErr.style.display = "none";
  modal.setLoading(true);
  try {
    await modal._onSubmit(vals);
    modal.close();
    cache = {}; route();
  } catch(e) {
    if (e.message !== "auth") modal.showError(e.message || "An error occurred");
  } finally {
    modal.setLoading(false);
  }
});

// ── Confirm Dialog ──────────────────────────────────────────────
var confirmCallback = null;

function showConfirm(msg, onOk, btnLabel, btnColor) {
  $confirmMsg.textContent = msg;
  $confirmOk.textContent = btnLabel || "Delete";
  $confirmOk.style.background = btnColor || "var(--red)";
  confirmCallback = onOk;
  $confirmModal.style.display = "flex";
}

$confirmCancel.addEventListener("click", function() {
  $confirmModal.style.display = "none";
  confirmCallback = null;
});
$confirmOk.addEventListener("click", async function() {
  $confirmModal.style.display = "none";
  if (confirmCallback) {
    try { await confirmCallback(); cache = {}; route(); } catch(e) { if (e.message !== "auth") showErr(e); }
    confirmCallback = null;
  }
});
$confirmModal.addEventListener("click", function(e) {
  if (e.target === $confirmModal) { $confirmModal.style.display = "none"; confirmCallback = null; }
});
document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    if ($crudModal.style.display !== "none") modal.close();
    else if ($confirmModal.style.display !== "none") {
      $confirmModal.style.display = "none"; confirmCallback = null;
    }
  }
});

// ── Field Factories ─────────────────────────────────────────────
function itemFields(item, projects, tags) {
  var projectOpts = [{value: "", label: "None"}].concat(
    (projects || []).map(function(p) { return {value: p.id, label: p.title}; })
  );
  var tagOpts = (tags || []).map(function(t) {
    return {value: t.id, label: t.name, color: validColor(t.color)};
  });
  var selectedTagIds = item ? item.tags.map(function(t) { return t.id; }) : [];
  return [
    {name:"title",        label:"Title",        type:"text",        required:true,  value: item ? item.title : ""},
    {name:"notes",        label:"Notes",        type:"textarea",    required:false, value: item ? (item.notes || "") : ""},
    {name:"project_id",   label:"Project",      type:"select",      required:false, options: projectOpts, value: item ? (item.project_id || "") : ""},
    {name:"tag_ids",      label:"Tags",         type:"multiselect", required:false, options: tagOpts, value: selectedTagIds},
    {name:"energy_level", label:"Energy Level", type:"select",      required:false, options: [{value:"",label:"Any"},{value:"low",label:"Low"},{value:"medium",label:"Medium"},{value:"high",label:"High"}], value: item ? (item.energy_level || "") : ""},
    {name:"due_date",     label:"Due Date",     type:"date",        required:false, value: item && item.due_date ? item.due_date.slice(0,10) : ""}
  ];
}

function projectFields(project) {
  return [
    {name:"title",       label:"Title",       type:"text",     required:true,  value: project ? project.title : ""},
    {name:"description", label:"Description", type:"textarea", required:false, value: project ? (project.description || "") : ""},
    {name:"outcome",     label:"Outcome",     type:"textarea", required:false, value: project ? (project.outcome || "") : ""},
    {name:"status",      label:"Status",      type:"select",   required:false, options: [{value:"active",label:"Active"},{value:"on_hold",label:"On Hold"},{value:"completed",label:"Completed"}], value: project ? project.status : "active"},
    {name:"due_date",    label:"Due Date",    type:"date",     required:false, value: project && project.due_date ? project.due_date.slice(0,10) : ""}
  ];
}

function tagFields(tag) {
  return [
    {name:"name",  label:"Tag Name", type:"text",  required:true,  value: tag ? tag.name : ""},
    {name:"color", label:"Color",    type:"color", required:false, value: tag && tag.color ? tag.color : "#6b7280"}
  ];
}

// ── CRUD Handlers ───────────────────────────────────────────────
async function handleNewItem(status) {
  var projects = cache.projectList || (cache.projectList = await api.getProjects());
  var tags = cache.tags || (cache.tags = await api.getTags());
  modal.open("New Item", itemFields(null, projects, tags), "Create", async function(vals) {
    await api.createItem(status, vals);
  });
}

async function handleEdit(status, id) {
  var item = await api.request(statusToPath(status) + "/" + id);
  var projects = cache.projectList || (cache.projectList = await api.getProjects());
  var tags = cache.tags || (cache.tags = await api.getTags());
  modal.open("Edit Item", itemFields(item, projects, tags), "Save", async function(vals) {
    await api.updateItem(status, id, vals);
  });
}

function handleDelete(status, id, title) {
  showConfirm('Delete "' + title + '"?', async function() {
    await api.deleteItem(status, id);
  });
}

function handleComplete(status, id, title) {
  showConfirm('Mark "' + title + '" as done?', async function() {
    await api.completeItem(status, id);
  }, "Done", "var(--green)");
}

async function handleNewProject() {
  modal.open("New Project", projectFields(null), "Create", async function(vals) {
    await api.createProject(vals);
  });
}

async function handleEditProject(id) {
  var project = await api.getProject(id);
  modal.open("Edit Project", projectFields(project), "Save", async function(vals) {
    await api.updateProject(id, vals);
  });
}

function handleDeleteProject(id, title) {
  showConfirm('Delete project "' + title + '"? All actions will be unlinked.', async function() {
    await api.deleteProject(id);
  });
}

function handleNewTag() {
  modal.open("New Tag", tagFields(null), "Create", async function(vals) {
    await api.createTag(vals);
  });
}

async function handleEditTag(id) {
  var tag = await api.getTag(id);
  modal.open("Edit Tag", tagFields(tag), "Save", async function(vals) {
    await api.updateTag(id, vals);
  });
}

function handleDeleteTag(id, title) {
  showConfirm('Delete tag "' + title + '"? It will be removed from all items.', async function() {
    await api.deleteTag(id);
  });
}

// ── Cache ──────────────────────────────────────────────────────
var cache = {};

// ── Render helpers ─────────────────────────────────────────────
function itemCard(item, statusSlug) {
  var meta = [];
  if (item.tags) item.tags.forEach(function(t) { meta.push(tagHtml(t)); });
  if (item.due_date) meta.push(dueBadge(item.due_date, item.due_date_is_hard));
  if (item.energy_level) meta.push(energyHtml(item.energy_level));
  if (item.time_estimate) meta.push(timeHtml(item.time_estimate));
  if (item.delegated_to) meta.push('<span class="badge badge-orange">&#x21e8; ' + esc(item.delegated_to) + "</span>");
  if (item.project_id) meta.push('<span class="badge badge-blue">project #' + item.project_id + "</span>");

  var actions = "";
  if (statusSlug) {
    var t = esc(item.title);
    var sa = 'data-id="' + parseInt(item.id) + '" data-status="' + esc(statusSlug) + '"';
    actions = '<div class="card-actions">' +
      '<button class="btn-action btn-complete" data-action="complete" ' + sa + ' data-title="' + t + '">Done</button>' +
      '<button class="btn-action btn-edit" data-action="edit" ' + sa + '>Edit</button>' +
      '<button class="btn-action btn-delete" data-action="delete" ' + sa + ' data-title="' + t + '">Delete</button>' +
    "</div>";
  }

  return '<div class="card">' +
    '<div class="card-title">' + esc(item.title) + "</div>" +
    (item.notes ? '<div class="card-notes">' + esc(item.notes) + "</div>" : "") +
    (meta.length ? '<div class="card-meta">' + meta.join(" ") + "</div>" : "") +
    actions +
    "</div>";
}

function projectCard(p) {
  var statusCls = p.status === "active" ? "badge-green" : p.status === "on_hold" ? "badge-orange" : "badge-gray";
  var done = p.completed_action_count || 0;
  var total = p.action_count || 0;
  var hasStats = typeof p.action_count !== "undefined";
  var t = esc(p.title);
  return '<div class="card">' +
    '<a href="#projects/' + parseInt(p.id) + '">' +
    '<div class="card-title">' + t + "</div>" +
    (p.description ? '<div class="card-notes">' + esc(p.description) + "</div>" : "") +
    '<div class="card-meta">' +
      '<span class="badge ' + statusCls + '">' + esc(p.status.replace("_", " ")) + "</span>" +
      (hasStats ? '<span class="badge badge-gray">' + done + "/" + total + " actions</span>" : "") +
      (p.has_next_action === false && p.status === "active" ? '<span class="badge badge-red">no next action</span>' : "") +
      (p.due_date ? " " + dueBadge(p.due_date, p.due_date_is_hard) : "") +
    "</div>" +
    (hasStats ? progressBar(done, total) : "") +
    "</a>" +
    '<div class="card-actions">' +
      '<button class="btn-action btn-edit" data-action="edit-project" data-id="' + parseInt(p.id) + '">Edit</button>' +
      '<button class="btn-action btn-delete" data-action="delete-project" data-id="' + parseInt(p.id) + '" data-title="' + t + '">Delete</button>' +
    "</div></div>";
}

function areaCard(a) {
  return '<a class="card" href="#areas/' + parseInt(a.id) + '">' +
    '<div class="card-title">' + esc(a.name) + "</div>" +
    (a.description ? '<div class="card-notes">' + esc(a.description) + "</div>" : "") +
    '<div class="card-meta">' +
      '<span class="badge badge-blue">' + (a.project_count || 0) + " projects</span>" +
      '<span class="badge badge-gray">' + (a.action_count || 0) + " actions</span>" +
    "</div></a>";
}

// ── Views ──────────────────────────────────────────────────────
async function viewInbox() {
  $view.innerHTML = loader();
  try {
    var items = cache.inbox || (cache.inbox = await api.getInbox());
    var h = '<div class="view-header"><h2>Inbox</h2><span class="count-badge">' + items.length + '</span><button class="btn-new" data-action="new-item" data-status="inbox">+ New</button></div>';
    if (!items.length) { $view.innerHTML = h + emptyMsg("&#x1f4e5;", "Inbox is empty"); return; }
    $view.innerHTML = h + items.map(function(i) { return itemCard(i, "inbox"); }).join("");
  } catch (e) { showErr(e); }
}

async function viewNextActions() {
  $view.innerHTML = loader();
  try {
    var tags = cache.tags || (cache.tags = await api.getTags());
    var projects = cache.projectList || (cache.projectList = await api.getProjects());
    var areas = cache.areas || (cache.areas = await api.getAreas());

    var items = cache.nextActions || (cache.nextActions = await api.getNextActions());

    var h = '<div class="view-header"><h2>Next Actions</h2><span class="count-badge">' + items.length + '</span><button class="btn-new" data-action="new-item" data-status="next_action">+ New</button></div>';

    h += '<div class="filter-bar">' +
      '<select id="f-tag"><option value="">All tags</option>' +
        tags.map(function(t) { return '<option value="' + parseInt(t.id) + '">' + esc(t.name) + " (" + (t.item_count || 0) + ")</option>"; }).join("") +
      "</select>" +
      '<select id="f-project"><option value="">All projects</option>' +
        projects.map(function(p) { return '<option value="' + parseInt(p.id) + '">' + esc(p.title) + "</option>"; }).join("") +
      "</select>" +
      '<select id="f-area"><option value="">All areas</option>' +
        areas.map(function(a) { return '<option value="' + parseInt(a.id) + '">' + esc(a.name) + "</option>"; }).join("") +
      "</select>" +
      '<select id="f-energy"><option value="">Any energy</option>' +
        '<option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>' +
      "</select>" +
    "</div>";

    h += '<div id="na-list">' + (items.length ? items.map(function(i) { return itemCard(i, "next_action"); }).join("") : emptyMsg("&#x2705;", "No next actions")) + "</div>";
    $view.innerHTML = h;

    ["f-tag", "f-project", "f-area", "f-energy"].forEach(function(id) {
      document.getElementById(id).addEventListener("change", applyNAFilters);
    });
  } catch (e) { showErr(e); }
}

async function applyNAFilters() {
  var tag = document.getElementById("f-tag").value;
  var proj = document.getElementById("f-project").value;
  var area = document.getElementById("f-area").value;
  var energy = document.getElementById("f-energy").value;
  var q = [];
  if (tag) q.push("tag_id=" + encodeURIComponent(tag));
  if (proj) q.push("project_id=" + encodeURIComponent(proj));
  if (area) q.push("area_id=" + encodeURIComponent(area));
  if (energy) q.push("energy_level=" + encodeURIComponent(energy));
  var qs = q.length ? "?" + q.join("&") : "";
  try {
    var items = await api.getNextActions(qs);
    var list = document.getElementById("na-list");
    if (list) list.innerHTML = items.length ? items.map(function(i) { return itemCard(i, "next_action"); }).join("") : emptyMsg("&#x1f50d;", "No actions match filters");
  } catch (e) { showErr(e); }
}

async function viewProjects() {
  $view.innerHTML = loader();
  try {
    var all = cache.projectList || (cache.projectList = await api.getProjects());
    var active = "active";

    function render(status) {
      active = status;
      var tabs = ["active", "on_hold", "completed"];
      var filtered = all.filter(function(p) { return p.status === status; });
      var h = '<div class="view-header"><h2>Projects</h2><span class="count-badge">' + all.length + '</span><button class="btn-new" data-action="new-project">+ New Project</button></div>';
      h += '<div class="tabs">' + tabs.map(function(t) {
        var cnt = all.filter(function(p) { return p.status === t; }).length;
        return '<button class="tab' + (t === active ? " active" : "") + '" data-tab="' + t + '">' + esc(t.replace("_", " ")) + " (" + cnt + ")</button>";
      }).join("") + "</div>";
      h += '<div id="proj-list">' + (filtered.length ? filtered.map(projectCard).join("") : emptyMsg("&#x1f4c1;", "No " + status.replace("_", " ") + " projects")) + "</div>";
      $view.innerHTML = h;
      $view.querySelectorAll(".tab").forEach(function(btn) {
        btn.addEventListener("click", function() { render(btn.dataset.tab); });
      });
    }
    render(active);
  } catch (e) { showErr(e); }
}

async function viewProjectDetail(id) {
  $view.innerHTML = loader();
  try {
    var p = await api.getProject(id);
    var actions = await api.getProjectActions(id, true);

    var h = '<div class="breadcrumb"><a href="#projects">Projects</a> &rsaquo; ' + esc(p.title) + "</div>";
    h += '<div class="detail-header">';
    h += "<h2>" + esc(p.title) + "</h2>";
    if (p.description) h += '<p style="color:var(--gray-600);margin-bottom:.5rem">' + esc(p.description) + "</p>";
    if (p.outcome) h += '<p style="font-size:.8125rem;color:var(--gray-500)"><strong>Outcome:</strong> ' + esc(p.outcome) + "</p>";
    h += '<div class="detail-meta">';
    var statusCls = p.status === "active" ? "badge-green" : p.status === "on_hold" ? "badge-orange" : "badge-gray";
    h += '<span class="badge ' + statusCls + '">' + esc(p.status.replace("_", " ")) + "</span>";
    h += '<span class="badge badge-gray">' + p.completed_action_count + "/" + p.action_count + " actions</span>";
    if (p.due_date) h += " " + dueBadge(p.due_date, p.due_date_is_hard);
    h += "</div>";
    h += progressBar(p.completed_action_count, p.action_count);
    h += "</div>";

    var grouped = groupBy(actions, function(a) { return a.status; });
    var order = ["next_action", "inbox", "someday_maybe", "completed"];
    var labels = { next_action: "Next Actions", inbox: "Inbox", someday_maybe: "Someday/Maybe", completed: "Completed" };
    order.forEach(function(s) {
      if (grouped[s] && grouped[s].length) {
        h += '<div class="section-label">' + esc(labels[s]) + " (" + grouped[s].length + ")</div>";
        h += grouped[s].map(function(a) { return itemCard(a, s === "completed" ? null : a.status); }).join("");
      }
    });

    if (!actions.length) h += emptyMsg("&#x1f4cb;", "No actions in this project");
    $view.innerHTML = h;
  } catch (e) { showErr(e); }
}

async function viewSomeday() {
  $view.innerHTML = loader();
  try {
    var items = cache.someday || (cache.someday = await api.getSomeday());
    var h = '<div class="view-header"><h2>Someday / Maybe</h2><span class="count-badge">' + items.length + '</span><button class="btn-new" data-action="new-item" data-status="someday_maybe">+ New</button></div>';
    if (!items.length) { $view.innerHTML = h + emptyMsg("&#x1f4ad;", "No someday/maybe items"); return; }
    $view.innerHTML = h + items.map(function(i) { return itemCard(i, "someday_maybe"); }).join("");
  } catch (e) { showErr(e); }
}

async function viewTickler() {
  $view.innerHTML = loader();
  try {
    var today = await api.getTicklerToday();
    var all = await api.getTickler();

    var total = today.length + all.length;
    var h = '<div class="view-header"><h2>Tickler</h2><span class="count-badge">' + total + "</span></div>";

    if (today.length) {
      h += '<div class="section-label">Due Today (' + today.length + ")</div>";
      h += today.map(itemCard).join("");
    }
    if (all.length) {
      h += '<div class="section-label">Upcoming (' + all.length + ")</div>";
      h += all.map(function(item) {
        var d = daysUntil(item.tickler_date);
        var meta = [];
        meta.push('<span class="badge badge-blue">' + (d <= 0 ? "now" : d + "d") + "</span>");
        meta.push('<span class="badge badge-gray">' + fmtDate(item.tickler_date) + "</span>");
        if (item.tags) item.tags.forEach(function(t) { meta.push(tagHtml(t)); });
        return '<div class="card">' +
          '<div class="card-title">' + esc(item.title) + "</div>" +
          (item.notes ? '<div class="card-notes">' + esc(item.notes) + "</div>" : "") +
          '<div class="card-meta">' + meta.join(" ") + "</div></div>";
      }).join("");
    }
    if (!total) h += emptyMsg("&#x1f4c5;", "No tickler items");
    $view.innerHTML = h;
  } catch (e) { showErr(e); }
}

async function viewAreas() {
  $view.innerHTML = loader();
  try {
    var areas = cache.areas || (cache.areas = await api.getAreas());
    var h = '<div class="view-header"><h2>Areas of Responsibility</h2><span class="count-badge">' + areas.length + "</span></div>";
    if (!areas.length) { $view.innerHTML = h + emptyMsg("&#x1f3af;", "No areas defined"); return; }
    $view.innerHTML = h + areas.map(areaCard).join("");
  } catch (e) { showErr(e); }
}

async function viewAreaDetail(id) {
  $view.innerHTML = loader();
  try {
    var area = await api.getArea(id);
    var projects = await api.getAreaProjects(id);
    var actions = await api.getAreaActions(id);

    var h = '<div class="breadcrumb"><a href="#areas">Areas</a> &rsaquo; ' + esc(area.name) + "</div>";
    h += '<div class="detail-header">';
    h += "<h2>" + esc(area.name) + "</h2>";
    if (area.description) h += '<p style="color:var(--gray-600)">' + esc(area.description) + "</p>";
    h += '<div class="detail-meta">' +
      '<span class="badge badge-blue">' + projects.length + " projects</span>" +
      '<span class="badge badge-gray">' + actions.length + " actions</span>" +
    "</div></div>";

    if (projects.length) {
      h += '<div class="section-label">Projects (' + projects.length + ")</div>";
      h += projects.map(projectCard).join("");
    }
    if (actions.length) {
      h += '<div class="section-label">Actions (' + actions.length + ")</div>";
      h += actions.map(itemCard).join("");
    }
    if (!projects.length && !actions.length) h += emptyMsg("&#x1f4c2;", "No projects or actions in this area");
    $view.innerHTML = h;
  } catch (e) { showErr(e); }
}

async function viewTags() {
  $view.innerHTML = loader();
  try {
    var tags = cache.tags || (cache.tags = await api.getTags());
    var h = '<div class="view-header"><h2>Tags</h2><span class="count-badge">' + tags.length + '</span><button class="btn-new" data-action="new-tag">+ New Tag</button></div>';
    if (!tags.length) { $view.innerHTML = h + emptyMsg("&#x1f3f7;", "No tags defined"); return; }
    h += '<div style="display:flex;flex-wrap:wrap;gap:.75rem">';
    tags.forEach(function(t) {
      var bg = validColor(t.color) || "#6b7280";
      var tEsc = esc(t.name);
      h += '<div style="display:inline-flex;flex-direction:column;align-items:flex-start;gap:.25rem">' +
        '<a href="#tags/' + parseInt(t.id) + '" style="text-decoration:none">' +
        '<span class="tag" style="font-size:.8125rem;padding:.375rem .75rem;background:' + bg + '22;border:1px solid ' + bg + '44">' +
        '<span class="tag-dot" style="background:' + bg + '"></span>' +
        tEsc + " (" + (t.item_count || 0) + ")</span></a>" +
        '<div style="display:flex;gap:.25rem">' +
        '<button class="btn-action btn-edit" data-action="edit-tag" data-id="' + parseInt(t.id) + '" style="font-size:.6875rem;padding:.125rem .5rem">Edit</button>' +
        '<button class="btn-action btn-delete" data-action="delete-tag" data-id="' + parseInt(t.id) + '" data-title="' + tEsc + '" style="font-size:.6875rem;padding:.125rem .5rem">Delete</button>' +
        "</div></div>";
    });
    h += "</div>";
    $view.innerHTML = h;
  } catch (e) { showErr(e); }
}

async function viewTagDetail(id) {
  $view.innerHTML = loader();
  try {
    var tag = await api.getTag(id);
    var items = await api.getTagItems(id);

    var h = '<div class="breadcrumb"><a href="#tags">Tags</a> &rsaquo; ' + esc(tag.name) + "</div>";
    h += '<div class="view-header"><h2>' + tagHtml(tag) + "</h2>" +
      '<span class="count-badge">' + items.length + " items</span></div>";

    if (!items.length) { $view.innerHTML = h + emptyMsg("&#x1f50d;", "No items with this tag"); return; }

    var grouped = groupBy(items, function(i) { return i.status; });
    var order = ["next_action", "inbox", "someday_maybe", "completed"];
    var labels = { next_action: "Next Actions", inbox: "Inbox", someday_maybe: "Someday/Maybe", completed: "Completed" };
    order.forEach(function(s) {
      if (grouped[s] && grouped[s].length) {
        h += '<div class="section-label">' + esc(labels[s]) + " (" + grouped[s].length + ")</div>";
        h += grouped[s].map(function(a) { return itemCard(a, s === "completed" ? null : s); }).join("");
      }
    });
    $view.innerHTML = h;
  } catch (e) { showErr(e); }
}

async function viewReview() {
  var h = '<div class="view-header"><h2>Weekly Review</h2></div><div class="stats-grid">' +
    '<div class="stat-card" id="r-inbox">' + loader() + "</div>" +
    '<div class="stat-card" id="r-overdue">' + loader() + "</div>" +
    '<div class="stat-card" id="r-deadlines">' + loader() + "</div>" +
    '<div class="stat-card" id="r-stale">' + loader() + "</div>" +
    '<div class="stat-card" id="r-waiting">' + loader() + "</div>" +
  "</div>";
  $view.innerHTML = h;

  var tasks = [
    api.reviewInbox().then(function(d) {
      var el = document.getElementById("r-inbox");
      if (!el) return;
      var color = d.count > 0 ? "var(--orange)" : "var(--green)";
      el.innerHTML = '<h3>Inbox</h3><div class="stat-number" style="color:' + color + '">' + d.count + "</div>" +
        "<p style='font-size:.8125rem;color:var(--gray-500)'>" + (d.count > 0 ? "items to process" : "all clear") + "</p>";
    }),
    api.reviewOverdue().then(function(items) {
      var el = document.getElementById("r-overdue");
      if (!el) return;
      var color = items.length > 0 ? "var(--red)" : "var(--green)";
      var out = '<h3>Overdue</h3><div class="stat-number" style="color:' + color + '">' + items.length + "</div>";
      if (items.length) {
        out += '<ul class="stat-list">' + items.slice(0, 5).map(function(i) {
          return "<li><span>" + esc(i.title) + "</span> " + dueBadge(i.due_date, i.due_date_is_hard) + "</li>";
        }).join("") + "</ul>";
        if (items.length > 5) out += '<p style="font-size:.75rem;color:var(--gray-400)">+' + (items.length - 5) + " more</p>";
      }
      el.innerHTML = out;
    }),
    api.reviewDeadlines(7).then(function(d) {
      var el = document.getElementById("r-deadlines");
      if (!el) return;
      var out = "<h3>Upcoming (7 days)</h3>";
      if (!d.deadlines.length) {
        out += '<p style="font-size:.875rem;color:var(--gray-400)">No upcoming deadlines</p>';
      } else {
        out += '<ul class="stat-list">' + d.deadlines.slice(0, 8).map(function(dl) {
          var icon = dl.type === "project" ? "&#x1f4c1;" : "&#x2022;";
          return "<li><span>" + icon + " " + esc(dl.title) + "</span>" + dueBadge(dl.due_date, dl.due_date_is_hard) + "</li>";
        }).join("") + "</ul>";
      }
      el.innerHTML = out;
    }),
    api.reviewStale().then(function(d) {
      var el = document.getElementById("r-stale");
      if (!el) return;
      var color = d.projects.length > 0 ? "var(--orange)" : "var(--green)";
      var out = '<h3>Stale Projects</h3><div class="stat-number" style="color:' + color + '">' + d.projects.length + "</div>";
      if (d.projects.length) {
        out += '<ul class="stat-list">' + d.projects.slice(0, 5).map(function(p) {
          return '<li><a href="#projects/' + parseInt(p.id) + '" style="color:var(--blue);text-decoration:none">' + esc(p.title) + "</a></li>";
        }).join("") + "</ul>";
      } else {
        out += '<p style="font-size:.8125rem;color:var(--gray-500)">All projects have next actions</p>';
      }
      el.innerHTML = out;
    }),
    api.reviewWaiting().then(function(d) {
      var el = document.getElementById("r-waiting");
      if (!el) return;
      var out = "<h3>Waiting For</h3>";
      if (!d.items.length) {
        out += '<p style="font-size:.875rem;color:var(--gray-400)">Nothing waiting</p>';
      } else {
        out += '<div class="stat-number">' + d.items.length + "</div>";
        out += '<ul class="stat-list">' + d.items.slice(0, 5).map(function(i) {
          var who = i.delegated_to ? " &#x21e8; " + esc(i.delegated_to) : "";
          return "<li><span>" + esc(i.title) + who + "</span></li>";
        }).join("") + "</ul>";
      }
      el.innerHTML = out;
    })
  ];

  Promise.allSettled(tasks);
}

// ── CRUD event delegation ───────────────────────────────────────
$view.addEventListener("click", function(e) {
  var btn = e.target.closest("[data-action]");
  if (!btn) return;
  e.preventDefault();
  var action = btn.dataset.action;
  var id     = btn.dataset.id ? parseInt(btn.dataset.id) : null;
  var status = btn.dataset.status || null;
  var title  = btn.dataset.title || "";

  switch (action) {
    case "complete":       handleComplete(status, id, title); break;
    case "edit":           handleEdit(status, id); break;
    case "delete":         handleDelete(status, id, title); break;
    case "edit-project":   handleEditProject(id); break;
    case "delete-project": handleDeleteProject(id, title); break;
    case "new-project":    handleNewProject(); break;
    case "edit-tag":       handleEditTag(id); break;
    case "delete-tag":     handleDeleteTag(id, title); break;
    case "new-tag":        handleNewTag(); break;
    case "new-item":       handleNewItem(status); break;
  }
});

// ── Error display ──────────────────────────────────────────────
function showErr(e) {
  if (e.message === "auth") return;
  $view.innerHTML = '<div class="error-box">' + esc(e.message) +
    '</div>';
}

// ── Router ─────────────────────────────────────────────────────
function route() {
  var hash = location.hash.slice(1) || "inbox";
  var parts = hash.split("/");
  var view = parts[0];
  var param = parts[1];

  $nav.querySelectorAll("a").forEach(function(a) {
    var href = a.getAttribute("href").slice(1);
    a.classList.toggle("active", href === view);
  });

  switch (view) {
    case "inbox":        viewInbox(); break;
    case "next-actions": viewNextActions(); break;
    case "projects":     param ? viewProjectDetail(param) : viewProjects(); break;
    case "someday":      viewSomeday(); break;
    case "tickler":      viewTickler(); break;
    case "areas":        param ? viewAreaDetail(param) : viewAreas(); break;
    case "tags":         param ? viewTagDetail(param) : viewTags(); break;
    case "review":       viewReview(); break;
    default:             viewInbox();
  }
}

window.addEventListener("hashchange", route);

// ── Init ───────────────────────────────────────────────────────
(function init() {
  var saved = lsGet("gtd_api_key");
  if (saved) {
    api.key = saved;
    api.validateKey().then(function() {
      hideModal();
      connectSSE();
      route();
    }).catch(function() {
      showModal();
    });
  } else {
    showModal();
  }
})();

})();
</script>
</body>
</html>
"""
