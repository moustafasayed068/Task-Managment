let token = null;

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const messageEl = document.getElementById('auth-message');

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
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
            messageEl.textContent = data.detail || 'Login failed!';
        }
    } catch (error) {
        messageEl.textContent = 'Cannot connect to server. Is backend running?';
    }
}

function getHeaders() {
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

async function loadProjects() {
    const res = await fetch('http://127.0.0.1:8000/api/v1/projects', {
        headers: getHeaders()
    });
    const projects = await res.json();

    const html = projects.map(p => `
    <div class="project">
      <strong>${p.name}</strong><br>
      ${p.description || ''}
    </div>
  `).join('');

    document.getElementById('projects-list').innerHTML = html || '<p>No projects found.</p>';
}

async function loadTasks() {
    const res = await fetch('http://127.0.0.1:8000/api/v1/v2/tasks', {
        headers: getHeaders()
    });
    const tasks = await res.json();

    const html = tasks.map(t => `
    <div class="task">
      <strong>${t.title}</strong> - <span style="color: #007bff;">${t.status}</span><br>
      ${t.description || ''}
    </div>
  `).join('');

    document.getElementById('tasks-list').innerHTML = html || '<p>No tasks found.</p>';
}

function logout() {
    token = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-app').style.display = 'none';
}