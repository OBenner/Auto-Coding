"""
Spec index sync (Track C — C4): mirror the FS spec listing into the DB.

The filesystem is the source of truth; ``sync_specs_index`` diffs the current
FS listing against ``SpecRecord`` rows for one workspace and appends
``SpecAuditEntry`` rows for every observed change (created / updated /
deleted / restored). Sync is called from the listing route through the
best-effort wrapper — an index failure must never break the listing itself.
"""

import logging
from datetime import UTC, datetime

from api.models.spec_record import SpecAuditEntry, SpecRecord
from core import sanitize_log
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Fields mirrored from the FS listing; a change in any of them is an 'updated'.
_MIRRORED_FIELDS = ("number", "name", "status", "progress", "has_build")


def _audit(db: Session, record: SpecRecord, action: str, detail: str | None) -> None:
    db.add(
        SpecAuditEntry(spec_record_id=record.id, action=action, detail=detail)
    )


def _normalized(spec: dict, field: str):
    """Normalize one FS-listing value to the SpecRecord column type."""
    value = spec.get(field)
    if field == "has_build":
        return bool(value)
    return str(value if value is not None else "")


def _create_record(
    db: Session, workspace_id: int, spec: dict, now: datetime
) -> SpecRecord:
    """Insert a new SpecRecord from an FS listing entry (audited as 'created')."""
    record = SpecRecord(
        workspace_id=workspace_id,
        folder=spec["folder"],
        number=_normalized(spec, "number"),
        name=_normalized(spec, "name"),
        status=_normalized(spec, "status"),
        progress=_normalized(spec, "progress"),
        has_build=_normalized(spec, "has_build"),
        last_synced_at=now,
    )
    db.add(record)
    db.flush()  # assign record.id for the audit row
    _audit(db, record, "created", None)
    return record


def _apply_field_changes(record: SpecRecord, spec: dict) -> list[str]:
    """Copy changed mirrored fields onto the record; return change summaries."""
    changes: list[str] = []
    for field in _MIRRORED_FIELDS:
        new_value = _normalized(spec, field)
        old_value = getattr(record, field)
        if old_value != new_value:
            changes.append(f"{field}: {old_value} -> {new_value}")
            setattr(record, field, new_value)
    return changes


def sync_specs_index(
    db: Session, workspace_id: int, specs: list[dict]
) -> dict[str, int]:
    """Diff the FS listing against the workspace's SpecRecords and audit changes.

    Returns counters {'created': n, 'updated': n, 'deleted': n} (restores count
    as 'created'). ``last_synced_at`` is bumped only on change to avoid one
    UPDATE per row on every listing.
    """
    now = datetime.now(UTC)
    counters = {"created": 0, "updated": 0, "deleted": 0}

    existing = {
        r.folder: r
        for r in db.query(SpecRecord)
        .filter(SpecRecord.workspace_id == workspace_id)
        .all()
    }
    seen: set[str] = set()

    for spec in specs:
        folder = spec.get("folder")
        if not folder:
            continue
        seen.add(folder)
        record = existing.get(folder)

        if record is None:
            _create_record(db, workspace_id, spec, now)
            counters["created"] += 1
            continue

        changes = _apply_field_changes(record, spec)

        if record.deleted_at is not None:
            # The folder reappeared on the FS after being deleted.
            record.deleted_at = None
            record.last_synced_at = now
            _audit(db, record, "created", "restored from filesystem")
            counters["created"] += 1
        elif changes:
            record.last_synced_at = now
            _audit(db, record, "updated", "; ".join(changes)[:500])
            counters["updated"] += 1

    # Anything in the DB but gone from the FS is a deletion (FS is the truth).
    for folder, record in existing.items():
        if folder in seen or record.deleted_at is not None:
            continue
        record.deleted_at = now
        record.last_synced_at = now
        _audit(db, record, "deleted", None)
        counters["deleted"] += 1

    db.commit()
    return counters


def sync_specs_index_safely(
    db: Session, workspace_id: int, specs: list[dict]
) -> None:
    """Best-effort sync for the listing route: log failures, never raise."""
    try:
        sync_specs_index(db, workspace_id, specs)
    except Exception:
        db.rollback()
        # workspace_id is request-derived; sanitize before logging (CodeQL).
        logger.warning(
            "Spec index sync failed for workspace %s",
            sanitize_log(str(workspace_id)),
            exc_info=True,
        )


def get_spec_record(
    db: Session, workspace_id: int, spec_id: str
) -> SpecRecord | None:
    """Find a workspace's SpecRecord by exact folder name or by spec number."""
    record = (
        db.query(SpecRecord)
        .filter(
            SpecRecord.workspace_id == workspace_id,
            SpecRecord.folder == spec_id,
        )
        .first()
    )
    if record is not None:
        return record
    return (
        db.query(SpecRecord)
        .filter(
            SpecRecord.workspace_id == workspace_id,
            SpecRecord.number == spec_id,
        )
        .order_by(SpecRecord.id.asc())
        .first()
    )
