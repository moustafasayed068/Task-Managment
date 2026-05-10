let token = null;
const API_BASE = "http://127.0.0.1:8000";

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
            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('main-app').style.display = 'block';
            loadProjects();
            loadTasks();
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

// ==================== PROJECTS ====================
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
            loadProjects();
        } else {
            alert("Failed to create project");
        }
    } catch (e) { alert("Error creating project"); }
}

async function loadProjects() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/projects/`, { headers: getHeaders() });
        const projects = await res.json();

        let html = '';
        projects.forEach(p => {
            html += `
                <div class="project">
                    <strong>${p.name}</strong> (ID: ${p.id})<br>
                    ${p.description || ''}
                    <button onclick="deleteProject(${p.id})" class="btn-danger" style="font-size:0.85rem; padding:6px 12px; margin-top:8px;">
                        🗑 Delete
                    </button>
                </div>`;
        });
        document.getElementById('projects-list').innerHTML = html || '<p>No projects found.</p>';
    } catch (e) {
        document.getElementById('projects-list').innerHTML = '<p style="color:red">Error loading projects</p>';
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
            loadProjects();
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
async function createTask() {
    const title = document.getElementById('task-title').value.trim();
    if (!title) return alert("Task title is required");

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/tasks/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                title: title,
                description: document.getElementById('task-desc').value,
                status: document.getElementById('task-status').value,
                project_id: parseInt(document.getElementById('project-id').value) || 1,
                assignee_id: 1
            })
        });
        if (res.ok) {
            alert("✅ Task Created!");
            loadTasks();
        }
    } catch (e) { alert("Error creating task"); }
}

async function loadTasks() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/tasks/`, { headers: getHeaders() });
        const tasks = await res.json();

        let html = '';
        tasks.forEach(t => {
            html += `
                <div class="task">
                    <strong>${t.title}</strong> - <span style="color:#22d3ee">${t.status}</span><br>
                    ${t.description || ''}
                    <button onclick="updateTaskStatus(${t.id}, 'in_progress')" style="background:#f59e0b">In Progress</button>
                    <button onclick="updateTaskStatus(${t.id}, 'done')" style="background:#10b981">Done</button>
                    <button onclick="deleteTask(${t.id})" class="btn-danger" style="font-size:0.85rem;">🗑 Delete</button>
                </div>`;
        });
        document.getElementById('tasks-list').innerHTML = html || '<p>No tasks found.</p>';
    } catch (e) {
        document.getElementById('tasks-list').innerHTML = '<p style="color:red">Error loading tasks</p>';
    }
}

async function updateTaskStatus(id, newStatus) {
    try {
        await fetch(`${API_BASE}/api/v1/v2/tasks/${id}`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify({ status: newStatus })
        });
        loadTasks();
    } catch (e) {
        alert("Failed to update task");
    }
}

async function deleteTask(id) {
    if (!confirm("Delete this task?")) return;
    try {
        await fetch(`${API_BASE}/api/v1/v2/tasks/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        loadTasks();
    } catch (e) {
        alert("Failed to delete task");
    }
}

function logout() {
    token = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-app').style.display = 'none';
}