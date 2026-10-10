import os
import sys
import time
import subprocess
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.preflight import run_preflight, check_docker
from backend.app.db.neo4j import check_neo4j_health

def start_docker_neo4j():
    passed, _, fix = check_docker()
    if not passed:
        print("[NOTICE] Docker Desktop is not currently running.")
        print(f"         {fix}")
        print("         Backend and SQLite will operate; Neo4j will sync once Docker is started.")
        return False
    
    print("Launching Neo4j container via docker compose...")
    try:
        subprocess.run(["docker", "compose", "up", "-d"], cwd=str(ROOT_DIR), check=True)
        print("Waiting for Neo4j Bolt service on port 7687...")
        max_retries = 15
        for attempt in range(max_retries):
            if check_neo4j_health():
                print("[OK] Neo4j is online and healthy!")
                return True
            time.sleep(2)
        print("[WARN] Neo4j container started, but health check timed out. Proceeding...")
    except Exception as e:
        print(f"[WARN] Failed to start Docker Compose: {e}")
    return False

def initialize_database():
    print("Running database initialization...")
    from scripts.init_db import init_sqlite, init_neo4j
    init_sqlite()
    init_neo4j()

def ensure_frontend_deps():
    frontend_dir = ROOT_DIR / "frontend"
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend node modules (npm install)...")
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        subprocess.run([npm_cmd, "install"], cwd=str(frontend_dir), check=True)

def main():
    print("==================================================")
    print("          CASE CONNECT AI — BOOTSTRAPPER          ")
    print("==================================================")
    
    # 1. Preflight
    run_preflight()
    
    # 2. Docker / Neo4j
    start_docker_neo4j()
    
    # 3. DB initialization
    initialize_database()
    
    # 4. Frontend check
    ensure_frontend_deps()
    
    print("\n==================================================")
    print("  Case Connect AI is ready to run:")
    print("  * Backend API:       http://localhost:8000")
    print("  * API Documentation: http://localhost:8000/docs")
    print("  * API Health:        http://localhost:8000/health")
    print("  * Frontend Web App:  http://localhost:5173")
    print("  * Neo4j Browser:     http://localhost:7474")
    print("--------------------------------------------------")
    print("  To launch the servers:")
    print("  1. Backend:   .\\.venv\\Scripts\\uvicorn.exe backend.app.main:app --reload --port 8000")
    print("  2. Frontend:  cd frontend && npm run dev")
    print("==================================================")

    import argparse
    parser = argparse.ArgumentParser(description="Start Case Connect AI services")
    parser.add_argument("--serve", action="store_true", help="Launch backend server immediately")
    args, _ = parser.parse_known_args()

    if args.serve:
        print("\nStarting FastAPI backend server...")
        py_exec = ROOT_DIR / ".venv" / "Scripts" / "python.exe" if os.name == "nt" else ROOT_DIR / ".venv" / "bin" / "python"
        subprocess.run([str(py_exec), "-m", "uvicorn", "backend.app.main:app", "--reload", "--port", "8000"], cwd=str(ROOT_DIR))

if __name__ == "__main__":
    main()
