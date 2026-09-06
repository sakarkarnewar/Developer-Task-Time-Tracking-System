import sqlite3
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from .models import TaskCreate, TaskUpdate, SessionManualCreate

IDLE_THRESHOLD_SECONDS = 7200  # 2 hours

def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string reliably."""
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        # Fallback format parsing
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)

def format_seconds_hms(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_seconds_human(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    elif m > 0:
        return f"{m}m"
    else:
        return f"{seconds}s"

def get_active_timer(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    cursor = conn.execute("""
        SELECT s.id as session_id, s.task_id, s.start_time, s.flagged_idle,
               t.title as task_title, t.project
        FROM sessions s
        JOIN tasks t ON s.task_id = t.id
        WHERE s.end_time IS NULL
        ORDER BY s.id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        return None
    
    start_dt = parse_iso_datetime(row["start_time"])
    now_dt = datetime.now(timezone.utc)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    
    elapsed = int((now_dt - start_dt).total_seconds())
    if elapsed < 0:
        elapsed = 0
    
    flagged = bool(row["flagged_idle"]) or (elapsed >= IDLE_THRESHOLD_SECONDS)
    
    return {
        "active": True,
        "session_id": row["session_id"],
        "task_id": row["task_id"],
        "task_title": row["task_title"],
        "project": row["project"],
        "start_time": row["start_time"],
        "elapsed_seconds": elapsed,
        "elapsed_formatted": format_seconds_hms(elapsed),
        "flagged_idle": flagged
    }

def create_task(conn: sqlite3.Connection, task: TaskCreate) -> Dict[str, Any]:
    with conn:
        cursor = conn.execute("""
            INSERT INTO tasks (title, project, status, priority)
            VALUES (?, ?, ?, ?)
        """, (task.title.strip(), task.project.strip(), task.status, task.priority))
        task_id = cursor.lastrowid
    return get_task(conn, task_id)

