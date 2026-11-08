"""Initial multi-tenant schema with all 15 tables, indexes, and constraints.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-06 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('settings_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_organizations_domain', 'organizations', ['domain'], unique=True)
    op.create_index('ix_organizations_deleted_at', 'organizations', ['deleted_at'])

    # 2. permissions
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'], unique=True)

    # 3. roles
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_roles_org_id', 'roles', ['org_id'])
    op.create_index('ix_roles_name', 'roles', ['name'])

    # 4. role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', sa.String(length=36), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )

    # 5. employees
    op.create_table(
        'employees',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_code', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('manager_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('designation', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('shift', sa.String(length=50), server_default='general', nullable=False),
        sa.Column('date_of_joining', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('mfa_secret', sa.String(length=255), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_employees_org_id', 'employees', ['org_id'])
    op.create_index('ix_employees_role_id', 'employees', ['role_id'])
    op.create_index('ix_employees_manager_id', 'employees', ['manager_id'])
    op.create_index('ix_employees_org_email', 'employees', ['org_id', 'email'], unique=True)
    op.create_index('ix_employees_org_code', 'employees', ['org_id', 'employee_code'], unique=True)
    op.create_index('ix_employees_org_status', 'employees', ['org_id', 'status'])

    # 6. projects
    op.create_table(
        'projects',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('client', sa.String(length=255), nullable=True),
        sa.Column('owner_id', sa.String(length=36), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='planned', nullable=False),
        sa.Column('priority', sa.String(length=50), server_default='medium', nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('target_end_date', sa.Date(), nullable=False),
        sa.Column('actual_end_date', sa.Date(), nullable=True),
        sa.Column('budget_hours', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('budget_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('health', sa.String(length=20), server_default='green', nullable=False),
        sa.Column('progress_pct', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_projects_org_status', 'projects', ['org_id', 'status'])
    op.create_index('ix_projects_org_code', 'projects', ['org_id', 'code'], unique=True)

    # 7. project_members
    op.create_table(
        'project_members',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_on_project', sa.String(length=100), server_default='Member', nullable=False),
        sa.Column('allocation_pct', sa.Float(), server_default='100.0', nullable=False),
        sa.Column('billable_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_project_members_unique', 'project_members', ['project_id', 'employee_id'], unique=True)

    # 8. milestones
    op.create_table(
        'milestones',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('progress_pct', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_milestones_proj_status', 'milestones', ['project_id', 'status'])

    # 9. tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('milestone_id', sa.String(length=36), sa.ForeignKey('milestones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parent_task_id', sa.String(length=36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assignee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reporter_id', sa.String(length=36), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='todo', nullable=False),
        sa.Column('priority', sa.String(length=50), server_default='medium', nullable=False),
        sa.Column('story_points', sa.Integer(), server_default='1', nullable=False),
        sa.Column('estimated_hours', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('actual_hours', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('progress_pct', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_tasks_org_status', 'tasks', ['org_id', 'status'])
    op.create_index('ix_tasks_assignee_status', 'tasks', ['assignee_id', 'status'])
    op.create_index('ix_tasks_proj_status', 'tasks', ['project_id', 'status'])

    # 10. task_updates (append-only)
    op.create_table(
        'task_updates',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_id', sa.String(length=36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('progress_pct', sa.Float(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('hours_logged', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_task_updates_task_created', 'task_updates', ['task_id', 'created_at'])

    # 11. timesheets
    op.create_table(
        'timesheets',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_id', sa.String(length=36), sa.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('hours', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('billable', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='draft', nullable=False),
        sa.Column('approved_by', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_timesheets_emp_date', 'timesheets', ['employee_id', 'work_date'])
    op.create_index('ix_timesheets_org_status', 'timesheets', ['org_id', 'status'])
    op.create_index('ix_timesheets_proj_date', 'timesheets', ['project_id', 'work_date'])

    # 12. login_sessions
    op.create_table(
        'login_sessions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_token_hash', sa.String(length=255), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=255), nullable=False),
        sa.Column('login_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('logout_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(length=100), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('os', sa.String(length=50), nullable=True),
        sa.Column('browser', sa.String(length=50), nullable=True),
        sa.Column('geo_city', sa.String(length=100), nullable=True),
        sa.Column('geo_country', sa.String(length=100), nullable=True),
        sa.Column('login_method', sa.String(length=50), server_default='password', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_login_sessions_emp_login', 'login_sessions', ['employee_id', 'login_at'])
    op.create_index('ix_login_sessions_org_active', 'login_sessions', ['org_id', 'is_active'])

    # 13. login_attempts
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('email_attempted', sa.String(length=255), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=100), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('os', sa.String(length=50), nullable=True),
        sa.Column('browser', sa.String(length=50), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_login_attempts_email_at', 'login_attempts', ['email_attempted', 'attempted_at'])
    op.create_index('ix_login_attempts_ip_at', 'login_attempts', ['ip_address', 'attempted_at'])

    # 14. attendance
    op.create_table(
        'attendance',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('first_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_logout_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_active_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('session_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='absent', nullable=False),
        sa.Column('is_late', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_attendance_emp_date', 'attendance', ['employee_id', 'work_date'], unique=True)
    op.create_index('ix_attendance_org_date', 'attendance', ['org_id', 'work_date'])

    # 15. audit_log (immutable)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=50), nullable=False),
        sa.Column('before_json', sa.JSON(), nullable=True),
        sa.Column('after_json', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_org_created', 'audit_log', ['org_id', 'created_at'])
    op.create_index('ix_audit_entity', 'audit_log', ['entity_type', 'entity_id'])

    # 16. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_notifications_recip_read', 'notifications', ['recipient_id', 'read_at'])

    # 17. leaves
    op.create_table(
        'leaves',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.String(length=36), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('leave_type', sa.String(length=50), server_default='vacation', nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='approved', nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_leaves_emp_dates', 'leaves', ['employee_id', 'start_date', 'end_date'])

    # 18. project_progress_snapshots
    op.create_table(
        'project_progress_snapshots',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('org_id', sa.String(length=36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('progress_pct', sa.Float(), nullable=False),
        sa.Column('spi', sa.Float(), nullable=False),
        sa.Column('effort_variance', sa.Float(), nullable=False),
        sa.Column('actual_hours', sa.Float(), nullable=False),
        sa.Column('estimated_hours', sa.Float(), nullable=False),
        sa.Column('remaining_story_points', sa.Integer(), nullable=False),
        sa.Column('health', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_snapshots_proj_date', 'project_progress_snapshots', ['project_id', 'snapshot_date'], unique=True)


def downgrade() -> None:
    tables = [
        'project_progress_snapshots', 'leaves', 'notifications', 'audit_log',
        'attendance', 'login_attempts', 'login_sessions', 'timesheets',
        'task_updates', 'tasks', 'milestones', 'project_members', 'projects',
        'employees', 'role_permissions', 'roles', 'permissions', 'organizations'
    ]
    for table in tables:
        op.drop_table(table)

