import sqlite3

def clean_database():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    tables_to_clear = [
        "call_records",
        "transactions",
        "ip_events",
        "rejected_rows",
        "alerts",
        "reports",
        "entities",
        "entity_links",
        "extracted_entities",
        "match_suggestions",
        "profile_members",
        "lead_decisions",
        "jobs",
        "saved_views",
        "evidence_files",
        "column_mappings",
        "case_settings",
        "case_members",
        "cases"
    ]

    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except Exception as e:
            print(f"Error clearing {table}: {e}")

    conn.commit()
    print("Database purged of all legacy/test/seed cases.")

    # Verify users are still intact
    users = cursor.execute("SELECT username, role FROM users").fetchall()
    print(f"Users remaining: {users}")
    conn.close()

if __name__ == "__main__":
    clean_database()
