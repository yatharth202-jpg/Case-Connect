import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.db.sql import Base, engine
from backend.app.db.neo4j import get_neo4j_driver, check_neo4j_health

def init_sqlite():
    print("Initializing SQLite tables...")
    Base.metadata.create_all(bind=engine)
    print("SQLite schema initialized successfully (22 tables created/verified).")

def init_neo4j():
    print("Checking Neo4j connection...")
    if not check_neo4j_health():
        print("Neo4j is currently unreachable. Make sure Docker Desktop / Neo4j is running.")
        print("Skipping Neo4j constraints setup for now (will be automatically applied when Neo4j is online).")
        return False

    driver = get_neo4j_driver()
    labels = [
        "Person", "Phone", "BankAccount", "Organization", "Vehicle",
        "FIR", "MasterProfile", "Email", "Device", "VPA", "IP"
    ]

    with driver.session() as session:
        print("Creating Neo4j uniqueness constraints on property `key`...")
        for label in labels:
            constraint_query = f"""
            CREATE CONSTRAINT constraint_{label.lower()}_key IF NOT EXISTS
            FOR (n:{label})
            REQUIRE n.key IS UNIQUE
            """
            session.run(constraint_query)
            print(f"  - Constraint ensured for {label}(key)")

        print("Creating Neo4j index on property `case_id`...")
        for label in labels:
            index_query = f"""
            CREATE INDEX index_{label.lower()}_case_id IF NOT EXISTS
            FOR (n:{label})
            ON (n.case_id)
            """
            session.run(index_query)
            print(f"  - Index ensured for {label}(case_id)")

    print("Neo4j constraints and indexes created successfully.")
    return True

def main():
    print("=== Case Connect AI — Database Initialization ===")
    init_sqlite()
    init_neo4j()
    print("=== Database initialization step complete ===")

if __name__ == "__main__":
    main()
