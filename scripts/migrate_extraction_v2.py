"""
Idempotent, additive SQLite schema migration script for CaseConnect AI (Extraction V2).

Responsibilities:
  1. Backs up the target SQLite database file into the gitignored `backups/` directory.
  2. Creates any new tables defined in `backend.app.db.sql.Base` (`CREATE TABLE IF NOT EXISTS`).
  3. Inspects existing tables via `PRAGMA table_info` and adds any new columns (`ADD COLUMN`)
     only when absent, making it completely safe to run multiple times.
"""

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from backend.app.db.sql import Base
from backend.app.config import settings

ADDITIVE_COLUMNS: Dict[str, List[Tuple[str, str]]] = {
    "call_records": [
        ("tz_source", "TEXT DEFAULT 'assumed_local'"),
        ("raw_json", "TEXT DEFAULT '{}'"),
        ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
    ],
    "transactions": [
        ("tz_source", "TEXT DEFAULT 'assumed_local'"),
        ("raw_json", "TEXT DEFAULT '{}'"),
        ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
    ],
    "ip_events": [
        ("tz_source", "TEXT DEFAULT 'assumed_local'"),
        ("raw_json", "TEXT DEFAULT '{}'"),
        ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
    ],
    "entities": [
        ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
    ],
    "entity_links": [
        ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
    ],
    "evidence_files": [
        ("perceptual_hash", "TEXT"),
        ("exif_json", "TEXT DEFAULT '{}'"),
        ("is_handwritten", "BOOLEAN DEFAULT 0 NOT NULL"),
        ("quality_json", "TEXT DEFAULT '{}'"),
    ],
    "extracted_entities": [
        ("page_no", "INTEGER"),
        ("bbox_json", "TEXT"),
        ("source_kind", "TEXT DEFAULT 'text_layer_pdf'"),
    ],
}


def resolve_sqlite_path(db_url_or_path: Optional[str] = None) -> Path:
    raw = db_url_or_path or settings.DATABASE_URL
    if raw.startswith("sqlite:///"):
        rel = raw.replace("sqlite:///", "", 1)
        p = Path(rel)
        return p if p.is_absolute() else (ROOT_DIR / p).resolve()
    return Path(raw).resolve()


def run_migration(
    db_path: Optional[Path] = None,
    create_backup: bool = True,
) -> Dict[str, any]:
    target_db = Path(db_path).resolve() if db_path else resolve_sqlite_path()
    backup_file: Optional[Path] = None

    if create_backup and target_db.exists():
        backups_dir = ROOT_DIR / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = backups_dir / f"{target_db.stem}_migrate_{ts}.db"
        shutil.copy2(target_db, backup_file)

    # 1. Ensure all tables exist via SQLAlchemy metadata
    eng = create_engine(f"sqlite:///{target_db.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    eng.dispose()

    # 2. Add missing columns idempotently
    columns_added: List[str] = []
    columns_skipped: List[str] = []

    conn = sqlite3.connect(str(target_db))
    try:
        cur = conn.cursor()
        for table_name, col_defs in ADDITIVE_COLUMNS.items():
            cur.execute(f"PRAGMA table_info({table_name})")
            existing_cols = {row[1] for row in cur.fetchall()}
            if not existing_cols:
                continue
            for col_name, col_sql_type in col_defs:
                if col_name not in existing_cols:
                    cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_sql_type}")
                    columns_added.append(f"{table_name}.{col_name}")
                else:
                    columns_skipped.append(f"{table_name}.{col_name}")
        conn.commit()
    finally:
        conn.close()

    return {
        "status": "ok",
        "database": str(target_db),
        "backup_path": str(backup_file) if backup_file else None,
        "columns_added": columns_added,
        "columns_already_present": columns_skipped,
    }


if __name__ == "__main__":
    result = run_migration(create_backup=True)
    print(f"[MIGRATE] Database: {result['database']}")
    if result["backup_path"]:
        print(f"[MIGRATE] Backup created: {result['backup_path']}")
    print(f"[MIGRATE] Columns added ({len(result['columns_added'])}): {result['columns_added']}")
    print(f"[MIGRATE] Columns already present ({len(result['columns_already_present'])}): {result['columns_already_present']}")

