import asyncio
import os
import re
from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, List, Optional
import openpyxl

from app.core.config import settings
from app.core.database import Base, engine, async_session_factory
from app.core.security import hash_password, hash_token
from app.models.organization import Organization
from app.models.role import Role, Permission, role_permissions
from app.models.employee import Employee
from app.models.project import Project, ProjectMember
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.task_update import TaskUpdate
from app.models.timesheet import Timesheet
from app.models.attendance import Attendance
from app.models.login_session import LoginSession
from app.models.project_snapshot import ProjectProgressSnapshot

PERMS = [
    "employee:create", "employee:read", "employee:delete",
    "project:create", "project:read", "project:update", "project:delete",
    "task:create", "task:read", "task:update", "task:delete",
    "timesheet:create", "timesheet:read", "timesheet:approve",
    "audit:read", "report:read", "notification:read"
]

ROLE_PERMS = {
    "admin": PERMS,
    "manager": [
        "employee:read", "project:create", "project:read", "project:update",
        "task:create", "task:read", "task:update", "task:delete",
        "timesheet:create", "timesheet:read", "timesheet:approve",
        "audit:read", "report:read", "notification:read"
    ],
    "team_lead": [
        "employee:read", "project:read", "task:create", "task:read",
        "task:update", "timesheet:create", "timesheet:read",
        "report:read", "notification:read"
    ],
    "member": [
        "project:read", "task:read", "task:update",
        "timesheet:create", "timesheet:read", "notification:read"
    ],
    "viewer": [
        "project:read", "task:read", "timesheet:read",
        "report:read", "notification:read"
    ],
}

TECH_SPECS = [
    ("Dheeraj", "dheeraj@example.com", "member"),
    ("Raghunath", "raghunath@example.com", "team_lead"),
    ("Harsha", "harsha@example.com", "member"),
    ("Hemanth", "hemanth@example.com", "member"),
    ("Saikumar", "saikumar@example.com", "member"),
    ("Sukumar", "sukumar@example.com", "member"),
    ("Manjunath", "manjunath@example.com", "member"),
    ("Hari Priya", "haripriya@example.com", "member"),
    ("Sai Priya", "saipriya@example.com", "member"),
    ("Vishal", "vishal@example.com", "member"),
    ("Sai Varshith", "varshith@example.com", "member"),
    ("Inayath Ali", "ali@example.com", "member"),
    ("Richard", "richard@example.com", "member"),
    ("Sanjay Reddy", "sanjay@example.com", "member"),
    ("Jayanth Reddy", "jayanth@example.com", "member"),
    ("Spoorthi", "spoorthi@example.com", "member"),
    ("Kalkesh", "kalkesh@example.com", "member"),
    ("Melvin", "melvin@example.com", "member"),
]


def parse_time_to_hours(val) -> float:
    if isinstance(val, time):
        return val.hour + val.minute / 60.0 + val.second / 3600.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        m = re.search(r"(\d+)\s*(?:hr|h)", val, re.I)
        hr = float(m.group(1)) if m else 0.0
        m2 = re.search(r"(\d+)\s*(?:min|m)", val, re.I)
        mn = float(m2.group(1)) if m2 else 0.0
        if hr or mn:
            return hr + mn / 60.0
    return 1.0


def normalize_status(raw) -> str:
    s = (str(raw) if raw else "").strip().lower()
    if s in ("closed", "completed", "resolved", "done"):
        return "done"
    if s in ("escalated", "blocked", "hold"):
        return "blocked"
    if s in ("in review", "review"):
        return "in_review"
    return "in_progress"


def normalize_priority(raw) -> tuple[str, int]:
    c = (str(raw) if raw else "").strip().lower()
    if c in ("extreme", "urgent", "critical"):
        return "urgent", 5
    if c == "high":
        return "high", 3
    if c == "medium":
        return "medium", 2
    return "low", 1


