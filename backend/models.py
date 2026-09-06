from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

StatusType = Literal["todo", "in-progress", "done"]
PriorityType = Literal["low", "medium", "high", "critical"]

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, json_schema_extra={"example": "Refactor Authentication Service"})
    project: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "Auth Service"})
    status: StatusType = Field(default="todo")
    priority: PriorityType = Field(default="medium")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    project: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[StatusType] = None
    priority: Optional[PriorityType] = None

class SessionResponse(BaseModel):
    id: int
    task_id: int
    task_title: Optional[str] = None
    project: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: int = 0
    duration_formatted: str = "00:00:00"
    flagged_idle: bool = False
    note: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    project: str
    status: StatusType
    priority: PriorityType
    created_at: str
    total_seconds: int = 0
    total_formatted: str = "0h 0m"
    is_active: bool = False
    active_session_id: Optional[int] = None
    sessions: Optional[List[SessionResponse]] = None

class SessionManualCreate(BaseModel):
    task_id: int
    start_time: str
    end_time: str
    note: Optional[str] = None

class ActiveTimerResponse(BaseModel):
    active: bool
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    project: Optional[str] = None
    session_id: Optional[int] = None
    start_time: Optional[str] = None
    elapsed_seconds: int = 0
    elapsed_formatted: str = "00:00:00"
    flagged_idle: bool = False

class ProjectSummary(BaseModel):
    project: str
    total_seconds: int
    total_hours: float
    formatted_time: str
    task_count: int
    session_count: int

class TaskReportSummary(BaseModel):
    task_id: int
    task_title: str
    project: str
    total_seconds: int
    total_hours: float
    formatted_time: str
    session_count: int

class ReportSummaryResponse(BaseModel):
    time_range: str
    start_date: Optional[str] = None
    total_seconds: int
    total_hours: float
    formatted_time: str
    total_sessions: int
    idle_flagged_count: int
    projects: List[ProjectSummary]
    tasks: List[TaskReportSummary]
