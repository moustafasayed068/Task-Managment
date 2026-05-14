let token = null;
let currentUser = null;
let isLoginMode = true;
const hostname = window.location.hostname || "127.0.0.1";
const API_BASE = `http://${hostname}:8000`;

function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    const title = document.getElementById('auth-title');
    const email = document.getElementById('email');
    const btn = document.getElementById('auth-btn');
    const toggle = document.getElementById('toggle-auth');
    
    if (isLoginMode) {
        title.innerText = "🔑 Welcome Back";
        email.style.display = "none";
        btn.innerText = "Login";
        btn.onclick = login;
        toggle.innerText = "Don't have an account? Register";
    } else {
        title.innerText = "📝 Create Account";
        email.style.display = "block";
        btn.innerText = "Register";
        btn.onclick = register;
        toggle.innerText = "Already have an account? Login";
    }
}

async function register() {
    const message = document.getElementById('auth-message');
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !email || !password) {
        message.textContent = "Please fill all fields";
        message.style.color = "red";
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        const data = await res.json();

        if (res.ok) {
            alert("Registration successful! Please login.");
            toggleAuthMode();
        } else {
            message.textContent = data.detail || "Registration failed";
            message.style.color = "red";
        }
    } catch (err) {
        message.textContent = "Cannot connect to backend";
    }
}

async function login() {
    const message = document.getElementById('auth-message');
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            token = data.access_token;
            
            // Get current user details
            const meRes = await fetch(`${API_BASE}/api/v1/auth/me`, { headers: getHeaders() });
            if (meRes.ok) {
                currentUser = await meRes.json();
            } else {
                currentUser = { id: 1 }; // fallback
            }

            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('main-app').style.display = 'block';
            
            // Only show Create Project card for admins
            const createProjCard = document.querySelector('.colorful-card');
            if (createProjCard) {
                createProjCard.style.display = (currentUser.role === 'admin') ? 'block' : 'none';
            }

            loadProjectsAndTasks(true);
        } else {
            message.textContent = data.detail || "Login failed";
            message.style.color = "red";
        }
    } catch (err) {
        message.textContent = "Cannot connect to backend";
    }
}

function getHeaders() {
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// ==================== PROJECTS & TASKS ====================
async function createProject() {
    const name = document.getElementById('proj-name').value.trim();
    if (!name) return alert("Project name is required");

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/projects/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                name,
                description: document.getElementById('proj-desc').value
            })
        });
        if (res.ok) {
            alert("✅ Project Created!");
            loadProjectsAndTasks(true);
        } else {
            alert("Failed to create project");
        }
    } catch (e) { alert("Error creating project"); }
}

async function loadProjectsAndTasks() {
    const listEl = document.getElementById('projects-list');
    
    try {
        const [projRes, taskRes] = await Promise.all([
            fetch(`${API_BASE}/api/v1/v2/projects/`, { headers: getHeaders() }),
            fetch(`${API_BASE}/api/v1/v2/tasks/`, { headers: getHeaders() })
        ]);
        
        const projects = await projRes.json();
        const tasks = await taskRes.json();

        let html = '';
        projects.forEach(p => {
            const projectTasks = tasks.filter(t => t.project_id === p.id);
            
            let tasksHtml = '<div style="margin-top: 15px; border-top: 1px solid #334155; padding-top: 10px;"><h4>📋 Tasks:</h4>';
            
            if (projectTasks.length === 0) {
                tasksHtml += '<p style="font-size: 0.85rem; color: #94a3b8;">No tasks in this project.</p>';
            } else {
                projectTasks.forEach(t => {
                    const statusColor = t.status === 'done' ? '#10b981' : (t.status === 'in_progress' ? '#f59e0b' : '#3b82f6');
                    
                    let taskControls = '';
                    
                    // Status updates (only the assignee can progress their tasks)
                    if (currentUser && currentUser.id === t.assignee_id) {
                        if (t.status === 'todo') {
                            taskControls += `<button onclick="updateTaskStatus(${t.id}, 'in_progress', this)" style="background:#f59e0b; padding:4px 8px; font-size:0.75rem;">▶ Start</button>`;
                        } else if (t.status === 'in_progress') {
                            taskControls += `<button onclick="updateTaskStatus(${t.id}, 'done', this)" style="background:#10b981; padding:4px 8px; font-size:0.75rem;">✓ Complete</button>`;
                        }
                    }

                    // Admin controls
                    if (currentUser && currentUser.role === 'admin') {
                         taskControls += `<button onclick="deleteTask(${t.id})" class="btn-danger" style="padding:4px 8px; font-size:0.75rem; margin-left: 5px;">🗑</button>`;
                    }

                    tasksHtml += `
                        <div style="background: #1e293b; padding: 10px; margin-bottom: 5px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${t.title}</strong> 
                                <span style="font-size: 0.75rem; background: ${statusColor}; padding: 2px 6px; border-radius: 12px; margin-left: 5px;">${t.status}</span>
                                <div style="font-size: 0.8rem; color: #94a3b8;">${t.description || ''}</div>
                            </div>
                            <div>
                                ${taskControls}
                            </div>
                        </div>
                    `;
                });
            }
            tasksHtml += '</div>';

            let projControls = '';
            // Only admin or PM can add tasks. Only admin can delete projects.
            if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'project_manager')) {
                projControls += `<button onclick="promptCreateTask(${p.id})" class="btn-success" style="font-size:0.85rem; padding:6px 12px;">➕ Add Task</button>`;
            }
            if (currentUser && currentUser.role === 'admin') {
                projControls += `<button onclick="deleteProject(${p.id})" class="btn-danger" style="font-size:0.85rem; padding:6px 12px; margin-left: 5px;">🗑 Delete</button>`;
            }

            html += `
                <div class="project" style="margin-bottom: 20px;">
                    <strong>${p.name}</strong> (ID: ${p.id})<br>
                    <span style="color: #cbd5e1; font-size: 0.9rem;">${p.description || ''}</span>
                    <div style="margin-top: 10px; margin-bottom: 10px;">
                        ${projControls}
                    </div>
                    ${tasksHtml}
                </div>`;
        });
        listEl.innerHTML = html || '<p>No projects found.</p>';
    } catch (e) {
        document.getElementById('projects-list').innerHTML = '<p style="color:red">Error loading data</p>';
    }
}

