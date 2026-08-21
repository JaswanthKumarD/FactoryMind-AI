import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "factorymind.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS machines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        machine_type TEXT NOT NULL,
        capacity_per_hour REAL NOT NULL,
        cost_per_hour REAL NOT NULL,
        available_hours REAL NOT NULL DEFAULT 16,
        status TEXT NOT NULL DEFAULT 'Available'
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT UNIQUE NOT NULL,
        product TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        priority INTEGER NOT NULL,
        deadline_hours REAL NOT NULL,
        material TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending'
    );
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material TEXT UNIQUE NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT NOT NULL,
        machine_type TEXT NOT NULL,
        sequence INTEGER NOT NULL,
        hours_per_unit REAL NOT NULL
    );
    """)
    conn.commit()
    conn.close()
