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
    const name = document.getElementById('proj-name').value;
    if (!name) return alert("Project name is required");

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/projects/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ name, description: document.getElementById('proj-desc').value })
        });
        if (res.ok) {
            alert("Project Created!");
            loadProjects();
        }
    } catch (e) { alert("Error creating project"); }
}

async function loadProjects() {
    const res = await fetch(`${API_BASE}/api/v1/v2/projects/`, { headers: getHeaders() });
    const projects = await res.json();
    let html = '';
    projects.forEach(p => {
        html += `
            <div class="project">
                <strong>${p.name}</strong> (ID: ${p.id})<br>
                ${p.description || ''}
                <button onclick="deleteProject(${p.id})" style="background:#ef4444; font-size:0.8rem;">Delete</button>
            </div>`;
    });
    document.getElementById('projects-list').innerHTML = html || '<p>No projects found.</p>';
}

async function deleteProject(id) {
    if (!confirm("⚠️ Delete this project and all its tasks?")) return;

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/projects/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });

        if (res.ok) {
            alert("✅ Project deleted successfully");
            loadProjects();
        } else {
            alert("Failed to delete project (Check if it has tasks)");
        }
    } catch (e) {
        alert("Error deleting project");
    }
}
// ==================== TASKS ====================
async function createTask() {
    const title = document.getElementById('task-title').value;
    if (!title) return alert("Task title is required");

    try {
        const res = await fetch(`${API_BASE}/api/v1/v2/tasks/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                title: title,
                description: document.getElementById('task-desc').value,
                status: document.getElementById('task-status').value,
                project_id: parseInt(document.getElementById('project-id').value),
                assignee_id: 1
            })
        });
        if (res.ok) {
            alert("Task Created!");
            loadTasks();
        }
    } catch (e) { alert("Error creating task"); }
}

async function loadTasks() {
    const res = await fetch(`${API_BASE}/api/v1/v2/tasks/`, { headers: getHeaders() });
    const tasks = await res.json();
    let html = '';
    tasks.forEach(t => {
        html += `
            <div class="task">
                <strong>${t.title}</strong> - <span style="color:#22d3ee">${t.status}</span><br>
                ${t.description || ''}
                <button onclick="updateTaskStatus(${t.id}, 'in_progress')">In Progress</button>
                <button onclick="updateTaskStatus(${t.id}, 'done')">Done</button>
                <button onclick="deleteTask(${t.id})" style="background:#ef4444;">Delete</button>
            </div>`;
    });
    document.getElementById('tasks-list').innerHTML = html || '<p>No tasks found.</p>';
}

async function updateTaskStatus(id, newStatus) {
    await fetch(`${API_BASE}/api/v1/v2/tasks/${id}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({ status: newStatus })
    });
    loadTasks();
}

async function deleteTask(id) {
    if (!confirm("Delete this task?")) return;
    await fetch(`${API_BASE}/api/v1/v2/tasks/${id}`, {
        method: 'DELETE',
        headers: getHeaders()
    });
    loadTasks();
}

function logout() {
    token = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-app').style.display = 'none';
}