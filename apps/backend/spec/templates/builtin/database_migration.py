"""
Database Migration Template
============================

Template for database schema migrations.
"""

from typing import Any, Dict

from ..registry import Template


class DatabaseMigrationTemplate(Template):
    """Template for database migration implementation."""

    def __init__(self):
        """Initialize the database migration template."""
        super().__init__(
            name="database_migration",
            description="Create database schema migration with rollback support",
            category="database",
            parameters={
                "migration_type": {
                    "type": str,
                    "required": True,
                    "description": "Type of migration (create_table, alter_table, add_column, drop_column, add_index)",
                },
                "table_name": {
                    "type": str,
                    "required": True,
                    "description": "Name of the database table",
                },
                "changes": {
                    "type": list,
                    "required": True,
                    "description": "List of changes to apply (e.g., ['add column email varchar(255)', 'add index on email'])",
                },
                "data_migration": {
                    "type": bool,
                    "required": False,
                    "default": False,
                    "description": "Whether migration includes data transformation",
                },
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate database migration spec from parameters."""
        migration_type = params["migration_type"]
        table_name = params["table_name"]
        changes = params["changes"]
        data_migration = params.get("data_migration", False)

        changes_str = "\n".join([f"- {change}" for change in changes])

        return {
            "title": f"Database Migration: {migration_type.replace('_', ' ').title()} for {table_name}",
            "description": f"Database schema migration to {migration_type.replace('_', ' ')} on the {table_name} table.",
            "rationale": f"Update database schema to support new feature requirements or fix existing schema issues in the {table_name} table.",
            "user_stories": [
                "As a developer, I want to apply schema changes safely",
                "As a developer, I want to rollback if migration fails",
                "As an operator, I want to track migration history",
            ],
            "acceptance_criteria": [
                f"Migration script applies {migration_type} to {table_name} table",
                "Rollback script reverses all changes",
                "Migration is idempotent (can be run multiple times safely)",
                "Migration is tracked in schema version history",
                "Zero downtime for production deployment",
                "All existing data preserved" + (" and transformed correctly" if data_migration else ""),
            ],
            "technical_details": f"""
### Migration Details

**Migration Type:** {migration_type}
**Table:** {table_name}

### Changes to Apply

{changes_str}

### Migration Script (Up)

```sql
-- Apply changes
{self._generate_sample_up_migration(migration_type, table_name, changes)}
```

### Rollback Script (Down)

```sql
-- Revert changes
{self._generate_sample_down_migration(migration_type, table_name, changes)}
```

### Deployment Strategy

1. Backup database before migration
2. Run migration in transaction (if database supports)
3. Verify data integrity after migration
4. Test rollback procedure in staging
5. Monitor performance impact

### Compatibility

- Ensure backward compatibility with running application code
{"- Data transformation preserves referential integrity" if data_migration else ""}
- Index creation runs in background (non-blocking)

### Risk Assessment

{"- **HIGH RISK**: Data migration involves transformation" if data_migration else "- **MEDIUM RISK**: Schema change only"}
- Test thoroughly in staging environment
- Plan maintenance window if needed
""",
            "test_coverage": [
                "Test migration runs successfully on empty database",
                "Test migration runs successfully on database with existing data",
                "Test rollback procedure",
                "Test migration idempotency (run twice)",
                "Verify data integrity after migration",
                "Performance tests for large tables",
            ] + (["Test data transformation logic"] if data_migration else []),
        }

    def _generate_sample_up_migration(self, migration_type: str, table_name: str, changes: list) -> str:
        """Generate sample SQL for up migration."""
        if migration_type == "create_table":
            return f"CREATE TABLE {table_name} (\n  id SERIAL PRIMARY KEY,\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);"
        elif migration_type == "add_column":
            return f"ALTER TABLE {table_name} ADD COLUMN {changes[0] if changes else 'new_column VARCHAR(255)'};"
        elif migration_type == "drop_column":
            return f"ALTER TABLE {table_name} DROP COLUMN {changes[0].split()[0] if changes else 'old_column'};"
        elif migration_type == "add_index":
            return f"CREATE INDEX idx_{table_name}_{changes[0].split()[0] if changes else 'column'} ON {table_name}({changes[0].split()[0] if changes else 'column'});"
        else:
            return f"-- {migration_type} on {table_name}\n-- Add your SQL here"

    def _generate_sample_down_migration(self, migration_type: str, table_name: str, changes: list) -> str:
        """Generate sample SQL for down migration."""
        if migration_type == "create_table":
            return f"DROP TABLE {table_name};"
        elif migration_type == "add_column":
            return f"ALTER TABLE {table_name} DROP COLUMN {changes[0].split()[0] if changes else 'new_column'};"
        elif migration_type == "drop_column":
            return f"ALTER TABLE {table_name} ADD COLUMN {changes[0] if changes else 'old_column VARCHAR(255)'};"
        elif migration_type == "add_index":
            return f"DROP INDEX idx_{table_name}_{changes[0].split()[0] if changes else 'column'};"
        else:
            return f"-- Rollback {migration_type} on {table_name}\n-- Add your rollback SQL here"
