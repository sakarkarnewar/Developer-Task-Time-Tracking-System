# Developer Task Time-Tracking System

A lightweight, self-contained, and full-featured Developer Task Time-Tracking System built with **FastAPI**, **SQLite**, and an interactive **Streamlit** dashboard (along with a standalone lightweight HTML/JS frontend).

Designed to help engineers manage backlogs, track active development time with zero friction, log retroactive sessions, flag idle timer anomalies, analyze productivity metrics, and export audit logs to CSV.

---

## 🚀 Key Features

- **Task Management**: Create, view, filter, update, and delete tasks with project tags, status (`todo`, `in-progress`, `done`), and priority (`low`, `medium`, `high`, `critical`).
- **Live Active Timer**:
  - Start/Stop timer with one click per task.
  - Automatically handles timer switching (only 1 active timer runs at a time).
  - Promotes task status to `in-progress` when timer starts.
- **Idle Detection (Threshold: 2 Hours)**:
  - Automatically flags sessions running uninterrupted past 2 hours (`flagged_idle = 1`).
  - Highlights warnings on the dashboard and audit logs for review instead of silently trusting unmonitored timers.
- **Manual Retroactive Logging**:
  - Record past work sessions, meetings, or offline debugging with date/time pickers and notes.
- **Reporting & Visual Analytics**:
  - Aggregates daily, weekly, monthly, and all-time tracked hours.
  - Interactive Plotly charts: Time spent by Project (Donut & Bar charts), Time spent by Task (Ranking chart).
- **Session Audit & CSV Export**:
  - Complete history of all tracking sessions with start/end ISO timestamps, duration, and idle flags.
  - One-click RFC-4180 CSV export for external analysis, invoicing, or sprint retrospectives.
- **Dual Frontend Support**:
  1. **Streamlit App**: Interactive analytical dashboard.
  2. **Minimal HTML/JS Frontend**: Lightweight zero-dependency single-page UI served directly by FastAPI at `/app`.

---

## 🛠️ Architecture & Tech Stack

```
Developer task time tracking system/
├── backend/
│   ├── __init__.py
│   ├── database.py       # SQLite connection with WAL mode & foreign keys
│   ├── models.py         # Pydantic v2 validation models
│   ├── crud.py           # DB business logic, timer engine, reports & CSV export
│   ├── main.py           # FastAPI application & REST endpoints
│   └── static/           # Minimal single-page HTML/JS/CSS frontend
│       ├── index.html
│       ├── style.css
│       └── app.js
├── frontend/
│   └── app.py            # Streamlit dashboard & analytics UI
├── tests/
│   └── test_api.py       # Automated test suite using pytest & TestClient
├── seed.py               # Database seed script with sample tasks & sessions
├── PROMPT.md             # Generated prompt specification for Antigravity
├── requirements.txt      # Python dependencies
└── README.md             # Documentation & setup guide
```

---

## 📦 Setup & Installation

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Seed Sample Data (Optional)
Populate realistic tasks and past sessions across multiple projects:
```bash
python seed.py
```

---

## 🏃 Running the Application

### Step 1: Start the FastAPI Backend
Launch the backend API on `http://127.0.0.1:8000`:
```bash
uvicorn backend.main:app --port 8000 --reload
```
- **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Minimal HTML/JS Frontend**: [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)

### Step 2: Start the Streamlit Dashboard
In a separate terminal window, start the Streamlit frontend:
```bash
streamlit run frontend/app.py
```
This opens the rich dashboard in your browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the test suite with `pytest`:
```bash
python -m pytest tests/test_api.py -v
```

Tests verify:
- Task CRUD operations (create, read, patch, delete).
- Active timer start/stop lifecycle and duration calculation.
- Auto-switching between tasks (preventing orphaned active timers).
- Idle detection threshold flagging (> 2 hours).
- Manual retroactive session recording.
- Summary report aggregations and CSV data streaming.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/tasks` | Create a new task (`title`, `project`, `status`, `priority`) |
| `GET` | `/tasks` | List tasks with filters (`project`, `status`, `priority`) |
| `GET` | `/tasks/{id}` | Get task details with complete session history |
| `PATCH` | `/tasks/{id}` | Update task title, project, status, or priority |
| `DELETE` | `/tasks/{id}` | Delete task and cascade delete its sessions |
| `POST` | `/tasks/{id}/start` | Start tracking timer for a task |
| `POST` | `/tasks/{id}/stop` | Stop tracking timer, calculate duration, flag if idle |
| `GET` | `/tasks/active/timer`| Check currently running timer across all tasks |
| `POST` | `/sessions/manual` | Log past retroactive session |
| `GET` | `/sessions` | List recorded sessions |
| `DELETE` | `/sessions/{id}` | Delete a specific session |
| `GET` | `/reports/summary` | Summary report (Query param: `range=day\|week\|month\|all`) |
| `GET` | `/export/csv` | Download sessions export as CSV file |

---

## 📄 Prompt Specification
The generated prompt specification for this system is located at [`PROMPT.md`](file:///c:/Users/VICTUS/OneDrive/Desktop/Developer%20task%20time%20tracking%20system/PROMPT.md).
