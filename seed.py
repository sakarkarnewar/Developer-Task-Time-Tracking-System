"""
Seed script to populate sample tasks and historical tracking sessions.
"""
import sqlite3
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from backend.database import init_db, get_db_connection

def seed_database():
    print("[INFO] Initializing database schema...")
    init_db()
    conn = get_db_connection()
    
    # Check if data already exists
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count > 0:
        print(f"[INFO] Database already contains {count} tasks. Clearing existing data for fresh seed...")
        with conn:
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM tasks")

    now = datetime.now(timezone.utc)
    
    tasks_data = [
        ("Implement JWT Authentication & Refresh Tokens", "Core API", "in-progress", "high"),
        ("Build Responsive Developer Time-Tracker Dashboard", "Web Portal", "in-progress", "critical"),
        ("Configure GitHub Actions CI/CD Pipeline", "DevOps", "done", "medium"),
        ("Fix Race Condition in Session Worker", "Core API", "done", "critical"),
        ("Design REST API Spec and OpenAPI Documentation", "Core API", "done", "medium"),
        ("Optimize Database Query Indexes & Benchmarks", "Database", "todo", "low"),
        ("Set up Sentry Error Logging & Slack Alerts", "DevOps", "todo", "medium"),
    ]

    print("[INFO] Inserting sample tasks...")
    task_ids = []
    with conn:
        for title, project, status, priority in tasks_data:
            cursor = conn.execute("""
                INSERT INTO tasks (title, project, status, priority, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (title, project, status, priority, (now - timedelta(days=5)).isoformat()))
            task_ids.append(cursor.lastrowid)

    # Insert realistic past sessions
    # Task 0: JWT Auth (2 sessions)
    s1_start = now - timedelta(days=2, hours=4)
    s1_end = s1_start + timedelta(minutes=95)
    
    s2_start = now - timedelta(days=1, hours=3)
    s2_end = s2_start + timedelta(minutes=45)

    # Task 1: Dashboard (1 session normal, 1 session long/idle flagged > 2 hours)
    s3_start = now - timedelta(days=1, hours=6)
    s3_end = s3_start + timedelta(hours=2, minutes=20) # 8400s -> FLAGGED IDLE
    
    s4_start = now - timedelta(hours=3)
    s4_end = s4_start + timedelta(minutes=50)

    # Task 2: CI/CD (1 session)
    s5_start = now - timedelta(days=3, hours=5)
    s5_end = s5_start + timedelta(hours=1, minutes=15)

    # Task 3: Race condition (1 session)
    s6_start = now - timedelta(days=4, hours=2)
    s6_end = s6_start + timedelta(minutes=75)

    # Task 4: OpenAPI Spec (1 session)
    s7_start = now - timedelta(days=4, hours=6)
    s7_end = s7_start + timedelta(minutes=60)

    sessions_data = [
        (task_ids[0], s1_start, s1_end, "Initial token validation & RSA key loading"),
        (task_ids[0], s2_start, s2_end, "Added refresh token rotation endpoint"),
        (task_ids[1], s3_start, s3_end, "Frontend layout components & charting"), # Will be flagged
        (task_ids[1], s4_start, s4_end, "Streamlit dashboard timer integration"),
        (task_ids[2], s5_start, s5_end, "Configured test runner & caching steps"),
        (task_ids[3], s6_start, s6_end, "Root caused async lock deadlock"),
        (task_ids[4], s7_start, s7_end, "Drafted OpenAPI 3.0 YAML spec"),
    ]

    print("[INFO] Inserting historical tracking sessions...")
    with conn:
        for t_id, start_dt, end_dt, note in sessions_data:
            duration = int((end_dt - start_dt).total_seconds())
            flagged = 1 if duration >= 7200 else 0
            conn.execute("""
                INSERT INTO sessions (task_id, start_time, end_time, duration_seconds, flagged_idle, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (t_id, start_dt.isoformat(), end_dt.isoformat(), duration, flagged, note))

    conn.close()
    print("[SUCCESS] Database successfully seeded with 7 tasks and 7 realistic sessions!")

if __name__ == "__main__":
    seed_database()
