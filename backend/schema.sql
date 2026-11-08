-- =============================================================================
-- Project & Employee Progress Tracking System
-- PostgreSQL 15+ Complete Production Schema with Foreign Keys & Indexes
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Organizations (Multi-tenant root)
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_organizations_domain ON organizations(domain);
CREATE INDEX IF NOT EXISTS ix_organizations_deleted_at ON organizations(deleted_at);

-- 2. Permissions (resource:action)
CREATE TABLE IF NOT EXISTS permissions (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255) NULL
);
CREATE INDEX IF NOT EXISTS ix_permissions_code ON permissions(code);

-- 3. Roles
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NULL REFERENCES organizations(id) ONDELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(255) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_roles_org_id ON roles(org_id);
CREATE INDEX IF NOT EXISTS ix_roles_name ON roles(name);

-- 4. Role Permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(36) REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- 5. Employees
CREATE TABLE IF NOT EXISTS employees (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    employee_code VARCHAR(50) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(100) NULL,
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id),
    manager_id VARCHAR(36) NULL REFERENCES employees(id) ON DELETE SET NULL,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(100) NOT NULL,
    location VARCHAR(100) NULL,
    shift VARCHAR(50) NOT NULL DEFAULT 'general',
    date_of_joining DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    password_hash VARCHAR(255) NOT NULL,
    mfa_secret VARCHAR(255) NULL,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_url VARCHAR(500) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_emp_org_email UNIQUE (org_id, email),
    CONSTRAINT uq_emp_org_code UNIQUE (org_id, employee_code)
);
CREATE INDEX IF NOT EXISTS ix_employees_org_id ON employees(org_id);
CREATE INDEX IF NOT EXISTS ix_employees_role_id ON employees(role_id);
CREATE INDEX IF NOT EXISTS ix_employees_manager_id ON employees(manager_id);
CREATE INDEX IF NOT EXISTS ix_employees_org_status ON employees(org_id, status);

-- 6. Projects
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    client VARCHAR(255) NULL,
    owner_id VARCHAR(36) NOT NULL REFERENCES employees(id),
    status VARCHAR(50) NOT NULL DEFAULT 'planned',
    priority VARCHAR(50) NOT NULL DEFAULT 'medium',
    start_date DATE NOT NULL,
    target_end_date DATE NOT NULL,
    actual_end_date DATE NULL,
    budget_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    budget_cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    health VARCHAR(20) NOT NULL DEFAULT 'green',
    progress_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_proj_org_code UNIQUE (org_id, code)
);
CREATE INDEX IF NOT EXISTS ix_projects_org_status ON projects(org_id, status);
CREATE INDEX IF NOT EXISTS ix_projects_owner_id ON projects(owner_id);

-- 7. Project Members
CREATE TABLE IF NOT EXISTS project_members (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    employee_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    role_on_project VARCHAR(100) NOT NULL DEFAULT 'Member',
    allocation_pct DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    billable_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_proj_member UNIQUE (project_id, employee_id)
);
CREATE INDEX IF NOT EXISTS ix_proj_members_org ON project_members(org_id);
CREATE INDEX IF NOT EXISTS ix_proj_members_emp ON project_members(employee_id);

