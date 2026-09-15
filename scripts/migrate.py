#!/usr/bin/env python3
"""
FleetTrack Database Migration CLI
Manages SQL-first Alembic migrations, transactional execution, and offline dry-run SQL generation.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import command
from alembic.config import Config


def get_alembic_config(db_url: str | None = None) -> Config:
    """Creates an Alembic Config object pointing to the repository alembic.ini."""
    repo_root = Path(__file__).resolve().parent.parent
    ini_path = repo_root / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(repo_root / "alembic"))
    if db_url:
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    return alembic_cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FleetTrack Database Migration CLI (SQL-First Alembic)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. upgrade
    up_parser = subparsers.add_parser("upgrade", help="Upgrade database schema to a specified revision (default: head)")
    up_parser.add_argument("revision", nargs="?", default="head", help="Target revision (default: head)")
    up_parser.add_argument("--url", type=str, default=None, help="Override database URL")

    # 2. downgrade
    down_parser = subparsers.add_parser("downgrade", help="Downgrade database schema by revision steps (default: -1)")
    down_parser.add_argument("revision", nargs="?", default="-1", help="Target revision or steps (default: -1)")
    down_parser.add_argument("--url", type=str, default=None, help="Override database URL")

    # 3. sql (offline dry-run)
    sql_parser = subparsers.add_parser("sql", help="Export deterministic offline migration SQL without connecting to database")
    sql_parser.add_argument("revision", nargs="?", default="head", help="Target revision to generate SQL for (default: head)")
    sql_parser.add_argument("--start", type=str, default="base", help="Starting revision for SQL range (default: base)")
    sql_parser.add_argument("--output", type=str, default=None, help="Write generated SQL to file instead of stdout")

    # 4. status
    status_parser = subparsers.add_parser("status", help="Show current revision and pending migration heads")
    status_parser.add_argument("--url", type=str, default=None, help="Override database URL")

    args = parser.parse_args()

    if args.subcommand == "upgrade":
        cfg = get_alembic_config(args.url)
        print(f"[Migration] Upgrading database to {args.revision}...")
        command.upgrade(cfg, args.revision)
        print("[Migration] Upgrade completed successfully.")

    elif args.subcommand == "downgrade":
        cfg = get_alembic_config(args.url)
        print(f"[Migration] Downgrading database to {args.revision}...")
        command.downgrade(cfg, args.revision)
        print("[Migration] Downgrade completed successfully.")

    elif args.subcommand == "sql":
        import io
        from contextlib import redirect_stdout

        cfg = get_alembic_config()
        range_target = f"{args.start}:{args.revision}" if args.start else args.revision

        buf = io.StringIO()
        with redirect_stdout(buf):
            command.upgrade(cfg, range_target, sql=True)
        raw_sql = buf.getvalue()

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(raw_sql)
            print(f"[Migration] Offline migration SQL written to {out_path.resolve()}")
        else:
            print(raw_sql)

    elif args.subcommand == "status":
        cfg = get_alembic_config(args.url)
        print("[Migration] Current revision:")
        command.current(cfg)
        print("[Migration] Available heads:")
        command.heads(cfg)


if __name__ == "__main__":
    main()
