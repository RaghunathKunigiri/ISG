from datetime import date, timedelta
import pytest
from app.services.progress_service import (
    compute_task_progress,
    compute_milestone_progress,
    compute_project_progress,
    compute_elapsed_time_pct,
    compute_spi,
    compute_effort_variance,
    compute_project_health,
)


def test_task_progress_manual():
    # If no subtasks, uses manual progress_pct bounded [0, 100]
    assert compute_task_progress(50.0, []) == 50.0
    assert compute_task_progress(150.0, []) == 100.0
    assert compute_task_progress(-20.0, []) == 0.0


def test_task_progress_with_subtasks():
    # Subtasks: done / total subtasks
    subtasks = [
        {"id": "1", "status": "done"},
        {"id": "2", "status": "in_progress"},
        {"id": "3", "status": "done"},
        {"id": "4", "status": "todo"},
    ]
    # 2 out of 4 done = 50.0%
    assert compute_task_progress(0.0, subtasks) == 50.0

    all_done = [{"status": "done"}, {"status": "done"}]
    assert compute_task_progress(10.0, all_done) == 100.0


def test_milestone_progress_weighted_by_story_points():
    # Milestone progress = Σ(task.progress × task.story_points) / Σ(story_points)
    tasks = [
        {"progress_pct": 100.0, "story_points": 3},  # 300
        {"progress_pct": 50.0, "story_points": 5},   # 250
        {"progress_pct": 0.0, "story_points": 2},    # 0
    ]
    # Total story points: 3 + 5 + 2 = 10
    # Weighted sum: 300 + 250 + 0 = 550
    # Expected milestone progress: 550 / 10 = 55.0%
    assert compute_milestone_progress(tasks) == 55.0


def test_project_progress_weighted_by_milestone_weights():
    # Project progress = Σ(milestone.progress × milestone.weight) / Σ(weight)
    milestones = [
        {"progress_pct": 100.0, "weight": 1.0},  # 100
        {"progress_pct": 50.0, "weight": 2.0},   # 100
        {"progress_pct": 0.0, "weight": 1.0},    # 0
    ]
    # Total weight: 1.0 + 2.0 + 1.0 = 4.0
    # Weighted sum: 100 + 100 + 0 = 200
    # Expected: 200 / 4.0 = 50.0%
    assert compute_project_progress(milestones) == 50.0


def test_schedule_performance_index_and_effort_variance():
    # Elapsed 50%, Progress 45% -> SPI = 45 / 50 = 0.90
    spi = compute_spi(progress_pct=45.0, elapsed_time_pct=50.0)
    assert spi == 0.90

    # Effort variance = (actual - estimated) / estimated
    # Actual 120h, Estimated 100h -> (120 - 100) / 100 = 0.20 (+20% variance)
    ev = compute_effort_variance(actual_hours=120.0, estimated_hours=100.0)
    assert ev == 0.20

    # Under budget: Actual 80h, Estimated 100h -> -0.20
    ev_under = compute_effort_variance(actual_hours=80.0, estimated_hours=100.0)
    assert ev_under == -0.20


def test_health_auto_flag_conditions():
    # Red conditions:
    # 1. SPI < 0.85
    assert compute_project_health(spi=0.80, has_task_blocked_gt_3_days=False, is_past_target_end_date_and_incomplete=False) == "red"

    # 2. Any task blocked > 3 days
    assert compute_project_health(spi=0.95, has_task_blocked_gt_3_days=True, is_past_target_end_date_and_incomplete=False) == "red"

    # 3. Past target_end_date and not complete
    assert compute_project_health(spi=1.1, has_task_blocked_gt_3_days=False, is_past_target_end_date_and_incomplete=True) == "red"

    # Amber condition: 0.85 <= SPI < 1.0
    assert compute_project_health(spi=0.88, has_task_blocked_gt_3_days=False, is_past_target_end_date_and_incomplete=False) == "amber"
    assert compute_project_health(spi=0.99, has_task_blocked_gt_3_days=False, is_past_target_end_date_and_incomplete=False) == "amber"

    # Green condition: SPI >= 1.0, no blocker > 3d, not overdue
    assert compute_project_health(spi=1.05, has_task_blocked_gt_3_days=False, is_past_target_end_date_and_incomplete=False) == "green"

