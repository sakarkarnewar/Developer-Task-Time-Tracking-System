// DevTracker Frontend Controller
let activeTimer = null;
let timerInterval = null;
let currentRange = 'week';

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  fetchActiveTimer();
  fetchTasks();
  fetchReport(currentRange);

  // Poll for active timer every 10s to sync
  setInterval(fetchActiveTimer, 10000);
});

function initEventListeners() {
  // Modal toggle
  const modal = document.getElementById('task-modal');
  document.getElementById('open-task-modal-btn').addEventListener('click', () => {
    modal.classList.remove('hidden');
    document.getElementById('task-title').focus();
  });
  document.getElementById('close-task-modal').addEventListener('click', () => modal.classList.add('hidden'));
  document.getElementById('cancel-task-btn').addEventListener('click', () => modal.classList.add('hidden'));

  // Task creation form
  document.getElementById('create-task-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('task-title').value.trim();
    const project = document.getElementById('task-project').value.trim();
    const priority = document.getElementById('task-priority').value;
    const status = document.getElementById('task-status').value;

    if (!title || !project) return;

    try {
      const res = await fetch('/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, project, priority, status })
      });
      if (res.ok) {
        document.getElementById('create-task-form').reset();
        modal.classList.add('hidden');
        fetchTasks();
      } else {
        alert('Error creating task');
      }
    } catch (err) {
      console.error(err);
    }
  });

  // Filters
  document.getElementById('task-search').addEventListener('input', filterTasks);
  document.getElementById('status-filter').addEventListener('change', fetchTasks);

  // Stop timer button
  document.getElementById('stop-timer-btn').addEventListener('click', async () => {
    if (!activeTimer || !activeTimer.task_id) return;
    await stopTimer(activeTimer.task_id);
  });

  // Range tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentRange = btn.dataset.range;
      fetchReport(currentRange);
    });
  });
}

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

async function fetchActiveTimer() {
  try {
    const res = await fetch('/tasks/active/timer');
    const data = await res.json();
    const card = document.getElementById('active-timer-card');
    const warning = document.getElementById('idle-warning');

    if (data.active) {
      activeTimer = data;
      card.classList.remove('hidden');
      document.getElementById('active-task-title').innerText = data.task_title;
      document.getElementById('active-task-project').innerText = `📁 ${data.project}`;
      
      // Idle detection
      if (data.flagged_idle || data.elapsed_seconds >= 7200) {
        warning.classList.remove('hidden');
      } else {
        warning.classList.add('hidden');
      }

      // Start ticker
      if (!timerInterval) {
        let elapsed = data.elapsed_seconds;
        document.getElementById('active-timer-display').innerText = formatDuration(elapsed);
        timerInterval = setInterval(() => {
          elapsed++;
          document.getElementById('active-timer-display').innerText = formatDuration(elapsed);
          if (elapsed >= 7200) {
            warning.classList.remove('hidden');
          }
        }, 1000);
      }
    } else {
      activeTimer = null;
      card.classList.add('hidden');
      warning.classList.add('hidden');
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
    }
  } catch (err) {
    console.error('Error fetching active timer:', err);
  }
}

async function fetchTasks() {
  const statusFilter = document.getElementById('status-filter').value;
  let url = '/tasks';
  if (statusFilter) {
    url += `?status=${encodeURIComponent(statusFilter)}`;
  }

  try {
    const res = await fetch(url);
    const tasks = await res.json();
    renderTasks(tasks);
  } catch (err) {
    console.error('Error fetching tasks:', err);
  }
}

