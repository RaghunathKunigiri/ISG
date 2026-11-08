from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class LoginIn(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes
    role: str
    permissions: List[str]
    employee_id: str
    employee_name: str
    org_id: str


class MFASetupOut(BaseModel):
    secret: str
    otpauth_url: str


class MFAVerifyIn(BaseModel):
    code: str


# Organization Schemas
class OrgOut(BaseModel):
    id: str
    name: str
    domain: str
    settings_json: Dict[str, Any]
    created_at: datetime


# Role & Permission Schemas
class PermissionOut(BaseModel):
    id: str
    code: str
    description: Optional[str] = None


class RoleOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


# Employee Schemas
class EmployeeBase(BaseModel):
    employee_code: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role_id: str
    manager_id: Optional[str] = None
    department: str
    designation: str
    location: Optional[str] = None
    shift: str = "general"
    date_of_joining: date
    status: str = "active"


class EmployeeCreate(EmployeeBase):
    password: str


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[str] = None
    manager_id: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    shift: Optional[str] = None
    status: Optional[str] = None


class EmployeeOut(EmployeeBase):
    id: str
    org_id: str
    role_name: str
    avatar_url: Optional[str] = None
    created_at: datetime


# Project Schemas
class ProjectBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    owner_id: str
    status: str = "planned"
    priority: str = "medium"
    start_date: date
    target_end_date: date
    budget_hours: float = 0.0
    budget_cost: float = 0.0


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    budget_hours: Optional[float] = None
    budget_cost: Optional[float] = None


class ProjectMemberCreate(BaseModel):
    employee_id: str
    role_on_project: str = "Member"
    allocation_pct: float = 100.0
    billable_rate: float = 0.0


class ProjectMemberOut(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    role_on_project: str
    allocation_pct: float
    billable_rate: float


class ProjectOut(ProjectBase):
    id: str
    org_id: str
    health: str
    progress_pct: float
    spi: Optional[float] = None
    effort_variance: Optional[float] = None
    owner_name: Optional[str] = None
    created_at: datetime


# Milestone Schemas
class MilestoneCreate(BaseModel):
    project_id: str
    name: str
    due_date: date
    weight: float = 1.0


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    weight: Optional[float] = None


class MilestoneOut(BaseModel):
    id: str
    project_id: str
    name: str
    due_date: date
    status: str
    weight: float
    progress_pct: float
    created_at: datetime


# Task Schemas
class TaskCreate(BaseModel):
    project_id: str
    milestone_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    story_points: int = 1
    estimated_hours: float = 0.0
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    tags: List[str] = []


class TaskUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    story_points: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    progress_pct: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    blocked_reason: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskProgressNoteIn(BaseModel):
    progress_pct: float
    comment: str
    hours_logged: float = 0.0


class TaskUpdateOut(BaseModel):
    id: str
    task_id: str
    employee_id: str
    employee_name: str
    progress_pct: float
    comment: str
    hours_logged: float
    created_at: datetime


class TaskOut(BaseModel):
    id: str
    org_id: str
    project_id: str
    milestone_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    reporter_id: str
    reporter_name: Optional[str] = None
    status: str
    priority: str
    story_points: int
    estimated_hours: float
    actual_hours: float
    progress_pct: float
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    tags: List[str] = []
    created_at: datetime


# Timesheet Schemas
class TimesheetCreate(BaseModel):
    project_id: str
    task_id: Optional[str] = None
    work_date: date
    hours: float
    description: str
    billable: bool = True


class TimesheetUpdate(BaseModel):
    hours: Optional[float] = None
    description: Optional[str] = None
    billable: Optional[bool] = None
    status: Optional[str] = None


class TimesheetOut(BaseModel):
    id: str
    org_id: str
    employee_id: str
    employee_name: str
    project_id: str
    project_name: str
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    work_date: date
    hours: float
    description: str
    billable: bool
    status: str
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime


# Attendance Schemas
class AttendanceOut(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    work_date: date
    first_login_at: Optional[datetime] = None
    last_logout_at: Optional[datetime] = None
    total_active_minutes: int
    session_count: int
    status: str
    is_late: bool


# Audit Log Schemas
class AuditLogOut(BaseModel):
    id: str
    actor_employee_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    before_json: Optional[Dict[str, Any]] = None
    after_json: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


# Dashboard Schemas
class MemberDashboardOut(BaseModel):
    my_tasks_by_status: Dict[str, int]
    my_hours_this_week: float
    overdue_task_ids: List[str]
    recent_tasks: List[TaskOut]


class ManagerDashboardOut(BaseModel):
    team_size: int
    blocked_count: int
    timesheet_approval_queue: int
    team_progress: List[Dict[str, Any]]
    blocked_tasks: List[TaskOut]
    capacity_heatmap: List[Dict[str, Any]]


class AdminDashboardOut(BaseModel):
    project_count: int
    employee_count: int
    active_sessions_count: int
    project_health_grid: List[Dict[str, Any]]
    recent_login_attempts: List[Dict[str, Any]]

