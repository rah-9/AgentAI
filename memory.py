# Shared Memory Store using SQLite
import sqlite3
import json
import time

class SharedMemory:
    def __init__(self, db_path='memory.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            classification TEXT,
            extracted_fields TEXT,
            actions_triggered TEXT,
            agent_trace TEXT
        )''')
        self.conn.commit()

    def log_trace(self, source, classification, extracted_fields, actions_triggered, agent_trace):
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO traces (timestamp, source, classification, extracted_fields, actions_triggered, agent_trace)
            VALUES (?, ?, ?, ?, ?, ?)''', (
            time.strftime('%Y-%m-%d %H:%M:%S'),
            source,
            json.dumps(classification),
            json.dumps(extracted_fields),
            json.dumps(actions_triggered),
            json.dumps(agent_trace)
        ))
        self.conn.commit()

    def get_traces(self, limit=20):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM traces ORDER BY id DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        return rows