function renderTasks(tasks) {
  const container = document.getElementById('task-list');
  if (!tasks || tasks.length === 0) {
    container.innerHTML = '<div class="text-center" style="padding: 20px;">No tasks found. Create one!</div>';
    return;
  }

  container.innerHTML = tasks.map(task => `
    <div class="task-item ${task.is_active ? 'active-item' : ''}" data-id="${task.id}" data-title="${task.title.toLowerCase()}" data-project="${task.project.toLowerCase()}">
      <div class="task-main">
        <div class="task-title">${escapeHtml(task.title)}</div>
        <div class="task-meta">
          <span>📁 ${escapeHtml(task.project)}</span>
          <span class="badge badge-${task.priority}">${task.priority}</span>
          <span>● ${task.status}</span>
        </div>
      </div>
      <div class="task-controls">
        <span class="time-badge">${task.total_formatted}</span>
        ${task.is_active 
          ? `<button class="btn btn-sm btn-danger" onclick="stopTimer(${task.id})">Stop</button>`
          : `<button class="btn btn-sm btn-success" onclick="startTimer(${task.id})">Start</button>`
        }
        <button class="btn btn-sm btn-secondary" onclick="deleteTask(${task.id})" title="Delete task">✕</button>
      </div>
    </div>
  `).join('');
}

function filterTasks() {
  const query = document.getElementById('task-search').value.toLowerCase();
  const items = document.querySelectorAll('.task-item');
  items.forEach(item => {
    const title = item.dataset.title;
    const proj = item.dataset.project;
    if (title.includes(query) || proj.includes(query)) {
      item.style.display = 'flex';
    } else {
      item.style.display = 'none';
    }
  });
}

async function startTimer(taskId) {
  try {
    const res = await fetch(`/tasks/${taskId}/start`, { method: 'POST' });
    if (res.ok) {
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
      await fetchActiveTimer();
      await fetchTasks();
    }
  } catch (err) {
    console.error('Failed to start timer:', err);
  }
}

async function stopTimer(taskId) {
  try {
    const res = await fetch(`/tasks/${taskId}/stop`, { method: 'POST' });
    if (res.ok) {
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
      await fetchActiveTimer();
      await fetchTasks();
      await fetchReport(currentRange);
    }
  } catch (err) {
    console.error('Failed to stop timer:', err);
  }
}

async function deleteTask(taskId) {
  if (!confirm('Are you sure you want to delete this task and all its recorded sessions?')) return;
  try {
    const res = await fetch(`/tasks/${taskId}`, { method: 'DELETE' });
    if (res.ok) {
      await fetchActiveTimer();
      await fetchTasks();
      await fetchReport(currentRange);
    }
  } catch (err) {
    console.error('Failed to delete task:', err);
  }
}

async function fetchReport(range = 'week') {
  try {
    const res = await fetch(`/reports/summary?range=${range}`);
    const data = await res.json();

    document.getElementById('metric-total-time').innerText = data.formatted_time;
    document.getElementById('metric-total-sessions').innerText = data.total_sessions;
    document.getElementById('metric-idle-count').innerText = data.idle_flagged_count;

    // Render projects table
    const projBody = document.getElementById('project-summary-body');
    if (data.projects && data.projects.length > 0) {
      projBody.innerHTML = data.projects.map(p => `
        <tr>
          <td><strong>${escapeHtml(p.project)}</strong></td>
          <td>${p.formatted_time}</td>
          <td>${p.session_count}</td>
        </tr>
      `).join('');
    } else {
      projBody.innerHTML = '<tr><td colspan="3" class="text-center">No project data for this period</td></tr>';
    }

    // Render tasks table
    const taskBody = document.getElementById('task-summary-body');
    if (data.tasks && data.tasks.length > 0) {
      taskBody.innerHTML = data.tasks.map(t => `
        <tr>
          <td>${escapeHtml(t.task_title)}</td>
          <td><span class="badge badge-medium">${escapeHtml(t.project)}</span></td>
          <td><strong>${t.formatted_time}</strong></td>
        </tr>
      `).join('');
    } else {
      taskBody.innerHTML = '<tr><td colspan="3" class="text-center">No task data for this period</td></tr>';
    }
  } catch (err) {
    console.error('Failed to fetch report:', err);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
