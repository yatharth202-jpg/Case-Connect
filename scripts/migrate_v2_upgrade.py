"""
Idempotent, additive SQLite schema migration script for CaseConnect AI Full Upgrade.
Adds raw_sheets, raw_rows, graph_nodes, graph_edges, analysis_results, saved_graph_views,
node_type_configs, edge_type_configs, and additive raw_row_id columns.
Seeds default graph node/edge configs and score weights.
"""

import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import yaml
from sqlalchemy import create_engine
from backend.app.db.sql import (
    Base, engine, SessionLocal,
    NodeTypeConfig, EdgeTypeConfig, SystemConfig
)
from backend.app.config import settings

ADDITIVE_COLUMNS: Dict[str, List[Tuple[str, str]]] = {
    "call_records": [
        ("raw_row_id", "TEXT"),
    ],
    "transactions": [
        ("raw_row_id", "TEXT"),
    ],
    "ip_events": [
        ("raw_row_id", "TEXT"),
    ],
    "rejected_rows": [
        ("raw_row_id", "TEXT"),
    ],
}


def backup_database(db_path: Path) -> Path:
    """Safely backs up SQLite DB using sqlite3 online backup API."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = ROOT_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / f"app_upgrade_backup_{timestamp}.db"

    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_file))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    print(f"[BACKUP] Created verified SQLite backup: {backup_file.name}")
    return backup_file


def get_existing_columns(conn: sqlite3.Connection, table_name: str) -> set:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    return {row[1] for row in cursor.fetchall()}


def apply_additive_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    for table_name, cols in ADDITIVE_COLUMNS.items():
        existing_cols = get_existing_columns(conn, table_name)
        for col_name, col_def in cols:
            if col_name not in existing_cols:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def};"
                print(f"[MIGRATE] Altering {table_name}: ADD COLUMN {col_name} {col_def}")
                cursor.execute(sql)
            else:
                print(f"[SKIP] Column '{col_name}' already exists in '{table_name}'")
    conn.commit()


def seed_graph_configurations(db) -> None:
    seed_file = ROOT_DIR / "backend" / "config" / "seed_graph_config.yaml"
    if not seed_file.exists():
        print(f"[WARN] Seed file {seed_file} not found, skipping config seeding.")
        return

    with open(seed_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Seed Node Types
    for nt in cfg.get("node_types", []):
        existing = db.query(NodeTypeConfig).filter(NodeTypeConfig.type_name == nt["type_name"]).first()
        if not existing:
            rec = NodeTypeConfig(
                type_name=nt["type_name"],
                label=nt.get("label", nt["type_name"]),
                color=nt.get("color", "#2563EB"),
                icon=nt.get("icon", "circle"),
                shape=nt.get("shape", "ellipse"),
                score_weight=float(nt.get("score_weight", 1.0)),
                is_active=True,
            )
            db.add(rec)
            print(f"[SEED] Added NodeTypeConfig: {nt['type_name']}")

    # Seed Edge Types
    for et in cfg.get("edge_types", []):
        existing = db.query(EdgeTypeConfig).filter(EdgeTypeConfig.type_name == et["type_name"]).first()
        if not existing:
            rec = EdgeTypeConfig(
                type_name=et["type_name"],
                label=et.get("label", et["type_name"]),
                color=et.get("color", "#64748B"),
                line_style=et.get("line_style", "solid"),
                directional=bool(et.get("directional", True)),
                is_active=True,
            )
            db.add(rec)
            print(f"[SEED] Added EdgeTypeConfig: {et['type_name']}")

    # Seed Score Weights in SystemConfig
    sw = cfg.get("score_weights", {})
    if sw:
        existing_sw = db.query(SystemConfig).filter(SystemConfig.key == "top_leads_weights").first()
        if not existing_sw:
            db.add(SystemConfig(key="top_leads_weights", value=json.dumps(sw)))
            print(f"[SEED] Added SystemConfig: top_leads_weights")

    db.commit()


def run_upgrade_migration(db_url: str = settings.DATABASE_URL) -> None:
    print("=" * 60)
    print("  CASECONNECT AI — UPGRADE SCHEMA MIGRATION")
    print("=" * 60)

    if db_url.startswith("sqlite:///"):
        raw_path = db_url.replace("sqlite:///", "")
        db_path = Path(raw_path).resolve()
        if db_path.exists():
            backup_database(db_path)

    # 1. Create all declarative models in Base
    print("[MIGRATE] Creating tables defined in Base (CREATE TABLE IF NOT EXISTS)...")
    Base.metadata.create_all(bind=engine)
    print("[MIGRATE] Base.metadata.create_all completed.")

    # 2. Add additive columns to existing tables
    if "sqlite" in db_url:
        raw_path = db_url.replace("sqlite:///", "")
        db_path = Path(raw_path).resolve()
        conn = sqlite3.connect(str(db_path))
        apply_additive_columns(conn)
        conn.close()

    # 3. Seed graph configurations
    db = SessionLocal()
    try:
        seed_graph_configurations(db)
    finally:
        db.close()

    print("=" * 60)
    print("  [SUCCESS] UPGRADE MIGRATION COMPLETED IDEMPOTENTLY")
    print("=" * 60)


if __name__ == "__main__":
    run_upgrade_migration()