async function deleteProject(id) {
    if (!confirm("Delete this project?\n\nWarning: This will also delete all tasks inside it!"))
        return;

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/projects/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });

        console.log("Project Delete Status:", res.status);   // For debugging

        if (res.ok) {
            alert("✅ Project deleted successfully!");
            loadProjectsAndTasks();
        } else if (res.status === 403) {
            alert("❌ Permission Denied!\nYou need to be logged in as **Admin** to delete projects.");
        } else if (res.status === 409) {
            alert("❌ Cannot delete project because it contains tasks.\nDelete the tasks first.");
        } else {
            const error = await res.json().catch(() => ({}));
            alert("Delete failed: " + (error.detail || res.status));
        }
    } catch (e) {
        console.error(e);
        alert("Connection error. Make sure backend is running and you opened frontend via http://localhost:5500");
    }
}

// ==================== TASKS ====================
let activeProjectId = null;
let systemUsers = [];

async function loadSystemUsers() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/users/`, { headers: getHeaders() });
        if (res.ok) {
            systemUsers = await res.json();
            const select = document.getElementById('modal-task-assignee');
            select.innerHTML = '';
            systemUsers.forEach(u => {
                select.innerHTML += `<option value="${u.id}">${u.username} (${u.role})</option>`;
            });
        }
    } catch (e) {
        console.error("Failed to load users for dropdown");
    }
}

async function promptCreateTask(projectId) {
    activeProjectId = projectId;
    const modal = document.getElementById('task-modal');
    document.getElementById('modal-task-title').value = '';
    document.getElementById('modal-task-desc').value = '';
    
    // Load users if empty
    if (systemUsers.length === 0) {
        await loadSystemUsers();
    }
    
    modal.showModal();
}

function closeTaskModal() {
    const modal = document.getElementById('task-modal');
    modal.close();
    activeProjectId = null;
}

async function submitTaskModal() {
    const title = document.getElementById('modal-task-title').value.trim();
    if (!title) {
        alert("Enter a task title");
        return;
    }
    const description = document.getElementById('modal-task-desc').value.trim();
    const assignee_id = parseInt(document.getElementById('modal-task-assignee').value);

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/tasks/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                title: title,
                description: description,
                status: "todo",
                priority: "medium",
                project_id: activeProjectId,
                assignee_id: assignee_id || currentUser.id
            })
        });
        if (res.ok) {
            alert("✅ Task Created!");
            closeTaskModal();
            loadProjectsAndTasks();
        } else {
            const err = await res.json().catch(() => ({}));
            alert("Failed to create task: " + (err.detail || ""));
        }
    } catch (e) { alert("Error creating task"); }
}

async function updateTaskStatus(id, newStatus, btn) {
    if (btn) {
        btn.disabled = true;
        btn.innerText = "⏳...";
    }
    try {
        await fetch(`${API_BASE}/api/v1/v2/tasks/${id}`, {
            method: 'PATCH',
            headers: getHeaders(),
            body: JSON.stringify({ status: newStatus })
        });
        loadProjectsAndTasks(false);
    } catch (e) {
        alert("Failed to update task");
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Retry";
        }
    }
}

async function deleteTask(id) {
    if (!confirm("Delete this task?")) return;
    try {
        await fetch(`${API_BASE}/api/v1/v2/tasks/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        loadProjectsAndTasks();
    } catch (e) {
        alert("Failed to delete task");
    }
}

function logout() {
    token = null;
    currentUser = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-app').style.display = 'none';
}