# Alembic Migrations

Production schema changes should be managed here instead of relying on `Base.metadata.create_all()`.

Common commands:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

`scripts/init_db.py` remains useful for local development and tests.

The current baseline migration is `0001_initial_schema`. For an existing
development database that was created with `create_all`, stamp it before
running future migrations:

```bash
alembic stamp 0001_initial_schema
```
