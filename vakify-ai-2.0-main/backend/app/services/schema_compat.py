from __future__ import annotations

from sqlalchemy import inspect, text


def _ddl_type_for_engine(engine, ddl_type: str) -> str:
    dialect = getattr(engine, "dialect", None)
    dialect_name = getattr(dialect, "name", "")
    if ddl_type.upper() == "DATETIME" and dialect_name == "postgresql":
        return "TIMESTAMP"
    return ddl_type


def ensure_schema_compatibility(db) -> list[str]:
    """Add small missing columns for older local/production databases."""
    engine = db.engine
    inspector = inspect(engine)
    added: list[str] = []

    legacy_columns = {
        "code_lab_submissions": {
            "task_id": "INTEGER",
        },
        "daily_tasks": {
            "content_json": "JSON",
        },
        "user_profile": {
            "phone_number": "VARCHAR(40)",
            "other_details_json": "JSON",
            "onboarding_completed_at": "DATETIME",
        },
    }

    for table_name, columns in legacy_columns.items():
        if not inspector.has_table(table_name):
            continue

        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, ddl_type in columns.items():
            if column_name in existing:
                continue
            resolved_type = _ddl_type_for_engine(engine, ddl_type)
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {resolved_type}"))
            added.append(f"{table_name}.{column_name}")

    return added
