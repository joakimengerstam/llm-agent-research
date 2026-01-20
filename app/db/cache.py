import sqlite3
from datetime import datetime
from typing import Optional
from app.config.settings import *


DB_PATH = settings.DATA_DIR / "cache.db"


class Cache:
    """Simple SQLite cache for web content"""

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                url TEXT PRIMARY KEY,
                content TEXT,
                timestamp REAL
            )
        """)
        self.conn.commit()

    def get(self, url: str) -> Optional[str]:
        cursor = self.conn.execute("SELECT content FROM cache WHERE url = ?", (url,))
        row = cursor.fetchone()
        return row[0] if row else None

    def set(self, url: str, content: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (url, content, timestamp) VALUES (?, ?, ?)",
            (url, content, datetime.now().timestamp())
        )
        self.conn.commit()
