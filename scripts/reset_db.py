import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.config import settings
from backend.app.db.sql import Base, engine
from backend.app.db.neo4j import get_neo4j_driver, check_neo4j_health

def reset_sqlite():
    print("Resetting SQLite database...")
    db_file = Path("app.db")
    if db_file.exists():
        os.remove(db_file)
        print("Removed existing app.db file.")
    Base.metadata.create_all(bind=engine)
    print("Fresh SQLite tables recreated.")

def reset_neo4j():
    print("Checking Neo4j connection for reset...")
    if not check_neo4j_health():
        print("Neo4j is unreachable, skipping Neo4j purge.")
        return

    driver = get_neo4j_driver()
    with driver.session() as session:
        print("Purging all nodes and relationships in Neo4j...")
        session.run("MATCH (n) DETACH DELETE n")
    print("Neo4j database purged successfully.")

def reset_uploads():
    upload_dir = Path(settings.UPLOAD_DIR)
    if upload_dir.exists():
        print(f"Cleaning upload directory: {upload_dir}...")
        for item in upload_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass
    print("Uploads directory cleared.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reset Case Connect AI database and uploads")
    parser.add_argument("--force", "-y", action="store_true", help="Bypass confirmation prompt")
    args = parser.parse_args()

    print("=== Case Connect AI — Database & Storage Reset ===")
    if not args.force:
        confirm = input("Are you sure you want to completely wipe the database and uploads? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Reset aborted by user.")
            return
    reset_sqlite()
    reset_neo4j()
    reset_uploads()
    print("=== Reset Completed Successfully ===")

if __name__ == "__main__":
    main()
