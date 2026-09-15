"""004_telemetry_policies

Revision ID: 004_telemetry_policies
Revises: 003_telemetry_hypertable
Create Date: 2026-09-15 12:15:00.000000

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_telemetry_policies"
down_revision: Union[str, None] = "003_telemetry_hypertable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def load_sql(filename: str) -> str:
    with open(SQL_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()


def upgrade() -> None:
    sql = load_sql("004_telemetry_policies.up.sql")
    op.execute(sql)


def downgrade() -> None:
    sql = load_sql("004_telemetry_policies.down.sql")
    op.execute(sql)
