const API_BASE = "/api/v1";
const ACCESS_TOKEN_KEY = "primetrade_access_token";

const elements = {
  authForm: document.getElementById("authForm"),
  authMessage: document.getElementById("authMessage"),
  showLogin: document.getElementById("showLogin"),
  showRegister: document.getElementById("showRegister"),
  email: document.getElementById("email"),
  fullName: document.getElementById("fullName"),
  password: document.getElementById("password"),
  welcomeTitle: document.getElementById("welcomeTitle"),
  roleBadge: document.getElementById("roleBadge"),
  tokenState: document.getElementById("tokenState"),
  logoutBtn: document.getElementById("logoutBtn"),
  taskForm: document.getElementById("taskForm"),
  taskTitle: document.getElementById("taskTitle"),
  taskDescription: document.getElementById("taskDescription"),
  taskStatus: document.getElementById("taskStatus"),
  tasksList: document.getElementById("tasksList"),
  searchInput: document.getElementById("searchInput"),
  statusFilter: document.getElementById("statusFilter"),
  refreshTasks: document.getElementById("refreshTasks"),
  adminSection: document.getElementById("adminSection"),
  loadUsersBtn: document.getElementById("loadUsersBtn"),
  usersList: document.getElementById("usersList"),
};

let mode = "login";
let currentUser = null;

function setMessage(text, type = "") {
  elements.authMessage.textContent = text;
  elements.authMessage.className = `message ${type}`.trim();
}

function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

function setAccessToken(token) {
  if (!token) {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    return;
  }
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

function updateUiForUser(user) {
  currentUser = user;
  if (!user) {
    elements.welcomeTitle.textContent = "Not signed in";
    elements.roleBadge.textContent = "guest";
    elements.tokenState.textContent = "No access token loaded";
    elements.adminSection.classList.add("hidden");
    return;
  }

  elements.welcomeTitle.textContent = `Welcome, ${user.full_name}`;
  elements.roleBadge.textContent = user.role;
  elements.tokenState.textContent = `Signed in as ${user.email}`;
  elements.adminSection.classList.toggle("hidden", user.role !== "admin");
}

function toggleMode(nextMode) {
  mode = nextMode;
  elements.showLogin.classList.toggle("active", mode === "login");
  elements.showRegister.classList.toggle("active", mode === "register");
  elements.fullName.parentElement.style.display =
    mode === "register" ? "grid" : "none";
  elements.authForm.querySelector("button[type='submit']").textContent =
    mode === "register" ? "Create account" : "Log in";
  setMessage("");
}

async function apiFetch(path, options = {}, retrying = false) {
  const headers = { ...(options.headers || {}) };
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && token && !retrying) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return apiFetch(path, options, true);
    }
  }

  return response;
}

async function refreshSession() {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    setAccessToken(null);
    updateUiForUser(null);
    return false;
  }

  const data = await response.json();
  setAccessToken(data.access_token);
  updateUiForUser(data.user);
  return true;
}

async function bootstrapSession() {
  const token = getAccessToken();
  if (token) {
    try {
      const meResponse = await apiFetch("/auth/me");
      if (meResponse.ok) {
        updateUiForUser(await meResponse.json());
        return;
      }
    } catch (error) {
      console.error(error);
    }
  }

  await refreshSession();
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
  const payload = {
    email: elements.email.value.trim(),
    password: elements.password.value,
  };

  if (mode === "register") {
    payload.full_name = elements.fullName.value.trim();
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    setMessage(data.detail || "Authentication failed", "error");
    return;
  }

  setAccessToken(data.access_token);
  updateUiForUser(data.user);
  setMessage(
    mode === "register"
      ? "Account created successfully"
      : "Logged in successfully",
    "success",
  );
  elements.authForm.reset();
  elements.fullName.parentElement.style.display = "none";
  await loadTasks();
  if (data.user.role === "admin") {
    await loadUsers();
  }
}

