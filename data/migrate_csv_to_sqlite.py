# data/migrate_csv_to_sqlite.py
import sqlite3
import sys
import os

# Add project root to sys.path to allow imports from data and config
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

from data.csv_handler import load_csv
from data.database import init_db, get_connection, get_db_path

if __name__ == "__main__":
    try:
        # STEP 1: Call init_db() to create the database and table
        init_db()
        
        # STEP 2: Call load_csv() to get all transactions as a list of dicts
        transactions = load_csv()
        
        # STEP 3: Open a connection with get_connection()
        conn = get_connection()
        cursor = conn.cursor()
        
        # STEP 4: For each transaction in the list insert it
        # Clear existing data first to avoid duplicates if run multiple times
        cursor.execute("DELETE FROM transactions")
        
        for t in transactions:
            cursor.execute(
                """
                INSERT INTO transactions (type, ticker, shares, price, date) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    t["type"],
                    t["ticker"],
                    float(t["shares"]),
                    float(t["price"]),
                    str(t["date"]),
                )
            )
            
        # STEP 5: Commit the connection
        conn.commit()
        
        # STEP 6: Count rows inserted
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        
        # STEP 7: Print confirmation
        print(f"Migration complete: {count} transactions imported to {get_db_path()}")
        
        # STEP 8: Close the connection
        conn.close()
        
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
