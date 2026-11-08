from datetime import date, datetime, timezone
from typing import List, Optional, Tuple, Dict, Any


def compute_task_progress(manual_progress_pct: float, subtasks: List[Dict[str, Any]]) -> float:
    """
    Task progress = manual progress_pct, or done/total subtasks if subtasks exist.
    """
    if not subtasks:
        return max(0.0, min(100.0, float(manual_progress_pct or 0.0)))

    total_subtasks = len(subtasks)
    if total_subtasks == 0:
        return 0.0

    done_subtasks = sum(1 for s in subtasks if s.get("status") == "done")
    return round((done_subtasks / total_subtasks) * 100.0, 2)


def compute_milestone_progress(tasks: List[Dict[str, Any]]) -> float:
    """
    Milestone progress = Σ(task.progress × task.story_points) / Σ(story_points)
    """
    if not tasks:
        return 0.0

    total_points = sum(max(1, t.get("story_points", 1)) for t in tasks)
    if total_points == 0:
        return 0.0

    weighted_progress = sum(
        t.get("progress_pct", 0.0) * max(1, t.get("story_points", 1))
        for t in tasks
    )
    return round(weighted_progress / total_points, 2)


def compute_project_progress(milestones: List[Dict[str, Any]]) -> float:
    """
    Project progress = Σ(milestone.progress × milestone.weight) / Σ(weight)
    """
    if not milestones:
        return 0.0

    total_weight = sum(max(0.1, m.get("weight", 1.0)) for m in milestones)
    if total_weight == 0:
        return 0.0

    weighted_progress = sum(
        m.get("progress_pct", 0.0) * max(0.1, m.get("weight", 1.0))
        for m in milestones
    )
    return round(weighted_progress / total_weight, 2)


def compute_elapsed_time_pct(start_date: date, target_end_date: date, current_date: Optional[date] = None) -> float:
    """
    Computes elapsed percentage between start_date and target_end_date.
    """
    if current_date is None:
        current_date = date.today()

    if target_end_date <= start_date:
        return 100.0

    total_days = (target_end_date - start_date).days
    elapsed_days = (current_date - start_date).days

    if elapsed_days <= 0:
        return 0.01  # Small positive to avoid division by zero
    if elapsed_days >= total_days:
        return 100.0

    return round((elapsed_days / total_days) * 100.0, 2)


def compute_spi(progress_pct: float, elapsed_time_pct: float) -> float:
    """
    Schedule Performance Index = progress_pct ÷ elapsed_time_pct
    """
    if elapsed_time_pct <= 0:
        return 1.0
    return round(progress_pct / elapsed_time_pct, 3)


def compute_effort_variance(actual_hours: float, estimated_hours: float) -> float:
    """
    Effort variance = (actual_hours − estimated_hours) ÷ estimated_hours
    """
    if estimated_hours <= 0:
        return 0.0
    return round((actual_hours - estimated_hours) / estimated_hours, 3)


def compute_project_health(
    spi: float,
    has_task_blocked_gt_3_days: bool,
    is_past_target_end_date_and_incomplete: bool
) -> str:
    """
    Health auto-flag:
    - RED if SPI < 0.85, or any task blocked > 3 days, or past target_end_date and not complete
    - AMBER if SPI 0.85–1.0
    - GREEN otherwise
    """
    if is_past_target_end_date_and_incomplete:
        return "red"
    if has_task_blocked_gt_3_days:
        return "red"
    if spi < 0.85:
        return "red"
    if 0.85 <= spi < 1.0:
        return "amber"
    return "green"