def map_owner_to_employee(raw_owner, emp_by_name: Dict[str, Employee], default_emp: Employee) -> Employee:
    if not raw_owner:
        return default_emp
    clean = str(raw_owner).strip()
    for name, emp in emp_by_name.items():
        if name.lower() in clean.lower():
            return emp
    token = re.split(r"[/, ]", clean)[0].strip().lower()
    for name, emp in emp_by_name.items():
        if token in name.lower() or name.lower() in token:
            return emp
    return default_emp


async def seed_database(excel_path: Optional[str] = None):
    print("=" * 70)
    print("STARTING UNIFIED SEED PROCESS")
    print("=" * 70)

    # 1. Ensure schema exists
    async with engine.begin() as conn:
        print("Ensuring database tables exist...")
        await conn.run_sync(Base.metadata.create_all)

    # Resolve excel path
    if not excel_path:
        candidates = [
            "Daily Ticket Tracker for Huntsville.xlsx",
            "../Daily Ticket Tracker for Huntsville.xlsx",
            r"C:\Users\kunig\OneDrive\Documentos\OPT\Service Global\ISG\Daily Ticket Tracker for Huntsville.xlsx"
        ]
        for c in candidates:
            if os.path.exists(c):
                excel_path = os.path.abspath(c)
                break

    async with async_session_factory() as session:
        # Create Organization
        org = Organization(
            name="Huntsville DC Ticket Operations",
            domain="huntsville.isg.local",
            settings_json={"timezone": "America/Chicago", "working_hours_per_day": 8.0}
        )
        session.add(org)
        await session.flush()
        print(f"Created organization: {org.name} ({org.id})")

        # Create Permissions
        perm_rows = {}
        for pcode in PERMS:
            p = Permission(code=pcode, description=f"Permission to {pcode}")
            session.add(p)
            await session.flush()
            perm_rows[pcode] = p

        # Create Roles
        role_rows = {}
        for rname, plist in ROLE_PERMS.items():
            r = Role(org_id=org.id, name=rname, description=f"Default {rname} role")
            r.permissions = [perm_rows[pcode] for pcode in plist]
            session.add(r)
            await session.flush()
            role_rows[rname] = r

        # Password hash (Argon2id)
        pw_hash = hash_password("ChangeMe123!")

        # System default accounts
        alice = Employee(
            org_id=org.id,
            employee_code="EMP-ADMIN",
            full_name="Alice Admin",
            email="admin@example.com",
            role_id=role_rows["admin"].id,
            department="Operations Management",
            designation="Administrator",
            location="Huntsville, AL",
            shift="general",
            date_of_joining=date(2024, 1, 1),
            password_hash=pw_hash,
            mfa_enabled=False
        )
        bob = Employee(
            org_id=org.id,
            employee_code="EMP-MGR",
            full_name="Bob Manager",
            email="manager@example.com",
            role_id=role_rows["manager"].id,
            department="Operations Management",
            designation="Operations Manager",
            location="Huntsville, AL",
            shift="general",
            date_of_joining=date(2024, 1, 1),
            password_hash=pw_hash,
            mfa_enabled=False
        )
        dave = Employee(
            org_id=org.id,
            employee_code="EMP-DEMO",
            full_name="Dave Member",
            email="member@example.com",
            role_id=role_rows["member"].id,
            department="Data Center Operations",
            designation="Data Center Technician",
            location="Huntsville, AL",
            shift="general",
            date_of_joining=date(2024, 2, 1),
            password_hash=pw_hash,
            mfa_enabled=False
        )
        ivan = Employee(
            org_id=org.id,
            employee_code="EMP-VIEW",
            full_name="Ivan Viewer",
            email="viewer@example.com",
            role_id=role_rows["viewer"].id,
            department="Data Center Operations",
            designation="Operations Auditor",
            location="Huntsville, AL",
            shift="general",
            date_of_joining=date(2024, 2, 1),
            password_hash=pw_hash,
            mfa_enabled=False
        )
        session.add_all([alice, bob, dave, ivan])
        await session.flush()

        alice.manager_id = bob.id
        bob.manager_id = alice.id
        dave.manager_id = bob.id
        ivan.manager_id = bob.id

        emp_by_name = {
            "Admin": alice,
            "Manager": bob,
            "Dave": dave,
            "Ivan": ivan,
            "Alice": alice,
            "Bob": bob
        }
        all_tech_employees = [dave]

        # Seed technicians
        for idx, (name, email, role_name) in enumerate(TECH_SPECS, start=1):
            code = f"HSV-T{idx:03d}"
            desig = "Lead DC Operations Engineer" if role_name == "team_lead" else "DC Fiber & Hardware Technician"
            emp = Employee(
                org_id=org.id,
                employee_code=code,
                full_name=name,
                email=email,
                role_id=role_rows[role_name].id,
                manager_id=bob.id,
                department="Huntsville Data Center Operations",
                designation=desig,
                location="Huntsville, AL",
                shift="general",
                date_of_joining=date(2024, 1, 15),
                password_hash=pw_hash,
                mfa_enabled=False
            )
            session.add(emp)
            await session.flush()
            emp_by_name[name] = emp
            all_tech_employees.append(emp)

        # Projects
        p1 = Project(
            org_id=org.id,
            code="HSV-TKT",
            name="Huntsville DC Ticket Operations",
            description="Daily datacenter operations, cable patching, hardware replacements, and circuit diagnostics.",
            client="Huntsville Data Center Campus",
            owner_id=bob.id,
            status="active",
            priority="high",
            start_date=date(2026, 9, 16),
            target_end_date=date(2026, 11, 15),
            budget_hours=4500.0,
            budget_cost=150000.0,
            health="green",
            progress_pct=88.0
        )
        p2 = Project(
            org_id=org.id,
            code="HSV-FIBER",
            name="Fiber Infrastructure & FCAN Maintenance",
            description="Multi-hall fiber optic testing, OTDR loopbacks, and FCAN backbone maintenance.",
            client="Internal Infrastructure Ops",
            owner_id=emp_by_name["Raghunath"].id,
            status="active",
            priority="medium",
            start_date=date(2026, 10, 1),
            target_end_date=date(2026, 12, 31),
            budget_hours=800.0,
            budget_cost=35000.0,
            health="green",
            progress_pct=65.0
        )
        p3 = Project(
            org_id=org.id,
            code="HSV-TOOL",
            name="Technician Tool Kit & Device Tracking",
            description="Tool checkout audits, optical power meter calibrations, and field device tracking.",
            client="Internal Quality & Compliance",
            owner_id=bob.id,
            status="completed",
            priority="low",
            start_date=date(2026, 9, 15),
            target_end_date=date(2026, 10, 31),
            actual_end_date=date(2026, 10, 31),
            budget_hours=300.0,
            budget_cost=12000.0,
            health="green",
            progress_pct=100.0
        )
        session.add_all([p1, p2, p3])
        await session.flush()

        for emp in all_tech_employees:
            session.add(ProjectMember(
                org_id=org.id,
                project_id=p1.id,
                employee_id=emp.id,
                role_on_project="Field Technician",
                allocation_pct=100.0,
                billable_rate=65.0
            ))
        await session.flush()

        # Milestones for HSV-TKT
        m_sep = Milestone(
            org_id=org.id,
            project_id=p1.id,
            name="September 2026 Ticket Queue",
            due_date=date(2026, 9, 30),
            status="completed",
            weight=1.0,
            progress_pct=100.0
        )
        m_oct = Milestone(
            org_id=org.id,
            project_id=p1.id,
            name="October 2026 Ticket Queue",
            due_date=date(2026, 10, 31),
            status="completed",
            weight=2.5,
            progress_pct=100.0
        )
        m_nov = Milestone(
            org_id=org.id,
            project_id=p1.id,
            name="November 2026 Ticket Queue",
            due_date=date(2026, 11, 15),
            status="in_progress",
            weight=1.0,
            progress_pct=95.0
        )
        session.add_all([m_sep, m_oct, m_nov])
        await session.flush()

        tasks_to_add = []
        timesheets_to_add = []
        attendance_map = {}

        if excel_path and os.path.exists(excel_path):
            print(f"Loading real Huntsville dataset from: {excel_path} ...")
            wb = openpyxl.load_workbook(excel_path, data_only=True)

            # 1. Parse 'Ticket report with Circuit' (Sep 16 - Oct 09)
            if 'Ticket report with Circuit' in wb.sheetnames:
                cir_sheet = wb['Ticket report with Circuit']
                print(f"Processing '{cir_sheet.title}' ...")
                for r in range(2, cir_sheet.max_row + 1):
                    dt_val = cir_sheet.cell(r, 1).value
                    tkt_no = cir_sheet.cell(r, 2).value
                    if not tkt_no:
                        continue
                    owner_raw = cir_sheet.cell(r, 3).value
                    raw_status = cir_sheet.cell(r, 4).value
                    data_hall = cir_sheet.cell(r, 5).value or "BDG 7"
                    circuit_no = cir_sheet.cell(r, 6).value
                    notes = cir_sheet.cell(r, 7).value
                    complexity = cir_sheet.cell(r, 8).value

                    work_date = dt_val.date() if isinstance(dt_val, datetime) else date(2026, 9, 20)
                    m_target = m_oct if work_date >= date(2026, 10, 1) else m_sep
                    status = normalize_status(raw_status)
                    priority, sp = normalize_priority(complexity)
                    hours = 0.5 if sp == 1 else (1.0 if sp == 2 else (1.5 if sp == 3 else 2.0))
                    assignee = map_owner_to_employee(owner_raw, emp_by_name, emp_by_name.get("Harsha", dave))

                    title = f"[{str(tkt_no).strip()}] {circuit_no or data_hall or 'Fiber Maintenance'}"
                    desc = f"Circuit: {circuit_no or 'N/A'}\nData Hall: {data_hall}\nNotes: {notes or 'Fiber connector / optic inspection'}"

                    task = Task(
                        org_id=org.id,
                        project_id=p1.id,
                        milestone_id=m_target.id,
                        title=title[:250],
                        description=desc,
                        assignee_id=assignee.id,
                        reporter_id=bob.id,
                        status=status,
                        priority=priority,
                        story_points=sp,
                        estimated_hours=hours,
                        actual_hours=hours,
                        progress_pct=100.0 if status == "done" else (0.0 if status == "blocked" else 50.0),
                        start_date=work_date,
                        due_date=work_date,
                        completed_at=datetime.combine(work_date, time(17, 0), tzinfo=timezone.utc) if status == "done" else None,
                        blocked_reason="Escalated ticket - awaiting cable or engineering review" if status == "blocked" else None,
                        blocked_at=datetime.combine(work_date, time(10, 0), tzinfo=timezone.utc) if status == "blocked" else None,
                        tags=[priority, str(data_hall).strip(), "Huntsville"]
                    )
                    tasks_to_add.append((task, assignee, work_date, hours, desc))

            # 2. Parse 'OCT - NOV Tracker' (Oct 12 - Nov 06)
            if 'OCT - NOV Tracker' in wb.sheetnames:
                oct_sheet = wb['OCT - NOV Tracker']
                print(f"Processing '{oct_sheet.title}' ...")
                for r in range(2, oct_sheet.max_row + 1):
                    dt_val = oct_sheet.cell(r, 1).value
                    tkt_no = oct_sheet.cell(r, 6).value
                    if not tkt_no:
                        continue
                    spent_raw = oct_sheet.cell(r, 5).value
                    owner_raw = oct_sheet.cell(r, 7).value
                    complexity = oct_sheet.cell(r, 8).value
                    raw_status = oct_sheet.cell(r, 9).value
                    notes = oct_sheet.cell(r, 10).value
                    data_hall = oct_sheet.cell(r, 11).value or "C"
                    circuit_no = oct_sheet.cell(r, 12).value
                    threshold_reason = oct_sheet.cell(r, 13).value

                    work_date = dt_val.date() if isinstance(dt_val, datetime) else date(2026, 10, 20)
                    m_target = m_nov if work_date >= date(2026, 11, 1) else m_oct
                    status = normalize_status(raw_status)
                    priority, sp = normalize_priority(complexity)
                    hours = parse_time_to_hours(spent_raw)
                    assignee = map_owner_to_employee(owner_raw, emp_by_name, emp_by_name.get("Hari Priya", dave))

                    title = f"[{str(tkt_no).strip()}] {circuit_no or f'Data Hall {data_hall} Ticket'}"
                    desc = f"Circuit: {circuit_no or 'N/A'}\nData Hall: {data_hall}\nNotes: {notes or 'N/A'}\nThreshold: {threshold_reason or 'Within SLA'}"

                    task = Task(
                        org_id=org.id,
                        project_id=p1.id,
                        milestone_id=m_target.id,
                        title=title[:250],
                        description=desc,
                        assignee_id=assignee.id,
                        reporter_id=bob.id,
                        status=status,
                        priority=priority,
                        story_points=sp,
                        estimated_hours=hours,
                        actual_hours=hours,
                        progress_pct=100.0 if status == "done" else (0.0 if status == "blocked" else 50.0),
                        start_date=work_date,
                        due_date=work_date,
                        completed_at=datetime.combine(work_date, time(17, 0), tzinfo=timezone.utc) if status == "done" else None,
                        blocked_reason=str(notes or threshold_reason or "Escalated to engineering")[:300] if status == "blocked" else None,
                        blocked_at=datetime.combine(work_date, time(9, 30), tzinfo=timezone.utc) if status == "blocked" else None,
                        tags=[priority, f"Hall-{str(data_hall).strip()}", "Huntsville"]
                    )
                    tasks_to_add.append((task, assignee, work_date, hours, desc))

            # 3. Import daily progress snapshots from 'Ticket Overview'
            if 'Ticket Overview' in wb.sheetnames:
                ov_sheet = wb['Ticket Overview']
                print(f"Processing '{ov_sheet.title}' daily snapshots...")
                cum_actual_hours = 0.0
                for r in range(6, ov_sheet.max_row + 1):
                    d_val = ov_sheet.cell(r, 1).value
                    if not d_val:
                        continue
                    snap_date = d_val.date() if isinstance(d_val, datetime) else None
                    if not snap_date:
                        continue
                    worked = ov_sheet.cell(r, 2).value or 0
                    closed = ov_sheet.cell(r, 3).value or 0
                    escalated = ov_sheet.cell(r, 4).value or 0

                    prog_pct = round((closed / worked * 100.0) if worked > 0 else 0.0, 1)
                    spi = round((prog_pct / 90.0), 2)
                    cum_actual_hours += (worked * 1.2)
                    variance = 0.02
                    health = "green" if spi >= 0.9 else ("amber" if spi >= 0.8 else "red")

                    snap = ProjectProgressSnapshot(
                        org_id=org.id,
                        project_id=p1.id,
                        snapshot_date=snap_date,
                        progress_pct=prog_pct,
                        spi=min(spi, 1.2),
                        effort_variance=variance,
                        actual_hours=round(cum_actual_hours, 1),
                        estimated_hours=round(cum_actual_hours * 1.05, 1),
                        remaining_story_points=int(escalated * 3),
                        health=health
                    )
                    session.add(snap)
        else:
            print("No Excel file found. Generating 40 standard sample tasks...")
            # Sample fallback tasks
            for i in range(1, 41):
                st = "done" if i <= 25 else ("in_progress" if i <= 35 else "blocked")
                pr = "urgent" if i % 10 == 0 else ("high" if i % 4 == 0 else "medium")
                sp = 5 if pr == "urgent" else (3 if pr == "high" else 2)
                tech = all_tech_employees[i % len(all_tech_employees)]
                dt = date(2026, 10, 1) + timedelta(days=(i % 30))
                t = Task(
                    org_id=org.id,
                    project_id=p1.id,
                    milestone_id=m_oct.id,
                    title=f"Sample Ticket #{1000 + i}: Data Center Fiber Inspection",
                    description=f"Standard ticket maintenance inspection #{i}",
                    assignee_id=tech.id,
                    reporter_id=bob.id,
                    status=st,
                    priority=pr,
                    story_points=sp,
                    estimated_hours=float(sp),
                    actual_hours=float(sp) if st == "done" else float(sp) * 0.5,
                    progress_pct=100.0 if st == "done" else (0.0 if st == "blocked" else 50.0),
                    start_date=dt,
                    due_date=dt + timedelta(days=2),
                    completed_at=datetime.combine(dt, time(17, 0), tzinfo=timezone.utc) if st == "done" else None,
                    blocked_reason="Awaiting spares" if st == "blocked" else None,
                    tags=["sample", pr, "datacenter"]
                )
                tasks_to_add.append((t, tech, dt, float(sp), t.description))

        print(f"Total tasks to insert: {len(tasks_to_add)}")

        # Bulk insert tasks in chunks
        for i in range(0, len(tasks_to_add), 500):
            chunk = [item[0] for item in tasks_to_add[i:i+500]]
            session.add_all(chunk)
            await session.flush()

        # Build timesheets & attendance records
        print("Generating timesheets & attendance records...")
        for task, assignee, work_date, hours, desc in tasks_to_add:
            ts = Timesheet(
                org_id=org.id,
                employee_id=assignee.id,
                project_id=p1.id,
                task_id=task.id,
                work_date=work_date,
                hours=min(hours, 8.0),
                description=f"Work on {task.title[:100]}",
                billable=True,
                status="approved" if work_date < date(2026, 11, 4) else "submitted",
                approved_by=bob.id if work_date < date(2026, 11, 4) else None,
                approved_at=datetime.combine(work_date + timedelta(days=1), time(10, 0), tzinfo=timezone.utc) if work_date < date(2026, 11, 4) else None
            )
            timesheets_to_add.append(ts)

            att_key = (assignee.id, work_date)
            if att_key not in attendance_map:
                attendance_map[att_key] = {
                    "hours": 0.0,
                    "count": 0,
                    "first_time": datetime.combine(work_date, time(8, 45), tzinfo=timezone.utc),
                    "last_time": datetime.combine(work_date, time(17, 30), tzinfo=timezone.utc),
                }
            attendance_map[att_key]["hours"] += hours
            attendance_map[att_key]["count"] += 1

        for i in range(0, len(timesheets_to_add), 500):
            session.add_all(timesheets_to_add[i:i+500])
            await session.flush()

        for (emp_id, work_date), data in attendance_map.items():
            total_mins = int(min(data["hours"], 10.0) * 60)
            att = Attendance(
                org_id=org.id,
                employee_id=emp_id,
                work_date=work_date,
                first_login_at=data["first_time"],
                last_logout_at=data["last_time"],
                total_active_minutes=total_mins,
                session_count=data["count"],
                status="present",
                is_late=False
            )
            session.add(att)

        # Active login sessions for Alice, Bob, and Tech Leads
        for user in [alice, bob, emp_by_name.get("Raghunath", dave), emp_by_name.get("Hari Priya", dave)]:
            session.add(LoginSession(
                org_id=org.id,
                employee_id=user.id,
                session_token_hash=hash_token(f"session-{user.id}"),
                refresh_token_hash=hash_token(f"refresh-{user.id}"),
                ip_address="127.0.0.1",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                device_type="Desktop",
                os="Windows",
                browser="Chrome",
                login_method="password",
                is_active=True,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            ))

        await session.commit()

    print("=" * 70)
    print("DATABASE SEED COMPLETED SUCCESSFULLY")
    print(f"- Org: {org.name}")
    print(f"- Employees: {len(emp_by_name)}")
    print(f"- Tasks created: {len(tasks_to_add)}")
    print(f"- Timesheets created: {len(timesheets_to_add)}")
    print(f"- Attendance daily rows: {len(attendance_map)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_database())
