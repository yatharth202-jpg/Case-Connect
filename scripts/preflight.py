import sys
import shutil
import socket
import subprocess
import re
from pathlib import Path

def check_python():
    version = sys.version_info
    passed = (version.major == 3 and version.minor >= 11) or version.major > 3
    actual = f"{version.major}.{version.minor}.{version.micro}"
    fix = "Install Python 3.11+ from https://www.python.org/downloads/ and add to PATH."
    return passed, f"Python >= 3.11 (Found: {actual})", fix

def check_node():
    try:
        proc = subprocess.run(["node", "-v"], capture_output=True, text=True, check=True)
        out = proc.stdout.strip()
        match = re.search(r"v?(\d+)\.", out)
        if match:
            major = int(match.group(1))
            passed = major >= 20
            return passed, f"Node.js >= 20 (Found: {out})", "Install Node.js 20+ from https://nodejs.org/"
        return False, f"Node.js (Unknown version: {out})", "Update Node.js to version 20 or higher."
    except Exception:
        return False, "Node.js (Not found)", "Install Node.js 20+ from https://nodejs.org/ and verify 'node' is in PATH."

def check_git():
    try:
        proc = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        return True, f"Git (Found: {proc.stdout.strip()})", ""
    except Exception:
        return False, "Git (Not found)", "Install Git from https://git-scm.com/ and add to PATH."

def check_docker():
    try:
        ver_proc = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        if ver_proc.returncode != 0:
            return False, "Docker (Not installed or not in PATH)", "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
        
        info_proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        if info_proc.returncode == 0:
            return True, "Docker Desktop (Running)", ""
        return False, "Docker Desktop (Installed, daemon not started)", "Please open Docker Desktop from your Windows Start menu to start the engine."
    except Exception:
        return False, "Docker Desktop (Not found)", "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

def check_ports():
    ports_to_check = [
        (5173, "Frontend Vite"),
        (8000, "Backend FastAPI"),
        (7474, "Neo4j HTTP/Browser"),
        (7687, "Neo4j Bolt Protocol")
    ]
    busy = []
    for port, name in ports_to_check:
        if is_port_in_use(port):
            busy.append(f"Port {port} ({name}) is already in use.")

    if not busy:
        return True, "Required ports (5173, 8000, 7474, 7687) are free", ""
    return True, "Ports checked", "Note: " + "; ".join(busy)

def check_disk():
    usage = shutil.disk_usage(".")
    free_gb = usage.free / (1024 ** 3)
    passed = free_gb >= 2.0
    status = f"Disk Space ({free_gb:.1f} GB free)"
    fix = "Free up at least 2 GB of disk space on your drive."
    return passed, status, fix

def run_preflight():
    print("==================================================")
    print("      CASE CONNECT AI — SYSTEM PREFLIGHT CHECK    ")
    print("==================================================")
    
    checks = [
        ("Python Environment", check_python),
        ("Node.js Runtime", check_node),
        ("Version Control (Git)", check_git),
        ("Container Engine (Docker)", check_docker),
        ("Network Ports", check_ports),
        ("Available Disk", check_disk)
    ]
    
    all_ok = True
    fixes = []
    
    for name, check_fn in checks:
        passed, status_text, fix_msg = check_fn()
        symbol = "[OK]" if passed else "[WARN/FAIL]"
        print(f" {symbol:<12} {name:<26}: {status_text}")
        if not passed:
            all_ok = False
            if fix_msg:
                fixes.append((name, fix_msg))
                
    print("--------------------------------------------------")
    if all_ok:
        print("RESULT: All critical requirements satisfied!")
    else:
        print("RESULT: Some items require your attention:")
        for name, fix in fixes:
            print(f"  * {name}: {fix}")
    print("==================================================")
    return all_ok

if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)
