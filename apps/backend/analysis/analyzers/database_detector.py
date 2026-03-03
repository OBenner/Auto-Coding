"""
Database Detector Module
========================

Detects database models and schemas across different ORMs:
- Python: SQLAlchemy, Django ORM
- JavaScript/TypeScript: Prisma, TypeORM, Drizzle, Mongoose
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import BaseAnalyzer

# Compiled regex patterns for database model detection
# SQLAlchemy patterns
PATTERN_SQLALCHEMY_CLASS = re.compile(
    r"class\s+(\w+)\([^)]*?(?:Base|db\.Model|DeclarativeBase)[^)]*\):"
)
PATTERN_SQLALCHEMY_TABLENAME = re.compile(r'__tablename__\s*=\s*["\'](\w+)["\']')
PATTERN_SQLALCHEMY_COLUMN = re.compile(r"(\w+)\s*=\s*Column\((.*?)\)")
PATTERN_SQLALCHEMY_COLUMN_TYPE = re.compile(
    r"(Integer|String|Text|Boolean|DateTime|Float|JSON)"
)

# Django patterns
PATTERN_DJANGO_MODEL = re.compile(r"class\s+(\w+)\(models\.Model\):")
PATTERN_DJANGO_FIELD = re.compile(r"(\w+)\s*=\s*models\.(\w+Field)\((.*?)\)")

# Prisma patterns
PATTERN_PRISMA_MODEL = re.compile(r"model\s+(\w+)\s*\{([^}]+)\}", re.MULTILINE)
PATTERN_PRISMA_FIELD = re.compile(r"(\w+)\s+(\w+)([^/\n]*)")

# TypeORM patterns
PATTERN_TYPEORM_ENTITY = re.compile(r"@Entity\([^)]*\)\s*(?:export\s+)?class\s+(\w+)")
PATTERN_TYPEORM_COLUMN = re.compile(
    r"@(PrimaryGeneratedColumn|Column)\(([^)]*)\)\s+(\w+):\s*(\w+)"
)

# Drizzle patterns
PATTERN_DRIZZLE_TABLE = re.compile(
    r'export\s+const\s+(\w+)\s*=\s*(?:pg|mysql|sqlite)Table\(["\'](\w+)["\']'
)

# Mongoose patterns
PATTERN_MONGOOSE_MODEL = re.compile(r'mongoose\.model\(["\'](\w+)["\']')


class DatabaseDetector(BaseAnalyzer):
    """Detects database models across multiple ORMs."""

    def __init__(self, path: Path):
        super().__init__(path)

    def detect_all_models(self) -> dict:
        """Detect all database models across different ORMs."""
        models = {}

        # Python SQLAlchemy
        models.update(self._detect_sqlalchemy_models())

        # Python Django
        models.update(self._detect_django_models())

        # Prisma schema
        models.update(self._detect_prisma_models())

        # TypeORM entities
        models.update(self._detect_typeorm_models())

        # Drizzle schema
        models.update(self._detect_drizzle_models())

        # Mongoose models
        models.update(self._detect_mongoose_models())

        return models

    def _detect_sqlalchemy_models(self) -> dict:
        """Detect SQLAlchemy models."""
        models = {}
        py_files = list(self.path.glob("**/*.py"))

        for file_path in py_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Find class definitions that inherit from Base or db.Model
            matches = PATTERN_SQLALCHEMY_CLASS.finditer(content)

            for match in matches:
                model_name = match.group(1)

                # Extract table name if defined
                table_match = PATTERN_SQLALCHEMY_TABLENAME.search(content)
                table_name = (
                    table_match.group(1) if table_match else model_name.lower() + "s"
                )

                # Extract columns
                fields = {}
                column_matches = PATTERN_SQLALCHEMY_COLUMN.finditer(
                    content[match.end() : match.end() + 2000]
                )

                for col_match in column_matches:
                    field_name = col_match.group(1)
                    field_def = col_match.group(2)

                    # Detect field properties
                    is_primary = "primary_key=True" in field_def
                    is_unique = "unique=True" in field_def
                    is_nullable = "nullable=False" not in field_def

                    # Extract type
                    type_match = PATTERN_SQLALCHEMY_COLUMN_TYPE.search(field_def)
                    field_type = type_match.group(1) if type_match else "Unknown"

                    fields[field_name] = {
                        "type": field_type,
                        "primary_key": is_primary,
                        "unique": is_unique,
                        "nullable": is_nullable,
                    }

                if fields:  # Only add if we found fields
                    models[model_name] = {
                        "table": table_name,
                        "fields": fields,
                        "file": str(file_path.relative_to(self.path)),
                        "orm": "SQLAlchemy",
                    }

        return models

    def _detect_django_models(self) -> dict:
        """Detect Django models."""
        models = {}
        model_files = list(self.path.glob("**/models.py")) + list(
            self.path.glob("**/models/*.py")
        )

        for file_path in model_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Find class definitions that inherit from models.Model
            matches = PATTERN_DJANGO_MODEL.finditer(content)

            for match in matches:
                model_name = match.group(1)
                table_name = model_name.lower()

                # Extract fields
                fields = {}
                field_matches = PATTERN_DJANGO_FIELD.finditer(
                    content[match.end() : match.end() + 2000]
                )

                for field_match in field_matches:
                    field_name = field_match.group(1)
                    field_type = field_match.group(2)
                    field_args = field_match.group(3)

                    fields[field_name] = {
                        "type": field_type,
                        "unique": "unique=True" in field_args,
                        "nullable": "null=True" in field_args,
                    }

                if fields:
                    models[model_name] = {
                        "table": table_name,
                        "fields": fields,
                        "file": str(file_path.relative_to(self.path)),
                        "orm": "Django",
                    }

        return models

    def _detect_prisma_models(self) -> dict:
        """Detect Prisma models from schema.prisma."""
        models = {}
        schema_file = self.path / "prisma" / "schema.prisma"

        if not schema_file.exists():
            return models

        try:
            content = schema_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return models

        # Find model definitions
        matches = PATTERN_PRISMA_MODEL.finditer(content)

        for match in matches:
            model_name = match.group(1)
            model_body = match.group(2)

            fields = {}
            # Parse fields: id Int @id @default(autoincrement())
            field_matches = PATTERN_PRISMA_FIELD.finditer(model_body)

            for field_match in field_matches:
                field_name = field_match.group(1)
                field_type = field_match.group(2)
                field_attrs = field_match.group(3)

                fields[field_name] = {
                    "type": field_type,
                    "primary_key": "@id" in field_attrs,
                    "unique": "@unique" in field_attrs,
                    "nullable": "?" in field_type,
                }

            if fields:
                models[model_name] = {
                    "table": model_name.lower(),
                    "fields": fields,
                    "file": "prisma/schema.prisma",
                    "orm": "Prisma",
                }

        return models

    def _detect_typeorm_models(self) -> dict:
        """Detect TypeORM entities."""
        models = {}
        ts_files = list(self.path.glob("**/*.entity.ts")) + list(
            self.path.glob("**/entities/*.ts")
        )

        for file_path in ts_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Find @Entity() class declarations
            matches = PATTERN_TYPEORM_ENTITY.finditer(content)

            for match in matches:
                model_name = match.group(1)

                # Extract columns
                fields = {}
                column_matches = PATTERN_TYPEORM_COLUMN.finditer(content)

                for col_match in column_matches:
                    decorator = col_match.group(1)
                    options = col_match.group(2)
                    field_name = col_match.group(3)
                    field_type = col_match.group(4)

                    fields[field_name] = {
                        "type": field_type,
                        "primary_key": decorator == "PrimaryGeneratedColumn",
                        "unique": "unique: true" in options,
                    }

                if fields:
                    models[model_name] = {
                        "table": model_name.lower(),
                        "fields": fields,
                        "file": str(file_path.relative_to(self.path)),
                        "orm": "TypeORM",
                    }

        return models

    def _detect_drizzle_models(self) -> dict:
        """Detect Drizzle ORM schemas."""
        models = {}
        schema_files = list(self.path.glob("**/schema.ts")) + list(
            self.path.glob("**/db/schema.ts")
        )

        for file_path in schema_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Find table definitions: export const users = pgTable('users', {...})
            matches = PATTERN_DRIZZLE_TABLE.finditer(content)

            for match in matches:
                const_name = match.group(1)
                table_name = match.group(2)

                models[const_name] = {
                    "table": table_name,
                    "fields": {},  # Would need more parsing for fields
                    "file": str(file_path.relative_to(self.path)),
                    "orm": "Drizzle",
                }

        return models

    def _detect_mongoose_models(self) -> dict:
        """Detect Mongoose models."""
        models = {}
        model_files = list(self.path.glob("**/models/*.js")) + list(
            self.path.glob("**/models/*.ts")
        )

        for file_path in model_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Find mongoose.model() or new Schema()
            matches = PATTERN_MONGOOSE_MODEL.finditer(content)

            for match in matches:
                model_name = match.group(1)

                models[model_name] = {
                    "table": model_name.lower(),
                    "fields": {},
                    "file": str(file_path.relative_to(self.path)),
                    "orm": "Mongoose",
                }

        return models
