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

/* ----- Toast utility ----- */
function showToast(message, type = "") {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`.trim();
  
  let icon = "";
  if (type === "success") icon = "✓ ";
  else if (type === "error") icon = "✗ ";
  else if (type === "warning") icon = "⚠ ";

  el.textContent = icon + message;
  root.appendChild(el);
  
  setTimeout(() => {
    el.style.opacity = "1";
    el.style.transform = "translateY(0)";
  }, 10);

  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(10px)";
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

/* ----- Confirm dialog utility (returns Promise<boolean>) ----- */
function confirmDialog(message) {
  return new Promise((resolve) => {
    const root = document.getElementById("modal-root");
    if (!root) return resolve(window.confirm(message));

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-body">
          <p>${message}</p>
        </div>
        <div class="actions">
          <button class="ghost-btn cancel">Cancel</button>
          <button class="danger-btn confirm">Delete</button>
        </div>
      </div>
    `;

    root.appendChild(overlay);

    const cleanup = (result) => {
      overlay.remove();
      resolve(result);
    };

    overlay.querySelector(".cancel").addEventListener("click", () => cleanup(false));
    overlay.querySelector(".confirm").addEventListener("click", () => cleanup(true));
  });
}

// Attach globally
window.showToast = showToast;
window.confirmDialog = confirmDialog;

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
    document.body.className = "logged-out";
    return;
  }

  elements.welcomeTitle.textContent = `Welcome, ${user.full_name}`;
  elements.roleBadge.textContent = user.role;
  elements.roleBadge.className = `role-badge role-${user.role.toLowerCase()}`;
  elements.tokenState.textContent = `Signed in as ${user.email}`;
  elements.adminSection.classList.toggle("hidden", user.role !== "admin");
  document.body.className = "logged-in";
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
    showToast(data.detail || "Authentication failed", "error");
    return;
  }

  setAccessToken(data.access_token);
  updateUiForUser(data.user);
  showToast(
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
    elements.tasksList.innerHTML = `<div class="item text-center"><strong>Log in to manage tasks.</strong></div>`;
    return;
  }

  // Show high-quality dark skeletons while loading
  elements.tasksList.innerHTML = Array.from({ length: 3 })
    .map(
      () => `
      <div class="item skeleton-card">
        <div class="skeleton text title-skeleton"></div>
        <div class="skeleton text desc-skeleton"></div>
        <div class="skeleton button-skeleton"></div>
      </div>
    `
    )
    .join("");

  const params = new URLSearchParams();
  const query = elements.searchInput.value.trim();
  const status = elements.statusFilter.value;
  if (query) params.set("q", query);
  if (status) params.set("status", status);

  const response = await apiFetch(`/tasks?${params.toString()}`);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    elements.tasksList.innerHTML = `<div class="item error-message"><strong>${data.detail || "Unable to load tasks"}</strong></div>`;
    return;
  }

  if (!data.items.length) {
    elements.tasksList.innerHTML = `
      <div class="empty-state">
        <svg class="empty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="15" x2="15" y2="15"></line></svg>
        <strong>No tasks found</strong>
        <span class="muted">Add a new task using the form on the left.</span>
      </div>
    `;
    return;
  }

  elements.tasksList.innerHTML = data.items.map(renderTask).join("");
  bindTaskActions();
}

