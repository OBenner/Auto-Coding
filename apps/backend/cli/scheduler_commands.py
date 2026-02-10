"""
Scheduler Commands
==================

Commands for scheduling builds and managing the build queue.
"""

import uuid
from datetime import datetime
from pathlib import Path

from scheduler.models import ScheduledBuild, SchedulePriority
from scheduler.scheduler import Scheduler
from ui import print_status


def handle_schedule_command(
    spec_id: str,
    project_dir: str,
    scheduled_time: str | None = None,
    priority: str = "normal",
    dependencies: list[str] | None = None,
) -> bool:
    """
    Schedule a build for a specific spec.

    Args:
        spec_id: Spec ID to schedule (e.g., '001' or '001-feature-name')
        project_dir: Project directory
        scheduled_time: Optional scheduled time (ISO format or 'tonight 10pm')
        priority: Build priority (low, normal, high, urgent)
        dependencies: List of spec IDs this build depends on

    Returns:
        True if successful
    """
    spec_dir = Path(project_dir) / ".auto-claude" / "specs"
    spec_path = None

    # Find spec directory
    for s in spec_dir.iterdir():
        if s.is_dir() and s.name.startswith(spec_id):
            spec_path = s
            break

    if not spec_path:
        print_status(f"Spec '{spec_id}' not found", "error")
        return False

    # Parse priority
    priority_map = {
        "low": SchedulePriority.LOW,
        "normal": SchedulePriority.NORMAL,
        "high": SchedulePriority.HIGH,
        "urgent": SchedulePriority.CRITICAL,
    }
    build_priority = priority_map.get(priority.lower(), SchedulePriority.NORMAL)

    # Parse scheduled time
    parsed_time = None
    if scheduled_time:
        try:
            # Try ISO format first
            parsed_time = datetime.fromisoformat(scheduled_time)
        except ValueError:
            # Try natural language (simple parsing)
            scheduled_time_lower = scheduled_time.lower()
            if "tonight" in scheduled_time_lower:
                # Parse time like "tonight 10pm"
                time_part = scheduled_time_lower.replace("tonight", "").strip()
                today = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                if "am" in time_part or "pm" in time_part:
                    hour = int(time_part.replace("am", "").replace("pm", "").strip())
                    if "pm" in time_part and hour != 12:
                        hour += 12
                    parsed_time = today.replace(hour=hour)
            else:
                print_status(
                    f"Could not parse scheduled time: {scheduled_time}", "error"
                )
                print_status(
                    "Use ISO format (e.g., 2026-02-08T22:00) or 'tonight 10pm'", "info"
                )
                return False

    # Create scheduled build
    build = ScheduledBuild(
        id=str(uuid.uuid4()),
        spec_id=spec_path.name,
        spec_name=spec_path.name,
        priority=build_priority,
        scheduled_time=parsed_time,
        dependencies=dependencies or [],
    )

    # Schedule using scheduler
    scheduler = Scheduler(project_dir)
    success = scheduler.schedule_build(build)

    if success:
        time_str = parsed_time.isoformat() if parsed_time else "immediate"
        deps_str = f" (deps: {', '.join(dependencies)})" if dependencies else ""
        print_status(
            f"Scheduled {spec_path.name} for {time_str}{deps_str} (priority: {priority})",
            "success",
        )
    else:
        print_status(f"Failed to schedule {spec_id}", "error")

    return success


def handle_schedule_status_command(project_dir: str) -> bool:
    """
    Show status of scheduled builds.

    Args:
        project_dir: Project directory

    Returns:
        True if successful
    """
    scheduler = Scheduler(project_dir)
    status = scheduler.get_queue_status()

    print_status("Scheduler Status", "info")
    print()

    running = "Running" if status["scheduler_running"] else "Stopped"
    print(f"Scheduler: {running}")
    print(f"Total builds: {status['total_builds']}")
    print()

    # Show builds by status
    for build_status, count in status["by_status"].items():
        if count > 0:
            icon = {
                "pending": "⏳",
                "queued": "📋",
                "running": "⚙️",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
            }.get(build_status, "•")
            print(f"{icon} {build_status.capitalize()}: {count}")

    print()

    # Show next build
    next_build = scheduler.get_next_scheduled_build()
    if next_build:
        time_str = (
            next_build.scheduled_time.isoformat()
            if next_build.scheduled_time
            else "immediate"
        )
        deps_str = (
            f" (deps: {', '.join(next_build.dependencies)})"
            if next_build.dependencies
            else ""
        )
        print_status(f"Next: {next_build.spec_id} at {time_str}{deps_str}", "info")
    else:
        print_status("No builds in queue", "info")

    return True


def handle_schedule_cancel_command(build_id: str, project_dir: str) -> bool:
    """
    Cancel a scheduled build.

    Args:
        build_id: Build ID to cancel
        project_dir: Project directory

    Returns:
        True if successful
    """
    scheduler = Scheduler(project_dir)
    success = scheduler.cancel_build(build_id)

    if success:
        print_status(f"Cancelled build {build_id}", "success")
    else:
        print_status(f"Failed to cancel build {build_id}", "error")

    return success


def handle_schedule_start_command(project_dir: str) -> bool:
    """
    Start the scheduler service.

    Args:
        project_dir: Project directory

    Returns:
        True if successful
    """
    scheduler = Scheduler(project_dir)
    success = scheduler.start()

    if success:
        print_status("Scheduler started", "success")
        print_status("Builds will execute automatically based on schedule", "info")
    else:
        print_status("Scheduler is already running", "warning")

    return success


def handle_schedule_stop_command(project_dir: str) -> bool:
    """
    Stop the scheduler service.

    Args:
        project_dir: Project directory

    Returns:
        True if successful
    """
    scheduler = Scheduler(project_dir)
    success = scheduler.stop()

    if success:
        print_status("Scheduler stopped", "success")
    else:
        print_status("Scheduler is not running", "warning")

    return success
