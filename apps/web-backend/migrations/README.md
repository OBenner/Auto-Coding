# Database Migrations

This directory contains Alembic database migrations for the Auto Claude web backend.

## Setup

Ensure PostgreSQL is running and the `DATABASE_URL` is configured in your `.env` file:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autoclaude
```

## Running Migrations

To apply all migrations to the database:

```bash
cd apps/web-backend
python -m alembic upgrade head
```

To check the current migration version:

```bash
python -m alembic current
```

To see migration history:

```bash
python -m alembic history
```

## Creating New Migrations

To create a new migration after modifying models:

```bash
python -m alembic revision --autogenerate -m "description of changes"
```

To create an empty migration file:

```bash
python -m alembic revision -m "description of changes"
```

## Migration Files

- `env.py` - Alembic environment configuration
- `script.py.mako` - Template for new migration files
- `versions/` - Directory containing migration scripts
  - `001_create_users.py` - Initial migration creating the users table

## Rollback

To rollback the last migration:

```bash
python -m alembic downgrade -1
```

To rollback to a specific revision:

```bash
python -m alembic downgrade <revision_id>
```

To rollback all migrations:

```bash
python -m alembic downgrade base
```