-- 8. Milestones
CREATE TABLE IF NOT EXISTS milestones (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    progress_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_milestones_proj_status ON milestones(project_id, status);
CREATE INDEX IF NOT EXISTS ix_milestones_org ON milestones(org_id);

-- 9. Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    milestone_id VARCHAR(36) NULL REFERENCES milestones(id) ON DELETE SET NULL,
    parent_task_id VARCHAR(36) NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    assignee_id VARCHAR(36) NULL REFERENCES employees(id) ON DELETE SET NULL,
    reporter_id VARCHAR(36) NOT NULL REFERENCES employees(id),
    status VARCHAR(50) NOT NULL DEFAULT 'todo',
    priority VARCHAR(50) NOT NULL DEFAULT 'medium',
    story_points INTEGER NOT NULL DEFAULT 1,
    estimated_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    actual_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    progress_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    start_date DATE NULL,
    due_date DATE NULL,
    completed_at TIMESTAMPTZ NULL,
    blocked_reason TEXT NULL,
    blocked_at TIMESTAMPTZ NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_tasks_org_status ON tasks(org_id, status);
CREATE INDEX IF NOT EXISTS ix_tasks_assignee_status ON tasks(assignee_id, status);
CREATE INDEX IF NOT EXISTS ix_tasks_proj_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS ix_tasks_milestone ON tasks(milestone_id);
CREATE INDEX IF NOT EXISTS ix_tasks_parent ON tasks(parent_task_id);

-- 10. Task Updates (Append-only)
CREATE TABLE IF NOT EXISTS task_updates (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    task_id VARCHAR(36) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    employee_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    progress_pct DOUBLE PRECISION NOT NULL,
    comment TEXT NOT NULL,
    hours_logged DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_task_updates_task_created ON task_updates(task_id, created_at);
CREATE INDEX IF NOT EXISTS ix_task_updates_org ON task_updates(org_id);
CREATE INDEX IF NOT EXISTS ix_task_updates_emp ON task_updates(employee_id);

-- 11. Timesheets
CREATE TABLE IF NOT EXISTS timesheets (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    employee_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id VARCHAR(36) NULL REFERENCES tasks(id) ON DELETE SET NULL,
    work_date DATE NOT NULL,
    hours DOUBLE PRECISION NOT NULL,
    description TEXT NOT NULL,
    billable BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    approved_by VARCHAR(36) NULL REFERENCES employees(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_timesheets_emp_date ON timesheets(employee_id, work_date);
CREATE INDEX IF NOT EXISTS ix_timesheets_org_status ON timesheets(org_id, status);
CREATE INDEX IF NOT EXISTS ix_timesheets_proj_date ON timesheets(project_id, work_date);

-- 12. Login Sessions
CREATE TABLE IF NOT EXISTS login_sessions (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    employee_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    session_token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255) NOT NULL,
    login_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    logout_at TIMESTAMPTZ NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(100) NULL,
    user_agent VARCHAR(500) NULL,
    device_type VARCHAR(50) NULL,
    os VARCHAR(50) NULL,
    browser VARCHAR(50) NULL,
    geo_city VARCHAR(100) NULL,
    geo_country VARCHAR(100) NULL,
    login_method VARCHAR(50) NOT NULL DEFAULT 'password',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_login_sessions_emp_login ON login_sessions(employee_id, login_at);
CREATE INDEX IF NOT EXISTS ix_login_sessions_org_active ON login_sessions(org_id, is_active);

-- 13. Login Attempts
CREATE TABLE IF NOT EXISTS login_attempts (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NULL REFERENCES organizations(id) ON DELETE SET NULL,
    email_attempted VARCHAR(255) NOT NULL,
    employee_id VARCHAR(36) NULL REFERENCES employees(id) ON DELETE SET NULL,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100) NULL,
    ip_address VARCHAR(100) NULL,
    user_agent VARCHAR(500) NULL,
    device_type VARCHAR(50) NULL,
    os VARCHAR(50) NULL,
    browser VARCHAR(50) NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_login_attempts_email_at ON login_attempts(email_attempted, attempted_at);
CREATE INDEX IF NOT EXISTS ix_login_attempts_ip_at ON login_attempts(ip_address, attempted_at);

-- 14. Attendance (Daily Rollup)
CREATE TABLE IF NOT EXISTS attendance (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    employee_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    first_login_at TIMESTAMPTZ NULL,
    last_logout_at TIMESTAMPTZ NULL,
    total_active_minutes INTEGER NOT NULL DEFAULT 0,
    session_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'absent',
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_att_emp_date UNIQUE (employee_id, work_date)
);
CREATE INDEX IF NOT EXISTS ix_attendance_org_date ON attendance(org_id, work_date);

-- 15. Audit Log (Immutable)
CREATE TABLE IF NOT EXISTS audit_log (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_employee_id VARCHAR(36) NULL REFERENCES employees(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    before_json JSONB NULL,
    after_json JSONB NULL,
    ip_address VARCHAR(100) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_org_created ON audit_log(org_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(entity_type, entity_id);

-- 16. Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    recipient_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message VARCHAR(500) NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_notifications_recip_read ON notifications(recipient_id, read_at);

-- 17. Leaves
CREATE TABLE IF NOT EXISTS leaves (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    employee_id VARCHAR(36) NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type VARCHAR(50) NOT NULL DEFAULT 'vacation',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'approved',
    reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS ix_leaves_emp_dates ON leaves(employee_id, start_date, end_date);

-- 18. Project Progress Snapshots
CREATE TABLE IF NOT EXISTS project_progress_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    progress_pct DOUBLE PRECISION NOT NULL,
    spi DOUBLE PRECISION NOT NULL,
    effort_variance DOUBLE PRECISION NOT NULL,
    actual_hours DOUBLE PRECISION NOT NULL,
    estimated_hours DOUBLE PRECISION NOT NULL,
    remaining_story_points INTEGER NOT NULL,
    health VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_snapshot_proj_date UNIQUE (project_id, snapshot_date)
);
CREATE INDEX IF NOT EXISTS ix_snapshots_org_date ON project_progress_snapshots(org_id, snapshot_date);

