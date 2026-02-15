"""
Recovery Notification Module
==============================

User notifications for recovery events and manual intervention needs.

Notifies users when:
- Subtasks get stuck and need manual intervention
- Recovery attempts are being made
- Rollback actions are performed
- Escalation to human is needed
"""

from pathlib import Path

from ui import (
    Icons,
    bold,
    box,
    error,
    highlight,
    icon,
    muted,
    print_key_value,
    print_status,
    warning,
)


def notify_stuck_subtask(
    subtask_id: str,
    reason: str,
    attempt_count: int,
    spec_dir: Path | None = None,
) -> None:
    """
    Notify user that a subtask is stuck and needs manual intervention.

    Args:
        subtask_id: ID of the stuck subtask
        reason: Why the subtask is stuck
        attempt_count: Number of attempts made
        spec_dir: Optional spec directory for additional context
    """
    print()
    print(
        box(
            [
                f"{icon(Icons.WARNING)} {bold('Subtask Stuck - Manual Intervention Required')}",
                "",
                f"Subtask {highlight(subtask_id)} requires your attention.",
            ],
            width=70,
            style="heavy",
        )
    )
    print()

    print_key_value("Subtask ID", subtask_id)
    print_key_value("Attempts Made", str(attempt_count))
    print_key_value("Reason", reason)

    if spec_dir:
        print_key_value("Spec Location", str(spec_dir))

    print()
    print(muted("  The agent will pause after completing other subtasks."))
    print(
        muted("  Please review the issue and either fix manually or skip this subtask.")
    )
    print()


def notify_recovery_attempt(
    subtask_id: str,
    attempt_number: int,
    max_attempts: int,
    approach: str,
) -> None:
    """
    Notify user that a recovery attempt is being made.

    Args:
        subtask_id: ID of the subtask being retried
        attempt_number: Current attempt number
        max_attempts: Maximum number of attempts allowed
        approach: Description of the recovery approach
    """
    print_status(
        f"Recovery attempt {attempt_number}/{max_attempts} for {highlight(subtask_id)}",
        "progress",
    )
    print_key_value("Approach", approach, indent=4)
    print()


def notify_rollback(
    target_commit: str,
    reason: str,
    subtask_id: str | None = None,
) -> None:
    """
    Notify user that a rollback is being performed.

    Args:
        target_commit: Commit hash being rolled back to
        reason: Why rollback is needed
        subtask_id: Optional subtask ID that triggered rollback
    """
    print()
    print(
        box(
            [
                f"{icon(Icons.WARNING)} {bold('Rolling Back to Last Good State')}",
                "",
                muted(reason),
            ],
            width=70,
            style="light",
        )
    )
    print()

    print_key_value("Target Commit", target_commit[:8])
    if subtask_id:
        print_key_value("Failed Subtask", subtask_id)
    print_key_value("Reason", reason)

    print()
    print(warning("  Work will be restored to the last working state."))
    print(muted("  Failed changes will be discarded."))
    print()


def notify_escalation(
    subtask_id: str,
    reason: str,
    history: list[dict] | None = None,
) -> None:
    """
    Notify user that a subtask is being escalated for manual intervention.

    Args:
        subtask_id: ID of the subtask being escalated
        reason: Why escalation is needed
        history: Optional attempt history for context
    """
    print()
    print(
        box(
            [
                f"{icon(Icons.ERROR)} {bold('Escalation Required')}",
                "",
                f"Unable to complete {highlight(subtask_id)} automatically.",
            ],
            width=70,
            style="heavy",
        )
    )
    print()

    print_key_value("Subtask ID", subtask_id)
    print_key_value("Escalation Reason", reason)

    if history and len(history) > 0:
        print()
        print(f"  {bold('Previous Attempts:')}")
        for i, attempt in enumerate(history[-3:], 1):
            status_text = "✓ SUCCESS" if attempt.get("success") else "✗ FAILED"
            print(
                f"    {muted(str(i) + '.')} {attempt.get('approach', 'Unknown')} - {status_text}"
            )
            if attempt.get("error") and not attempt.get("success"):
                error_snippet = attempt["error"][:80]
                print(f"       {muted('Error:')} {error(error_snippet)}")

    print()
    print(error("  ⚠️  Agent will skip this subtask and continue with others."))
    print(muted("  Please review and complete manually or adjust the spec."))
    print()


def notify_circular_fix_detected(
    subtask_id: str,
    similar_approaches: list[str],
) -> None:
    """
    Notify user that a circular fix pattern has been detected.

    Args:
        subtask_id: ID of the subtask with circular fixes
        similar_approaches: List of similar approaches that were tried
    """
    print()
    print(
        box(
            [
                f"{icon(Icons.WARNING)} {bold('Circular Fix Detected')}",
                "",
                f"Subtask {highlight(subtask_id)} is repeating similar approaches.",
            ],
            width=70,
            style="light",
        )
    )
    print()

    print_key_value("Subtask ID", subtask_id)
    print()
    print(f"  {bold('Recent Similar Approaches:')}")
    for i, approach in enumerate(similar_approaches[-3:], 1):
        print(f"    {muted(str(i) + '.')} {approach}")

    print()
    print(warning("  ⚠️  Agent will try a different approach or escalate."))
    print()


def notify_context_exhausted(
    subtask_id: str,
    will_commit: bool = True,
) -> None:
    """
    Notify user that context has been exhausted mid-subtask.

    Args:
        subtask_id: ID of the current subtask
        will_commit: Whether progress will be committed
    """
    print_status(
        f"Context exhausted during {highlight(subtask_id)}",
        "warning",
    )

    if will_commit:
        print(
            muted(
                "  → Committing progress and continuing in next session with fresh context"
            )
        )
    else:
        print(muted("  → Will continue in next session with fresh context"))

    print()
