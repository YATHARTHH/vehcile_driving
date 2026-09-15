"""003_telemetry_hypertable

Revision ID: 003_telemetry_hypertable
Revises: 002_telemetry_schema
Create Date: 2026-09-15 12:10:00.000000

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_telemetry_hypertable"
down_revision: Union[str, None] = "002_telemetry_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def load_sql(filename: str) -> str:
    with open(SQL_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()


def upgrade() -> None:
    sql = load_sql("003_telemetry_hypertable.up.sql")
    op.execute(sql)


def downgrade() -> None:
    sql = load_sql("003_telemetry_hypertable.down.sql")
    op.execute(sql)
