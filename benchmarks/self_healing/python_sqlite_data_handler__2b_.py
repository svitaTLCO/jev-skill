import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime


class GameTelemetryStore:
    def __init__(self, db_path: str = "telemetry_logs.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the telemetry_logs table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    id INTEGER PRIMARY KEY,
                    player TEXT,
                    action TEXT,
                    payload TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
    
    def log_event(self, player: str, action: str, payload_dict: Dict[str, Any]) ->