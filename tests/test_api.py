import pytest
import os
import tempfile
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

# Set temporary test database before importing backend modules
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["TRACKER_DB_PATH"] = temp_db_path

from backend.database import init_db
from backend.main import app

init_db(temp_db_path)
client = TestClient(app)

def teardown_module():
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_task_crud():
    # 1. Create task
    task_payload = {
        "title": "Build Auth Middleware",
        "project": "Security",
        "priority": "high",
        "status": "todo"
    }
    create_res = client.post("/tasks", json=task_payload)
    assert create_res.status_code == 201
    task = create_res.json()
    task_id = task["id"]
    assert task["title"] == "Build Auth Middleware"
    assert task["project"] == "Security"
    assert task["priority"] == "high"
    assert task["status"] == "todo"

    # 2. Get task list
    list_res = client.get("/tasks")
    assert list_res.status_code == 200
    tasks = list_res.json()
    assert any(t["id"] == task_id for t in tasks)

    # 3. Update task
    update_res = client.patch(f"/tasks/{task_id}", json={"status": "in-progress", "priority": "critical"})
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["status"] == "in-progress"
    assert updated["priority"] == "critical"

    # 4. Get specific task
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Build Auth Middleware"

def test_timer_lifecycle():
    # Create task
    t_res = client.post("/tasks", json={"title": "Timer Test Task", "project": "Testing", "priority": "low", "status": "todo"})
    task_id = t_res.json()["id"]

    # Start timer
    start_res = client.post(f"/tasks/{task_id}/start")
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["active"] is True
    assert start_data["task_id"] == task_id

    # Check active timer endpoint
    active_res = client.get("/tasks/active/timer")
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["active"] is True
    assert active_data["task_id"] == task_id

    # Stop timer
    stop_res = client.post(f"/tasks/{task_id}/stop")
    assert stop_res.status_code == 200
    session_data = stop_res.json()
    assert session_data["task_id"] == task_id
    assert session_data["end_time"] is not None

    # Check active timer is now inactive
    active_res2 = client.get("/tasks/active/timer")
    assert active_res2.status_code == 200
    assert active_res2.json()["active"] is False

def test_timer_auto_switch():
    # When timer is running on Task 1 and user starts Task 2, Task 1 should be stopped automatically
    t1 = client.post("/tasks", json={"title": "Task 1", "project": "P1", "priority": "medium", "status": "todo"}).json()
    t2 = client.post("/tasks", json={"title": "Task 2", "project": "P2", "priority": "medium", "status": "todo"}).json()

    # Start Task 1
    client.post(f"/tasks/{t1['id']}/start")
    a1 = client.get("/tasks/active/timer").json()
    assert a1["task_id"] == t1["id"]

    # Start Task 2
    client.post(f"/tasks/{t2['id']}/start")
    a2 = client.get("/tasks/active/timer").json()
    assert a2["task_id"] == t2["id"]

    # Task 1 timer should now be closed
    t1_details = client.get(f"/tasks/{t1['id']}").json()
    assert len(t1_details["sessions"]) >= 1
    assert t1_details["sessions"][0]["end_time"] is not None

    # Clean up by stopping Task 2
    client.post(f"/tasks/{t2['id']}/stop")

def test_manual_session_and_idle_detection():
    t = client.post("/tasks", json={"title": "Idle Detection Task", "project": "Analytics", "priority": "medium", "status": "todo"}).json()
    task_id = t["id"]

    # Create session with 2 hours 15 minutes (8100 seconds) -> Should be flagged idle!
    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(hours=3)
    end_dt = start_dt + timedelta(hours=2, minutes=15)

    manual_payload = {
        "task_id": task_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "note": "Extensive load testing session"
    }

    res = client.post("/sessions/manual", json=manual_payload)
    assert res.status_code == 201
    sess = res.json()
    assert sess["duration_seconds"] == 8100
    assert sess["flagged_idle"] is True
    assert sess["note"] == "Extensive load testing session"

def test_reports_and_csv_export():
    # Reports summary
    rep_res = client.get("/reports/summary?range=all")
    assert rep_res.status_code == 200
    report = rep_res.json()
    assert report["total_seconds"] > 0
    assert len(report["projects"]) > 0
    assert len(report["tasks"]) > 0
    assert report["idle_flagged_count"] >= 1

    # CSV export
    csv_res = client.get("/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    csv_text = csv_res.text
    assert "session_id,task_id,task_title,project" in csv_text
    assert "Idle Detection Task" in csv_text
    assert "YES" in csv_text # Idle flagged indicator