def get_tasks(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> List[Dict[str, Any]]:
    active_info = get_active_timer(conn)
    active_task_id = active_info["task_id"] if active_info else None
    
    query = """
        SELECT t.id, t.title, t.project, t.status, t.priority, t.created_at,
               COALESCE(SUM(s.duration_seconds), 0) as total_seconds
        FROM tasks t
        LEFT JOIN sessions s ON t.id = s.task_id AND s.end_time IS NOT NULL
        WHERE 1=1
    """
    params = []
    if project:
        query += " AND t.project = ?"
        params.append(project)
    if status:
        query += " AND t.status = ?"
        params.append(status)
    if priority:
        query += " AND t.priority = ?"
        params.append(priority)
        
    query += " GROUP BY t.id ORDER BY t.id DESC"
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        t_id = r["id"]
        is_active = (t_id == active_task_id)
        tot_sec = r["total_seconds"]
        # If currently active, add running elapsed time
        if is_active and active_info:
            tot_sec += active_info["elapsed_seconds"]
            
        results.append({
            "id": t_id,
            "title": r["title"],
            "project": r["project"],
            "status": r["status"],
            "priority": r["priority"],
            "created_at": str(r["created_at"]),
            "total_seconds": tot_sec,
            "total_formatted": format_seconds_human(tot_sec),
            "is_active": is_active,
            "active_session_id": active_info["session_id"] if is_active else None
        })
    return results

def get_task(conn: sqlite3.Connection, task_id: int) -> Optional[Dict[str, Any]]:
    cursor = conn.execute("""
        SELECT t.id, t.title, t.project, t.status, t.priority, t.created_at,
               COALESCE(SUM(s.duration_seconds), 0) as total_seconds
        FROM tasks t
        LEFT JOIN sessions s ON t.id = s.task_id AND s.end_time IS NOT NULL
        WHERE t.id = ?
        GROUP BY t.id
    """, (task_id,))
    row = cursor.fetchone()
    if not row:
        return None
    
    # Fetch sessions for this task
    s_cursor = conn.execute("""
        SELECT id, task_id, start_time, end_time, duration_seconds, flagged_idle, note
        FROM sessions
        WHERE task_id = ?
        ORDER BY id DESC
    """, (task_id,))
    sessions_raw = s_cursor.fetchall()
    
    active_info = get_active_timer(conn)
    is_active = (active_info is not None and active_info["task_id"] == task_id)
    
    sessions_list = []
    for s in sessions_raw:
        dur = s["duration_seconds"] or 0
        sessions_list.append({
            "id": s["id"],
            "task_id": s["task_id"],
            "task_title": row["title"],
            "project": row["project"],
            "start_time": str(s["start_time"]),
            "end_time": str(s["end_time"]) if s["end_time"] else None,
            "duration_seconds": dur,
            "duration_formatted": format_seconds_hms(dur),
            "flagged_idle": bool(s["flagged_idle"]),
            "note": s["note"]
        })
    
    tot_sec = row["total_seconds"]
    if is_active and active_info:
        tot_sec += active_info["elapsed_seconds"]
        
    return {
        "id": row["id"],
        "title": row["title"],
        "project": row["project"],
        "status": row["status"],
        "priority": row["priority"],
        "created_at": str(row["created_at"]),
        "total_seconds": tot_sec,
        "total_formatted": format_seconds_human(tot_sec),
        "is_active": is_active,
        "active_session_id": active_info["session_id"] if is_active else None,
        "sessions": sessions_list
    }

def update_task(conn: sqlite3.Connection, task_id: int, updates: TaskUpdate) -> Optional[Dict[str, Any]]:
    existing = get_task(conn, task_id)
    if not existing:
        return None
    
    fields = []
    values = []
    if updates.title is not None:
        fields.append("title = ?")
        values.append(updates.title.strip())
    if updates.project is not None:
        fields.append("project = ?")
        values.append(updates.project.strip())
    if updates.status is not None:
        fields.append("status = ?")
        values.append(updates.status)
    if updates.priority is not None:
        fields.append("priority = ?")
        values.append(updates.priority)
        
    if fields:
        values.append(task_id)
        with conn:
            conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
            
    return get_task(conn, task_id)

def delete_task(conn: sqlite3.Connection, task_id: int) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0

def start_timer(conn: sqlite3.Connection, task_id: int) -> Dict[str, Any]:
    task = get_task(conn, task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} does not exist.")
    
    # Check if there is an existing running session
    active = get_active_timer(conn)
    if active:
        if active["task_id"] == task_id:
            # Already running on this task
            return active
        else:
            # Automatically stop previous active timer on another task
            stop_timer(conn, active["task_id"])
            
    now_iso = datetime.now(timezone.utc).isoformat()
    with conn:
        # If task was 'todo', promote to 'in-progress'
        if task["status"] == "todo":
            conn.execute("UPDATE tasks SET status = 'in-progress' WHERE id = ?", (task_id,))
            
        cursor = conn.execute("""
            INSERT INTO sessions (task_id, start_time, end_time, duration_seconds, flagged_idle)
            VALUES (?, ?, NULL, 0, 0)
        """, (task_id, now_iso))
        session_id = cursor.lastrowid
        
    return {
        "active": True,
        "session_id": session_id,
        "task_id": task_id,
        "task_title": task["title"],
        "project": task["project"],
        "start_time": now_iso,
        "elapsed_seconds": 0,
        "elapsed_formatted": "00:00:00",
        "flagged_idle": False
    }

def stop_timer(conn: sqlite3.Connection, task_id: int) -> Dict[str, Any]:
    # Find active session for this task
    cursor = conn.execute("""
        SELECT id, start_time FROM sessions
        WHERE task_id = ? AND end_time IS NULL
        ORDER BY id DESC LIMIT 1
    """, (task_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No running timer found for task ID {task_id}.")
    
    session_id = row["id"]
    start_dt = parse_iso_datetime(row["start_time"])
    now_dt = datetime.now(timezone.utc)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
        
    duration = int((now_dt - start_dt).total_seconds())
    if duration < 0:
        duration = 0
        
    flagged = 1 if duration >= IDLE_THRESHOLD_SECONDS else 0
    now_iso = now_dt.isoformat()
    
    with conn:
        conn.execute("""
            UPDATE sessions
            SET end_time = ?, duration_seconds = ?, flagged_idle = ?
            WHERE id = ?
        """, (now_iso, duration, flagged, session_id))
        
    task = get_task(conn, task_id)
    return {
        "id": session_id,
        "task_id": task_id,
        "task_title": task["title"] if task else "",
        "project": task["project"] if task else "",
        "start_time": row["start_time"],
        "end_time": now_iso,
        "duration_seconds": duration,
        "duration_formatted": format_seconds_hms(duration),
        "flagged_idle": bool(flagged),
        "note": None
    }

def create_manual_session(conn: sqlite3.Connection, manual: SessionManualCreate) -> Dict[str, Any]:
    task = get_task(conn, manual.task_id)
    if not task:
        raise ValueError(f"Task with ID {manual.task_id} does not exist.")
        
    start_dt = parse_iso_datetime(manual.start_time)
    end_dt = parse_iso_datetime(manual.end_time)
    if end_dt < start_dt:
        raise ValueError("End time cannot be earlier than start time.")
        
    duration = int((end_dt - start_dt).total_seconds())
    flagged = 1 if duration >= IDLE_THRESHOLD_SECONDS else 0
    
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()
    
    with conn:
        cursor = conn.execute("""
            INSERT INTO sessions (task_id, start_time, end_time, duration_seconds, flagged_idle, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (manual.task_id, start_iso, end_iso, duration, flagged, manual.note))
        session_id = cursor.lastrowid
        
    return {
        "id": session_id,
        "task_id": manual.task_id,
        "task_title": task["title"],
        "project": task["project"],
        "start_time": start_iso,
        "end_time": end_iso,
        "duration_seconds": duration,
        "duration_formatted": format_seconds_hms(duration),
        "flagged_idle": bool(flagged),
        "note": manual.note
    }

def delete_session(conn: sqlite3.Connection, session_id: int) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0

def get_sessions(
    conn: sqlite3.Connection,
    limit: int = 100,
    task_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    query = """
        SELECT s.id, s.task_id, s.start_time, s.end_time, s.duration_seconds, s.flagged_idle, s.note,
               t.title as task_title, t.project
        FROM sessions s
        JOIN tasks t ON s.task_id = t.id
        WHERE 1=1
    """
    params = []
    if task_id is not None:
        query += " AND s.task_id = ?"
        params.append(task_id)
        
    query += " ORDER BY s.id DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    result = []
    for r in rows:
        dur = r["duration_seconds"] or 0
        result.append({
            "id": r["id"],
            "task_id": r["task_id"],
            "task_title": r["task_title"],
            "project": r["project"],
            "start_time": str(r["start_time"]),
            "end_time": str(r["end_time"]) if r["end_time"] else None,
            "duration_seconds": dur,
            "duration_formatted": format_seconds_hms(dur),
            "flagged_idle": bool(r["flagged_idle"]),
            "note": r["note"]
        })
    return result

def get_summary_report(conn: sqlite3.Connection, time_range: str = "week") -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    time_range = time_range.lower()
    
    if time_range == "day":
        cutoff = now - timedelta(days=1)
    elif time_range == "week":
        cutoff = now - timedelta(days=7)
    elif time_range == "month":
        cutoff = now - timedelta(days=30)
    else:
        # "all" or unrecognized
        cutoff = None
        
    where_clause = "WHERE s.end_time IS NOT NULL"
    params: List[Any] = []
    if cutoff:
        where_clause += " AND s.start_time >= ?"
        params.append(cutoff.isoformat())
        
    # Project summary
    proj_query = f"""
        SELECT t.project,
               COALESCE(SUM(s.duration_seconds), 0) as total_seconds,
               COUNT(DISTINCT t.id) as task_count,
               COUNT(s.id) as session_count
        FROM tasks t
        JOIN sessions s ON t.id = s.task_id
        {where_clause}
        GROUP BY t.project
        ORDER BY total_seconds DESC
    """
    proj_rows = conn.execute(proj_query, params).fetchall()
    projects = []
    for pr in proj_rows:
        sec = pr["total_seconds"]
        projects.append({
            "project": pr["project"],
            "total_seconds": sec,
            "total_hours": round(sec / 3600.0, 2),
            "formatted_time": format_seconds_human(sec),
            "task_count": pr["task_count"],
            "session_count": pr["session_count"]
        })
        
    # Task summary
    task_query = f"""
        SELECT t.id as task_id, t.title as task_title, t.project,
               COALESCE(SUM(s.duration_seconds), 0) as total_seconds,
               COUNT(s.id) as session_count
        FROM tasks t
        JOIN sessions s ON t.id = s.task_id
        {where_clause}
        GROUP BY t.id
        ORDER BY total_seconds DESC
    """
    task_rows = conn.execute(task_query, params).fetchall()
    tasks = []
    for tr in task_rows:
        sec = tr["total_seconds"]
        tasks.append({
            "task_id": tr["task_id"],
            "task_title": tr["task_title"],
            "project": tr["project"],
            "total_seconds": sec,
            "total_hours": round(sec / 3600.0, 2),
            "formatted_time": format_seconds_human(sec),
            "session_count": tr["session_count"]
        })
        
    # Global totals
    total_sec = sum(p["total_seconds"] for p in projects)
    total_sess = sum(p["session_count"] for p in projects)
    
    # Idle flagged count
    idle_query = f"SELECT COUNT(*) FROM sessions s {where_clause} AND s.flagged_idle = 1"
    idle_count = conn.execute(idle_query, params).fetchone()[0]
    
    return {
        "time_range": time_range,
        "start_date": cutoff.isoformat() if cutoff else None,
        "total_seconds": total_sec,
        "total_hours": round(total_sec / 3600.0, 2),
        "formatted_time": format_seconds_human(total_sec),
        "total_sessions": total_sess,
        "idle_flagged_count": idle_count,
        "projects": projects,
        "tasks": tasks
    }

def export_csv_data(conn: sqlite3.Connection) -> str:
    cursor = conn.execute("""
        SELECT s.id as session_id, s.task_id, t.title as task_title, t.project,
               s.start_time, s.end_time, s.duration_seconds, s.flagged_idle, s.note
        FROM sessions s
        JOIN tasks t ON s.task_id = t.id
        ORDER BY s.id DESC
    """)
    rows = cursor.fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "session_id", "task_id", "task_title", "project",
        "start_time", "end_time", "duration_seconds", "duration_minutes",
        "duration_hours", "flagged_idle", "note"
    ])
    
    for r in rows:
        sec = r["duration_seconds"] or 0
        writer.writerow([
            r["session_id"],
            r["task_id"],
            r["task_title"],
            r["project"],
            r["start_time"],
            r["end_time"] or "IN_PROGRESS",
            sec,
            round(sec / 60.0, 2),
            round(sec / 3600.0, 2),
            "YES" if r["flagged_idle"] else "NO",
            r["note"] or ""
        ])
        
    return output.getvalue()
