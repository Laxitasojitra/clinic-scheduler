const API = "";
let state = {
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user") || "null"),
  tab: "dashboard",
  slots: { items: [], total: 0, page: 1, page_size: 10 },
  filters: { q: "", provider_id: "", status: "", date_from: "", date_to: "" },
  providers: [],
  dashboard: null,
  alerts: { count: 0, alerts: [] },
  modalSlot: null,
  error: "",
};

async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  if (opts.body && !(opts.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(API + path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

function login(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  state.tab = "dashboard";
  refreshAll();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.clear();
  render();
}

async function refreshAll() {
  try {
    await Promise.all([loadProviders(), loadSlots(), loadDashboard(),
      state.user.role === "front_desk" ? loadAlerts() : Promise.resolve()]);
  } catch (e) { state.error = e.message; }
  render();
}

async function loadProviders() { state.providers = await api("/users/providers"); }
async function loadDashboard() { state.dashboard = await api("/dashboard"); }
async function loadAlerts() { state.alerts = await api("/alerts"); }

async function loadSlots() {
  const f = state.filters;
  const params = new URLSearchParams();
  if (f.q) params.set("q", f.q);
  if (f.provider_id) params.set("provider_id", f.provider_id);
  if (f.status) params.set("status", f.status);
  if (f.date_from) params.set("date_from", f.date_from);
  if (f.date_to) params.set("date_to", f.date_to);
  params.set("page", state.slots.page);
  params.set("page_size", state.slots.page_size);
  state.slots = await api("/slots?" + params.toString());
}

function providerName(id) {
  const p = state.providers.find(p => p.id === id);
  return p ? p.full_name : id;
}

// ---------- render ----------
function render() {
  const app = document.getElementById("app");
  if (!state.token) { app.innerHTML = renderAuth(); attachAuthHandlers(); return; }

  app.innerHTML = `
    <header>
      <div><strong>Clinic Scheduler</strong> — ${state.user.full_name} (${state.user.role.replace("_"," ")})</div>
      <div><button class="secondary" id="logoutBtn">Log out</button></div>
    </header>
    <nav>
      ${navBtn("dashboard", "Dashboard")}
      ${navBtn("appointments", "Appointments")}
      ${navBtn("new-slot", "New Slot")}
      ${state.user.role === "front_desk" ? navBtn("bulk", "Bulk Generate") : ""}
      ${state.user.role === "front_desk" ? navBtn("alerts", `Alerts ${state.alerts.count ? `<span class="badge">${state.alerts.count}</span>` : ""}`) : ""}
    </nav>
    <main>
      ${state.error ? `<div class="error">${state.error}</div>` : ""}
      ${tabContent()}
    </main>
    ${state.modalSlot ? renderModal() : ""}
  `;
  document.getElementById("logoutBtn").onclick = logout;
  document.querySelectorAll("nav button").forEach(b => b.onclick = () => { state.tab = b.dataset.tab; render(); if (b.dataset.tab === "appointments") loadSlots().then(render); });
  attachTabHandlers();
}

function navBtn(tab, label) {
  return `<button data-tab="${tab}" class="${state.tab === tab ? "active" : ""}">${label}</button>`;
}

function tabContent() {
  if (state.tab === "dashboard") return renderDashboard();
  if (state.tab === "appointments") return renderAppointments();
  if (state.tab === "new-slot") return renderNewSlot();
  if (state.tab === "bulk") return renderBulk();
  if (state.tab === "alerts") return renderAlerts();
  return "";
}

function renderAuth() {
  return `
  <main style="max-width:400px;margin:60px auto;">
    <div class="card">
      <h2>Sign in</h2>
      <form id="loginForm" class="inline" style="flex-direction:column;align-items:stretch;">
        <input name="email" type="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Log in</button>
      </form>
      <p class="error" id="authError"></p>
      <hr>
      <h3>New user? Sign up</h3>
      <form id="signupForm" class="inline" style="flex-direction:column;align-items:stretch;">
        <input name="full_name" placeholder="Full name" required>
        <input name="email" type="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <select name="role">
          <option value="front_desk">Front desk</option>
          <option value="provider">Provider</option>
        </select>
        <button type="submit">Sign up</button>
      </form>
    </div>
  </main>`;
}

function attachAuthHandlers() {
  document.getElementById("loginForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = new URLSearchParams();
    body.set("username", fd.get("email"));
    body.set("password", fd.get("password"));
    try {
      const res = await api("/auth/login", { method: "POST", body });
      login(res.access_token, res.user);
    } catch (err) { document.getElementById("authError").textContent = err.message; }
  };
  document.getElementById("signupForm").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api("/auth/signup", { method: "POST", body: Object.fromEntries(fd) });
      const body = new URLSearchParams();
      body.set("username", fd.get("email"));
      body.set("password", fd.get("password"));
      const res = await api("/auth/login", { method: "POST", body });
      login(res.access_token, res.user);
    } catch (err) { document.getElementById("authError").textContent = err.message; }
  };
}

function renderDashboard() {
  const d = state.dashboard;
  if (!d) return "Loading...";
  return `
    <div class="grid">
      <div class="stat"><div class="num">${d.appointments_today}</div><div class="label">Appointments today</div></div>
      <div class="stat"><div class="num">${d.checked_in_now}</div><div class="label">Checked in now</div></div>
      <div class="stat"><div class="num">${d.no_shows_this_week}</div><div class="label">No-shows this week</div></div>
      <div class="stat"><div class="num">${d.confirmed_upcoming}</div><div class="label">Confirmed upcoming</div></div>
    </div>
    <div class="card">
      <h3>By provider</h3>
      ${Object.entries(d.by_provider).map(([k,v]) => `<div>${k}: ${v}</div>`).join("") || "No data yet"}
    </div>
    <div class="card">
      <h3>By status</h3>
      ${Object.entries(d.by_status).map(([k,v]) => `<span class="status-pill status-${k}">${k}: ${v}</span> `).join("")}
    </div>
    <div class="card">
      <h3>No-show rate, last 8 weeks</h3>
      <table><tr>${d.no_show_rate_weekly.map(w => `<th>${w.week_start}</th>`).join("")}</tr>
      <tr>${d.no_show_rate_weekly.map(w => `<td>${w.no_show_rate}%</td>`).join("")}</tr></table>
    </div>
  `;
}

function renderAppointments() {
  const f = state.filters;
  return `
    <div class="card">
      <form class="inline" id="filterForm">
        <input name="q" placeholder="Patient name" value="${f.q}">
        <select name="provider_id"><option value="">All providers</option>
          ${state.providers.map(p => `<option value="${p.id}" ${f.provider_id===p.id?"selected":""}>${p.full_name}</option>`).join("")}
        </select>
        <select name="status"><option value="">All statuses</option>
          ${["open","requested","confirmed","checked_in","completed","no_show","cancelled"].map(s => `<option value="${s}" ${f.status===s?"selected":""}>${s}</option>`).join("")}
        </select>
        <input name="date_from" type="date" value="${f.date_from}">
        <input name="date_to" type="date" value="${f.date_to}">
        <button type="submit">Filter</button>
        <a href="/slots/export-csv?day=${new Date().toISOString().slice(0,10)}" target="_blank"><button type="button">Export today CSV</button></a>
      </form>
      <table>
        <tr><th>Date</th><th>Time</th><th>Provider</th><th>Patient</th><th>Status</th><th></th></tr>
        ${state.slots.items.map(s => `
          <tr>
            <td>${s.date}</td><td>${s.start_time}</td><td>${s.provider_name}</td>
            <td>${s.patient_name || "-"}</td>
            <td><span class="status-pill status-${s.status}">${s.status}</span></td>
            <td><button class="viewBtn" data-id="${s.id}">View</button></td>
          </tr>`).join("")}
      </table>
      <div style="margin-top:10px;">
        Page ${state.slots.page} — ${state.slots.total} total
        <button class="secondary" id="prevPage" ${state.slots.page<=1?"disabled":""}>Prev</button>
        <button class="secondary" id="nextPage" ${state.slots.page*state.slots.page_size>=state.slots.total?"disabled":""}>Next</button>
      </div>
    </div>
  `;
}

function renderNewSlot() {
  return `
    <div class="card">
      <h3>Create availability slot</h3>
      <form class="inline" id="newSlotForm" style="flex-direction:column;align-items:stretch;max-width:300px;">
        ${state.user.role === "front_desk" ? `
        <label>Provider</label>
        <select name="provider_id" required>${state.providers.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("")}</select>
        ` : `<input type="hidden" name="provider_id" value="${state.user.id}"><div>Provider: you (${state.user.full_name})</div>`}
        <label>Date</label><input name="date" type="date" required>
        <label>Start time</label><input name="start_time" type="time" required>
        <label>Duration (minutes)</label><input name="duration_minutes" type="number" value="30" required>
        <button type="submit">Create slot</button>
      </form>
    </div>
  `;
}

function renderBulk() {
  return `
    <div class="card">
      <h3>Bulk-generate recurring slots</h3>
      <form class="inline" id="bulkForm" style="flex-direction:column;align-items:stretch;max-width:340px;">
        <label>Provider</label>
        <select name="provider_id" required>${state.providers.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("")}</select>
        <label>From</label><input name="date_from" type="date" required>
        <label>To</label><input name="date_to" type="date" required>
        <label>Days of week</label>
        <div>${["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((d,i) => `<label><input type="checkbox" name="dow" value="${i}"> ${d}</label>`).join(" ")}</div>
        <label>Start time</label><input name="start_time" type="time" required>
        <label>Duration (minutes)</label><input name="duration_minutes" type="number" value="30" required>
        <button type="submit">Generate</button>
      </form>
      <div id="bulkResult"></div>
    </div>
  `;
}

function renderAlerts() {
  return `
    <div class="card">
      <h3>Unconfirmed appointments (within 24h)</h3>
      ${state.alerts.alerts.length === 0 ? "<p>No alerts.</p>" : `
      <table>
        <tr><th>Date</th><th>Time</th><th>Provider</th><th>Patient</th><th></th></tr>
        ${state.alerts.alerts.map(s => `
          <tr>
            <td>${s.date}</td><td>${s.start_time}</td><td>${s.provider_name}</td><td>${s.patient_name}</td>
            <td><button class="dismissBtn" data-id="${s.id}">Dismiss</button></td>
          </tr>`).join("")}
      </table>`}
    </div>
  `;
}

function renderModal() {
  const s = state.modalSlot;
  const transitions = {
    open: [], requested: ["confirmed", "cancelled"], confirmed: ["checked_in", "no_show", "cancelled"],
    checked_in: ["completed"], completed: [], no_show: [], cancelled: [],
  }[s.status] || [];
  return `
  <div class="modal-backdrop" id="modalBackdrop">
    <div class="modal">
      <h3>${s.patient_name || "(open slot)"} — <span class="status-pill status-${s.status}">${s.status}</span></h3>
      <p>${s.date} ${s.start_time} · ${s.provider_name} · ${s.duration_minutes} min</p>

      ${s.status === "open" ? `
        <form id="requestForm" class="inline">
          <input name="patient_name" placeholder="Patient name" required>
          <input name="patient_contact" placeholder="Contact">
          <button type="submit">Book / Request</button>
        </form>` : ""}

      <div class="inline">
        ${transitions.map(t => `<button class="statusBtn" data-status="${t}">${t.replace("_"," ")}</button>`).join("")}
      </div>

      <h4>Visit notes</h4>
      ${(s.visit_notes||[]).map(n => `<div class="timeline-item"><b>${n.provider_name}</b> (${new Date(n.created_at).toLocaleString()}): ${n.content}</div>`).join("") || "<p>None yet</p>"}
      ${state.user.role === "provider" ? `
      <form id="noteForm" class="inline">
        <textarea name="content" placeholder="Add a visit note" required style="flex:1;"></textarea>
        <button type="submit">Add note</button>
      </form>` : ""}

      <h4>Care team</h4>
      ${(s.supporting_providers||[]).map(p => `<div>${p.provider_name} ${state.user.role==="front_desk" ? `<button class="removeSupportBtn" data-id="${p.provider_id}">remove</button>`:""}</div>`).join("") || "<p>None</p>"}
      ${state.user.role === "front_desk" ? `
      <form id="supportForm" class="inline">
        <select name="provider_id">${state.providers.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("")}</select>
        <button type="submit">Add supporting provider</button>
      </form>` : ""}

      <h4>Timeline</h4>
      ${(s.timeline||[]).map(e => `<div class="timeline-item">${e.event_type} ${e.old_value?`(${e.old_value} → ${e.new_value})`:""} by ${e.actor_name} ${e.reason?`— "${e.reason}"`:""} · ${new Date(e.created_at).toLocaleString()}</div>`).join("") || "<p>No history</p>"}

      <div style="margin-top:16px;"><button class="secondary" id="closeModal">Close</button></div>
    </div>
  </div>`;
}

function attachTabHandlers() {
  document.querySelectorAll(".viewBtn").forEach(b => b.onclick = async () => {
    state.modalSlot = await api(`/slots/${b.dataset.id}`);
    render();
  });
  const closeBtn = document.getElementById("closeModal");
  if (closeBtn) closeBtn.onclick = () => { state.modalSlot = null; render(); };

  const filterForm = document.getElementById("filterForm");
  if (filterForm) filterForm.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    state.filters = Object.fromEntries(fd);
    state.slots.page = 1;
    await loadSlots(); render();
  };
  const prevPage = document.getElementById("prevPage");
  if (prevPage) prevPage.onclick = async () => { state.slots.page--; await loadSlots(); render(); };
  const nextPage = document.getElementById("nextPage");
  if (nextPage) nextPage.onclick = async () => { state.slots.page++; await loadSlots(); render(); };

  const newSlotForm = document.getElementById("newSlotForm");
  if (newSlotForm) newSlotForm.onsubmit = async (e) => {
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target));
    fd.duration_minutes = parseInt(fd.duration_minutes);
    try { await api("/slots", { method: "POST", body: fd }); alert("Slot created"); e.target.reset(); }
    catch (err) { alert(err.message); }
  };

  const bulkForm = document.getElementById("bulkForm");
  if (bulkForm) bulkForm.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const dow = fd.getAll("dow").map(Number);
    const body = {
      provider_id: fd.get("provider_id"), date_from: fd.get("date_from"), date_to: fd.get("date_to"),
      days_of_week: dow, start_time: fd.get("start_time"), duration_minutes: parseInt(fd.get("duration_minutes")),
    };
    try {
      const res = await api("/slots/bulk-generate", { method: "POST", body });
      document.getElementById("bulkResult").innerHTML = `<p>Created: ${res.created.length}, Skipped (collisions): ${res.skipped.length}</p>`;
    } catch (err) { alert(err.message); }
  };

  document.querySelectorAll(".dismissBtn").forEach(b => b.onclick = async () => {
    await api(`/alerts/${b.dataset.id}/dismiss`, { method: "POST" });
    await loadAlerts(); render();
  });

  const requestForm = document.getElementById("requestForm");
  if (requestForm) requestForm.onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    try {
      state.modalSlot = await api(`/slots/${state.modalSlot.id}/request`, { method: "POST", body });
      state.modalSlot = await api(`/slots/${state.modalSlot.id}`);
      await loadSlots(); render();
    } catch (err) { alert(err.message); }
  };

  document.querySelectorAll(".statusBtn").forEach(b => b.onclick = async () => {
    let reason = null;
    if (b.dataset.status === "cancelled") reason = prompt("Cancellation reason (required):");
    if (b.dataset.status === "cancelled" && !reason) return;
    try {
      await api(`/slots/${state.modalSlot.id}/status`, { method: "POST", body: { new_status: b.dataset.status, reason } });
      state.modalSlot = await api(`/slots/${state.modalSlot.id}`);
      await loadSlots(); render();
    } catch (err) { alert(err.message); }
  });

  const noteForm = document.getElementById("noteForm");
  if (noteForm) noteForm.onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    await api(`/slots/${state.modalSlot.id}/visit-notes`, { method: "POST", body });
    state.modalSlot = await api(`/slots/${state.modalSlot.id}`); render();
  };

  const supportForm = document.getElementById("supportForm");
  if (supportForm) supportForm.onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    await api(`/slots/${state.modalSlot.id}/care-team`, { method: "POST", body });
    state.modalSlot = await api(`/slots/${state.modalSlot.id}`); render();
  };

  document.querySelectorAll(".removeSupportBtn").forEach(b => b.onclick = async () => {
    await api(`/slots/${state.modalSlot.id}/care-team/${b.dataset.id}`, { method: "DELETE" });
    state.modalSlot = await api(`/slots/${state.modalSlot.id}`); render();
  });
}

if (state.token) refreshAll(); else render();
