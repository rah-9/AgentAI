"""
Memory Store: Provides persistent storage for agent actions, classifications, and results
Uses SQLite for simplicity but can be extended to other databases
"""
import os
import json
import sqlite3
import datetime
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple

class MemoryStore:
    def __init__(self, db_path="./memory.db"):
        """
        Initialize the memory store with a SQLite database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database and required tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create classifications table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS classifications (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            format TEXT NOT NULL,
            intent TEXT NOT NULL,
            confidence REAL,
            source TEXT,
            metadata TEXT,
            summary TEXT
        )
        ''')
        
        # Create extractions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS extractions (
            id TEXT PRIMARY KEY,
            classification_id TEXT,
            timestamp TEXT NOT NULL,
            format TEXT NOT NULL,
            agent TEXT NOT NULL,
            fields TEXT,
            valid BOOLEAN,
            anomalies TEXT,
            summary TEXT,
            FOREIGN KEY (classification_id) REFERENCES classifications(id)
        )
        ''')
        
        # Create actions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            extraction_id TEXT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target TEXT,
            priority TEXT,
            endpoint TEXT,
            status TEXT NOT NULL,
            attempts INTEGER,
            data TEXT,
            result TEXT,
            FOREIGN KEY (extraction_id) REFERENCES extractions(id)
        )
        ''')
        
        # Create traces table for debugging and audit
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            process_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            details TEXT,
            duration_ms INTEGER
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_classification(self, format_type: str, intent: str, confidence: float = None, 
                          metadata: Dict = None, summary: str = None) -> str:
        """
        Log a classification result
        
        Args:
            format_type: Detected format (Email, PDF, JSON, Image)
            intent: Detected business intent
            confidence: Confidence score (0-1)
            metadata: Additional metadata about the classification
            summary: Human-readable summary
            
        Returns:
            ID of the classification record
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            INSERT INTO classifications 
            (id, timestamp, format, intent, confidence, source, metadata, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                record_id,
                timestamp,
                format_type,
                intent,
                confidence,
                metadata.get('source') if metadata else None,
                json.dumps(metadata) if metadata else None,
                summary
            )
        )
        
        conn.commit()
        conn.close()
        
        return record_id
    
    def log_extraction(self, format_type: str, agent: str, fields: Dict = None,
                      valid: bool = True, anomalies: List[str] = None, 
                      summary: str = None, classification_id: str = None) -> str:
        """
        Log an extraction result
        
        Args:
            format_type: Document format (Email, PDF, JSON, Image)
            agent: Agent that performed the extraction
            fields: Extracted fields
            valid: Whether the extraction is valid
            anomalies: List of anomalies found
            summary: Human-readable summary
            classification_id: Related classification ID
            
        Returns:
            ID of the extraction record
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            INSERT INTO extractions
            (id, classification_id, timestamp, format, agent, fields, valid, anomalies, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                record_id,
                classification_id,
                timestamp,
                format_type,
                agent,
                json.dumps(fields) if fields else None,
                valid,
                json.dumps(anomalies) if anomalies else None,
                summary
            )
        )
        
        conn.commit()
        conn.close()
        
        return record_id
    
    def log_action(self, action_type: str, data: Dict = None, result: str = None,
                  status: str = "pending", extraction_id: str = None,
                  target: str = None, priority: str = None, 
                  endpoint: str = None, attempts: int = 1) -> str:
        """
        Log an action taken by the system
        
        Args:
            action_type: Type of action taken
            data: Action data/payload
            result: Result of the action
            status: Status of the action (pending, success, failed)
            extraction_id: Related extraction ID
            target: Target system (CRM, risk, etc.)
            priority: Priority level
            endpoint: API endpoint used
            attempts: Number of attempts made
            
        Returns:
            ID of the action record
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            INSERT INTO actions
            (id, extraction_id, timestamp, action_type, target, priority, endpoint, status, attempts, data, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                record_id,
                extraction_id,
                timestamp,
                action_type,
                target,
                priority,
                endpoint,
                status,
                attempts,
                json.dumps(data) if data else None,
                result
            )
        )
        
        conn.commit()
        conn.close()
        
        return record_id
    
    def log_trace(self, process_id: str, stage: str, details: Dict = None, 
                 duration_ms: int = None) -> str:
        """
        Log a trace for debugging and audit
        
        Args:
            process_id: ID of the overall process
            stage: Processing stage (classify, extract, action)
            details: Additional details
            duration_ms: Duration of the stage in milliseconds
            
        Returns:
            ID of the trace record
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            INSERT INTO traces
            (id, timestamp, process_id, stage, details, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                record_id,
                timestamp,
                process_id,
                stage,
                json.dumps(details) if details else None,
                duration_ms
            )
        )
        
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_process_history(self, process_id: str) -> Dict[str, Any]:
        """
        Get the complete history of a process
        
        Args:
            process_id: ID of the process
            
        Returns:
            Dict with process history
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all traces for the process
        cursor.execute(
            '''
            SELECT * FROM traces
            WHERE process_id = ?
            ORDER BY timestamp
            ''',
            (process_id,)
        )
        
        traces = [dict(row) for row in cursor.fetchall()]
        
        # Extract IDs from traces
        classification_ids = []
        extraction_ids = []
        
        for trace in traces:
            details = json.loads(trace['details']) if trace['details'] else {}
            if 'classification_id' in details:
                classification_ids.append(details['classification_id'])
            if 'extraction_id' in details:
                extraction_ids.append(details['extraction_id'])
        
        # Get classifications
        classifications = []
        if classification_ids:
            placeholders = ','.join(['?'] * len(classification_ids))
            cursor.execute(
                f'''
                SELECT * FROM classifications
                WHERE id IN ({placeholders})
                ''',
                classification_ids
            )
            classifications = [dict(row) for row in cursor.fetchall()]
        
        # Get extractions
        extractions = []
        if extraction_ids:
            placeholders = ','.join(['?'] * len(extraction_ids))
            cursor.execute(
                f'''
                SELECT * FROM extractions
                WHERE id IN ({placeholders})
                ''',
                extraction_ids
            )
            extractions = [dict(row) for row in cursor.fetchall()]
        
        # Get actions
        actions = []
        if extraction_ids:
            placeholders = ','.join(['?'] * len(extraction_ids))
            cursor.execute(
                f'''
                SELECT * FROM actions
                WHERE extraction_id IN ({placeholders})
                ''',
                extraction_ids
            )
            actions = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Build complete history
        return {
            "process_id": process_id,
            "traces": traces,
            "classifications": classifications,
            "extractions": extractions,
            "actions": actions
        }
    
    def get_recent_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent processes
        
        Args:
            limit: Maximum number of processes to return
            
        Returns:
            List of process summaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get distinct process IDs
        cursor.execute(
            '''
            SELECT DISTINCT process_id, MIN(timestamp) as start_time
            FROM traces
            GROUP BY process_id
            ORDER BY start_time DESC
            LIMIT ?
            ''',
            (limit,)
        )
        
        processes = [dict(row) for row in cursor.fetchall()]
        
        # Get summary for each process
        for process in processes:
            process_id = process['process_id']
            
            # Count stages
            cursor.execute(
                '''
                SELECT stage, COUNT(*) as count
                FROM traces
                WHERE process_id = ?
                GROUP BY stage
                ''',
                (process_id,)
            )
            
            stages = {row['stage']: row['count'] for row in cursor.fetchall()}
            process['stages'] = stages
            
            # Get process duration
            cursor.execute(
                '''
                SELECT MIN(timestamp) as start_time, MAX(timestamp) as end_time
                FROM traces
                WHERE process_id = ?
                ''',
                (process_id,)
            )
            
            timing = dict(cursor.fetchone())
            process['start_time'] = timing['start_time']
            process['end_time'] = timing['end_time']
            
            # Format
            cursor.execute(
                '''
                SELECT format
                FROM classifications c
                JOIN traces t ON JSON_EXTRACT(t.details, '$.classification_id') = c.id
                WHERE t.process_id = ?
                LIMIT 1
                ''',
                (process_id,)
            )
            
            format_row = cursor.fetchone()
            process['format'] = format_row['format'] if format_row else None
        
        conn.close()
        
        return processes
    
    def search_by_content(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search memory store by content
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Search classifications
        cursor.execute(
            '''
            SELECT 'classification' as record_type, id, timestamp, format, intent, summary
            FROM classifications
            WHERE summary LIKE ? OR intent LIKE ? OR metadata LIKE ?
            LIMIT ?
            ''',
            (f'%{query}%', f'%{query}%', f'%{query}%', limit)
        )
        
        classification_results = [dict(row) for row in cursor.fetchall()]
        
        # Search extractions
        cursor.execute(
            '''
            SELECT 'extraction' as record_type, id, timestamp, format, agent, summary
            FROM extractions
            WHERE summary LIKE ? OR fields LIKE ?
            LIMIT ?
            ''',
            (f'%{query}%', f'%{query}%', limit)
        )
        
        extraction_results = [dict(row) for row in cursor.fetchall()]
        
        # Search actions
        cursor.execute(
            '''
            SELECT 'action' as record_type, id, timestamp, action_type, target, result
            FROM actions
            WHERE result LIKE ? OR data LIKE ?
            LIMIT ?
            ''',
            (f'%{query}%', f'%{query}%', limit)
        )
        
        action_results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Combine and sort results
        all_results = classification_results + extraction_results + action_results
        all_results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory store statistics
        
        Returns:
            Dict with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Count records by type
        cursor.execute('SELECT COUNT(*) FROM classifications')
        stats['classification_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM extractions')
        stats['extraction_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM actions')
        stats['action_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM traces')
        stats['trace_count'] = cursor.fetchone()[0]
        
        # Count by format
        cursor.execute(
            '''
            SELECT format, COUNT(*) as count
            FROM classifications
            GROUP BY format
            '''
        )
        stats['formats'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by intent
        cursor.execute(
            '''
            SELECT intent, COUNT(*) as count
            FROM classifications
            GROUP BY intent
            '''
        )
        stats['intents'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by action status
        cursor.execute(
            '''
            SELECT status, COUNT(*) as count
            FROM actions
            GROUP BY status
            '''
        )
        stats['action_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Database size
        stats['db_size_bytes'] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        conn.close()
        
        return stats
