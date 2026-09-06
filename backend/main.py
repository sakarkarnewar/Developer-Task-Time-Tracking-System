import sqlite3
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse

from .database import init_db, get_db
from .models import (
    TaskCreate, TaskUpdate, TaskResponse,
    SessionManualCreate, SessionResponse, ActiveTimerResponse,
    ReportSummaryResponse
)
from . import crud

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Developer Task Time-Tracking API",
    description="High-performance backend API for tracking tasks, development sessions, active timers, and analytics.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local development & cross-origin frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory for minimal HTML/JS frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/app", include_in_schema=False)
async def serve_minimal_frontend():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return PlainTextResponse("Static frontend not initialized yet.", status_code=404)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Developer Task Time-Tracking System"}

# ----------------- TASKS ENDPOINTS -----------------

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
def create_task(task_in: TaskCreate, db: sqlite3.Connection = Depends(get_db)):
    """Create a new task with title, project, status, and priority."""
    created = crud.create_task(db, task_in)
    return created

@app.get("/tasks", response_model=List[TaskResponse], tags=["Tasks"])
def list_tasks(
    project: Optional[str] = Query(None, description="Filter by project name"),
    status: Optional[str] = Query(None, description="Filter by status (todo, in-progress, done)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, critical)"),
    db: sqlite3.Connection = Depends(get_db)
):
    """List tasks with total tracked duration and active status."""
    return crud.get_tasks(db, project=project, status=status, priority=priority)

@app.get("/tasks/active/timer", response_model=ActiveTimerResponse, tags=["Timer"])
def get_active_timer(db: sqlite3.Connection = Depends(get_db)):
    """Get the currently active running task timer, if one is running."""
    active = crud.get_active_timer(db)
    if not active:
        return {
            "active": False,
            "task_id": None,
            "task_title": None,
            "project": None,
            "session_id": None,
            "start_time": None,
            "elapsed_seconds": 0,
            "elapsed_formatted": "00:00:00",
            "flagged_idle": False
        }
    return active

@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def get_task(task_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Retrieve detailed information and session history for a specific task."""
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return task

@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def update_task(task_id: int, updates: TaskUpdate, db: sqlite3.Connection = Depends(get_db)):
    """Update task title, project, status, or priority."""
    task = crud.update_task(db, task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return task

@app.delete("/tasks/{task_id}", tags=["Tasks"])
def delete_task(task_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a task and all of its associated sessions."""
    success = crud.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return {"message": f"Task {task_id} and all related sessions deleted successfully"}

# ----------------- TIMER CONTROLS -----------------

@app.post("/tasks/{task_id}/start", tags=["Timer"])
def start_timer(task_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Start tracking time for a task. Closes any other currently active timer."""
    try:
        return crud.start_timer(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/tasks/{task_id}/stop", response_model=SessionResponse, tags=["Timer"])
def stop_timer(task_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Stop active timer for a task, calculate duration, and flag idle if duration >= 2h."""
    try:
        return crud.stop_timer(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- SESSIONS ENDPOINTS -----------------

@app.post("/sessions/manual", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, tags=["Sessions"])
def create_manual_session(session_in: SessionManualCreate, db: sqlite3.Connection = Depends(get_db)):
    """Manually log retroactive time spent on a task."""
    try:
        return crud.create_manual_session(db, session_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sessions", response_model=List[SessionResponse], tags=["Sessions"])
def list_sessions(
    limit: int = Query(100, ge=1, le=500),
    task_id: Optional[int] = Query(None),
    db: sqlite3.Connection = Depends(get_db)
):
    """List past tracking sessions."""
    return crud.get_sessions(db, limit=limit, task_id=task_id)

@app.delete("/sessions/{session_id}", tags=["Sessions"])
def delete_session(session_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a specific session record."""
    success = crud.delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found")
    return {"message": f"Session {session_id} deleted successfully"}

# ----------------- REPORTING & EXPORT -----------------

@app.get("/reports/summary", response_model=ReportSummaryResponse, tags=["Reporting"])
def get_summary_report(
    range: str = Query("week", pattern="^(day|week|month|all)$", description="Aggregation range: day, week, month, or all"),
    db: sqlite3.Connection = Depends(get_db)
):
    """Daily, weekly, or monthly summary of time spent per task and per project."""
    return crud.get_summary_report(db, time_range=range)

@app.get("/export/csv", tags=["Export"])
def export_csv(db: sqlite3.Connection = Depends(get_db)):
    """Export raw session logs as downloadable CSV."""
    csv_content = crud.export_csv_data(db)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=developer_time_tracking_sessions.csv"}
    )
