import os
import sys
import getpass
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from backend.app.db.sql import SessionLocal, User

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def seed_user(username: str, role: str, password: str | None = None):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"User '{username}' already exists (Role: {existing.role}).")
            return

        if not password:
            print(f"--- Create Password for {username} ({role}) ---")
            p1 = getpass.getpass(f"Enter password for {username}: ")
            p2 = getpass.getpass("Confirm password: ")
            if p1 != p2:
                print("Passwords do not match. Aborting.")
                return
            if len(p1) < 6:
                print("Password must be at least 6 characters. Aborting.")
                return
            password = p1

        pwd_hash = hash_password(password)
        new_user = User(
            username=username,
            password_hash=pwd_hash,
            role=role,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"Successfully created user '{username}' with role '{role}'.")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Seed users for Case Connect AI")
    parser.add_argument("--username", help="Username")
    parser.add_argument("--role", default="admin", choices=["admin", "investigator", "viewer"], help="User role")
    parser.add_argument("--password", help="Password (optional, if omitted will prompt)")
    parser.add_argument("--defaults", action="store_true", help="Seed all default accounts non-interactively")
    args = parser.parse_args()

    if args.defaults:
        seed_user("admin", "admin", "AdminPass1234!")
        seed_user("investigator1", "investigator", "OfficerPass1234!")
        seed_user("viewer1", "viewer", "ViewerPass1234!")
        print("Default users (admin, investigator1, viewer1) seeded successfully.")
        return

    username = args.username or input("Enter username (default: admin): ").strip() or "admin"
    seed_user(username=username, role=args.role, password=args.password)

if __name__ == "__main__":
    main()
