"""002_telemetry_schema

Revision ID: 002_telemetry_schema
Revises: 001_core_schema
Create Date: 2026-09-15 12:05:00.000000

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_telemetry_schema"
down_revision: Union[str, None] = "001_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def load_sql(filename: str) -> str:
    with open(SQL_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()


def upgrade() -> None:
    sql = load_sql("002_telemetry_schema.up.sql")
    op.execute(sql)


def downgrade() -> None:
    sql = load_sql("002_telemetry_schema.down.sql")
    op.execute(sql)