async function loadTasks() {
  if (!getAccessToken()) {
    elements.tasksList.innerHTML = `<div class="item"><strong>Log in to manage tasks.</strong></div>`;
    return;
  }

  const params = new URLSearchParams();
  const query = elements.searchInput.value.trim();
  const status = elements.statusFilter.value;
  if (query) params.set("q", query);
  if (status) params.set("status", status);

  const response = await apiFetch(`/tasks?${params.toString()}`);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    elements.tasksList.innerHTML = `<div class="item"><strong>${data.detail || "Unable to load tasks"}</strong></div>`;
    return;
  }

  if (!data.items.length) {
    elements.tasksList.innerHTML = `<div class="item"><strong>No tasks yet.</strong><span class="muted">Create the first one above.</span></div>`;
    return;
  }

  elements.tasksList.innerHTML = data.items.map(renderTask).join("");
  bindTaskActions();
}

function renderTask(task) {
  return `
    <article class="item" data-task-id="${task.id}">
      <div class="item-top">
        <div>
          <h3>${escapeHtml(task.title)}</h3>
          <p class="muted">${escapeHtml(task.description || "No description")}</p>
        </div>
        <span class="badge">${task.status}</span>
      </div>
      <div class="item-actions">
        <button type="button" class="ghost edit-task">Edit</button>
        <button type="button" class="ghost delete-task">Delete</button>
      </div>
    </article>
  `;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function bindTaskActions() {
  document.querySelectorAll(".edit-task").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const taskId = event.target.closest("[data-task-id]").dataset.taskId;
      const newTitle = window.prompt("Task title");
      if (!newTitle) return;
      const newStatus = window.prompt(
        "Status: pending, in_progress, or completed",
        "pending",
      );
      if (!newStatus) return;

      const response = await apiFetch(`/tasks/${taskId}`, {
        method: "PUT",
        body: JSON.stringify({ title: newTitle, status: newStatus }),
      });
      if (response.ok) {
        await loadTasks();
      }
    });
  });

  document.querySelectorAll(".delete-task").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const taskId = event.target.closest("[data-task-id]").dataset.taskId;
      if (!window.confirm("Delete this task?")) return;
      const response = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
      if (response.ok) {
        await loadTasks();
      }
    });
  });
}

async function handleTaskSubmit(event) {
  event.preventDefault();
  const response = await apiFetch("/tasks", {
    method: "POST",
    body: JSON.stringify({
      title: elements.taskTitle.value.trim(),
      description: elements.taskDescription.value.trim() || null,
      status: elements.taskStatus.value,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    setMessage(data.detail || "Task creation failed", "error");
    return;
  }

  elements.taskForm.reset();
  await loadTasks();
}

async function loadUsers() {
  const response = await apiFetch("/admin/users");
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    elements.usersList.innerHTML = `<div class="item"><strong>${data.detail || "Unable to load users"}</strong></div>`;
    return;
  }

  elements.usersList.innerHTML = data.items
    .map(
      (user) =>
        `<div class="item"><strong>${escapeHtml(user.full_name)}</strong><span class="muted">${escapeHtml(user.email)} · ${escapeHtml(user.role)}</span></div>`,
    )
    .join("");
}

async function handleLogout() {
  await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  setAccessToken(null);
  updateUiForUser(null);
  setMessage("Logged out", "success");
  elements.tasksList.innerHTML = "";
  elements.usersList.innerHTML = "";
}

elements.showLogin.addEventListener("click", () => toggleMode("login"));
elements.showRegister.addEventListener("click", () => toggleMode("register"));
elements.authForm.addEventListener("submit", handleAuthSubmit);
elements.taskForm.addEventListener("submit", handleTaskSubmit);
elements.refreshTasks.addEventListener("click", loadTasks);
elements.searchInput.addEventListener(
  "input",
  () =>
    clearTimeout(window.taskSearchTimer) ||
    (window.taskSearchTimer = setTimeout(loadTasks, 250)),
);
elements.statusFilter.addEventListener("change", loadTasks);
elements.logoutBtn.addEventListener("click", handleLogout);
elements.loadUsersBtn.addEventListener("click", loadUsers);

toggleMode("login");
elements.fullName.parentElement.style.display = "none";

bootstrapSession().then(async () => {
  if (getAccessToken()) {
    await loadTasks();
    if (currentUser?.role === "admin") {
      await loadUsers();
    }
  }
});