function renderTask(task) {
  const statusClasses = {
    pending: "status-pending",
    in_progress: "status-inprogress",
    completed: "status-completed",
  };
  const statusClass = statusClasses[task.status] || "";

  return `
    <article class="item" data-task-id="${task.id}">
      <!-- View mode -->
      <div class="view-mode">
        <div class="item-top">
          <div class="item-text">
            <h3 class="task-title-text">${escapeHtml(task.title)}</h3>
            <p class="task-desc-text muted">${escapeHtml(task.description || "No description")}</p>
          </div>
          <div class="status-badge-container">
            <select class="status-select-badge ${statusClass}" data-task-id="${task.id}">
              <option value="pending" ${task.status === "pending" ? "selected" : ""}>Pending</option>
              <option value="in_progress" ${task.status === "in_progress" ? "selected" : ""}>In Progress</option>
              <option value="completed" ${task.status === "completed" ? "selected" : ""}>Completed</option>
            </select>
          </div>
        </div>
        <div class="item-actions">
          <button type="button" class="ghost-btn edit-task-btn">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
            Edit
          </button>
          <button type="button" class="danger-btn delete-task">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            Delete
          </button>
        </div>
      </div>

      <!-- Edit mode (initially hidden) -->
      <div class="edit-mode hidden">
        <div class="edit-form-fields">
          <div class="form-group">
            <label class="field-label">Title</label>
            <input type="text" class="edit-title-input" value="${escapeHtml(task.title)}" required />
          </div>
          <div class="form-group">
            <label class="field-label">Description</label>
            <textarea class="edit-desc-input" rows="2">${escapeHtml(task.description || "")}</textarea>
          </div>
        </div>
        <div class="item-actions edit-actions">
          <button type="button" class="primary save-task-btn">Save</button>
          <button type="button" class="ghost-btn cancel-edit-btn">Cancel</button>
        </div>
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
  // Bind Edit button click (switch to Edit Mode inline)
  document.querySelectorAll(".edit-task-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      const card = event.target.closest("[data-task-id]");
      card.querySelector(".view-mode").classList.add("hidden");
      card.querySelector(".edit-mode").classList.remove("hidden");
    });
  });

  // Bind Cancel button click (switch back to View Mode)
  document.querySelectorAll(".cancel-edit-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      const card = event.target.closest("[data-task-id]");
      card.querySelector(".edit-mode").classList.add("hidden");
      card.querySelector(".view-mode").classList.remove("hidden");
      
      // Reset inputs to original values
      const titleInput = card.querySelector(".edit-title-input");
      const descInput = card.querySelector(".edit-desc-input");
      const titleText = card.querySelector(".task-title-text").textContent;
      const descText = card.querySelector(".task-desc-text").textContent;
      
      titleInput.value = titleText;
      descInput.value = descText === "No description" ? "" : descText;
    });
  });

  // Bind Save button click (submit updates and reload list)
  document.querySelectorAll(".save-task-btn").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const card = event.target.closest("[data-task-id]");
      const taskId = card.dataset.taskId;
      const title = card.querySelector(".edit-title-input").value.trim();
      const description = card.querySelector(".edit-desc-input").value.trim();

      if (title.length < 3) {
        showToast("Title must be at least 3 characters", "error");
        return;
      }

      const response = await apiFetch(`/tasks/${taskId}`, {
        method: "PUT",
        body: JSON.stringify({
          title,
          description: description || null,
        }),
      });

      if (response.ok) {
        showToast("Task updated successfully", "success");
        await loadTasks();
      } else {
        const data = await response.json().catch(() => ({}));
        showToast(data.detail || "Failed to update task", "error");
      }
    });
  });

  // Bind inline status pill change (immediate action)
  document.querySelectorAll(".status-select-badge").forEach((select) => {
    select.addEventListener("change", async (event) => {
      const selectEl = event.target;
      const taskId = selectEl.dataset.taskId;
      const newStatus = selectEl.value;

      const response = await apiFetch(`/tasks/${taskId}`, {
        method: "PUT",
        body: JSON.stringify({
          status: newStatus,
        }),
      });

      if (response.ok) {
        showToast(`Status updated to ${newStatus.replace("_", " ")}`, "success");
        await loadTasks();
      } else {
        const data = await response.json().catch(() => ({}));
        showToast(data.detail || "Failed to update status", "error");
        await loadTasks(); // Revert back on failure
      }
    });
  });

  // Bind Delete button click (utilize confirmDialog modal)
  document.querySelectorAll(".delete-task").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const taskId = event.target.closest("[data-task-id]").dataset.taskId;
      const ok = await confirmDialog("Are you sure you want to delete this task?");
      if (!ok) return;
      
      const response = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
      if (response.ok) {
        showToast("Task deleted successfully", "success");
        await loadTasks();
      } else {
        const data = await response.json().catch(() => ({}));
        showToast(data.detail || "Failed to delete task", "error");
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
    showToast(data.detail || "Task creation failed", "error");
    return;
  }

  showToast("Task created successfully", "success");
  elements.taskForm.reset();
  await loadTasks();
}

async function loadUsers() {
  const response = await apiFetch("/admin/users");
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    elements.usersList.innerHTML = `<div class="item error-message"><strong>${data.detail || "Unable to load users"}</strong></div>`;
    return;
  }

  elements.usersList.innerHTML = data.items
    .map(
      (user) =>
        `<div class="item user-item">
          <div class="user-meta">
            <strong>${escapeHtml(user.full_name)}</strong>
            <span class="muted">${escapeHtml(user.email)}</span>
          </div>
          <span class="role-badge role-${user.role.toLowerCase()}">${escapeHtml(user.role)}</span>
        </div>`,
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
  showToast("Logged out successfully", "success");
  elements.tasksList.innerHTML = "";
  elements.usersList.innerHTML = "";
}

// Form and filter event listeners
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

// Initialize UI Mode
toggleMode("login");
elements.fullName.parentElement.style.display = "none";

// Bootstrap session on load
bootstrapSession().then(async () => {
  if (getAccessToken()) {
    await loadTasks();
    if (currentUser?.role === "admin") {
      await loadUsers();
    }
  }
});
