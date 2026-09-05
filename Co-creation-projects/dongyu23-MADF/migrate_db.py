import sqlite3
import os

DB_PATH = "madf.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        return

    print(f"Migrating database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check messages table columns
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Current columns in messages: {columns}")

        if 'thoughts' in columns:
            print("Found 'thoughts' column. Renaming to 'thought'...")
            cursor.execute("ALTER TABLE messages RENAME COLUMN thoughts TO thought")
            print("Renamed 'thoughts' to 'thought'.")
        elif 'thought' not in columns:
            print("'thought' column missing. Adding it...")
            cursor.execute("ALTER TABLE messages ADD COLUMN thought TEXT")
            print("Added 'thought' column.")
        else:
            print("'thought' column already exists.")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
