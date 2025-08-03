import sqlite3
from typing import Optional, List
from dataclasses import dataclass
from contextlib import contextmanager
import datetime
import uuid

@dataclass
class InterviewSession:
    interview_id: str
    candidate_name: str
    position: str
    start_time: str
    end_time: Optional[str]
    technical_score: int
    behavioral_score: int
    overall_impression: str
    interview_data: str
    status: str

class DatabaseDriver:
    def __init__(self, db_path: str = "ai_interview_db.sqlite"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create interview_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    interview_id TEXT PRIMARY KEY,
                    candidate_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    technical_score INTEGER DEFAULT 0,
                    behavioral_score INTEGER DEFAULT 0,
                    overall_impression TEXT,
                    interview_data TEXT,
                    status TEXT DEFAULT 'in_progress'
                )
            """)
            
            # Create interview_analytics table for reporting
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interview_id TEXT,
                    metric_name TEXT,
                    metric_value TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (interview_id) REFERENCES interview_sessions (interview_id)
                )
            """)
            
            conn.commit()

    def create_interview_session(self, candidate_name: str, position: str) -> str:
        """Create a new interview session and return the interview ID"""
        interview_id = str(uuid.uuid4())
        # Fix: Convert datetime to string immediately
        start_time = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interview_sessions 
                (interview_id, candidate_name, position, start_time, status) 
                VALUES (?, ?, ?, ?, ?)
            """, (interview_id, candidate_name, position, start_time, 'in_progress'))
            conn.commit()
            
        return interview_id

    def complete_interview_session(
        self, 
        interview_id: str, 
        technical_score: int, 
        behavioral_score: int,
        overall_impression: str,
        interview_data: str
    ) -> bool:
        """Mark an interview session as completed with final scores"""
        # Fix: Convert datetime to string immediately
        end_time = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE interview_sessions 
                SET end_time = ?, technical_score = ?, behavioral_score = ?, 
                    overall_impression = ?, interview_data = ?, status = 'completed'
                WHERE interview_id = ?
            """, (end_time, technical_score, behavioral_score, 
                  overall_impression, interview_data, interview_id))
            
            conn.commit()
            return cursor.rowcount > 0

    def get_interview_session(self, interview_id: str) -> Optional[InterviewSession]:
        """Get an interview session by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM interview_sessions WHERE interview_id = ?", (interview_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return InterviewSession(
                interview_id=row[0],
                candidate_name=row[1],
                position=row[2],
                start_time=row[3],
                end_time=row[4],
                technical_score=row[5],
                behavioral_score=row[6],
                overall_impression=row[7] or "",  # Handle None values
                interview_data=row[8] or "",      # Handle None values
                status=row[9]
            )

    def get_recent_interviews(self, limit: int = 10) -> List[InterviewSession]:
        """Get recent interview sessions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM interview_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [
                InterviewSession(
                    interview_id=row[0],
                    candidate_name=row[1],
                    position=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    technical_score=row[5],
                    behavioral_score=row[6],
                    overall_impression=row[7] or "",  # Handle None values
                    interview_data=row[8] or "",      # Handle None values
                    status=row[9]
                ) for row in rows
            ]

    def get_interview_analytics(self, position: str = None) -> dict:
        """Get analytics data for interviews"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Base query
            base_query = "SELECT * FROM interview_sessions WHERE status = 'completed'"
            params = []
            
            if position:
                base_query += " AND position = ?"
                params.append(position)
            
            cursor.execute(base_query, params)
            completed_interviews = cursor.fetchall()
            
            if not completed_interviews:
                return {
                    "total_interviews": 0,
                    "average_technical_score": 0.0,
                    "average_behavioral_score": 0.0,
                    "position_breakdown": {}
                }
            
            total_interviews = len(completed_interviews)
            avg_technical = sum(row[5] for row in completed_interviews) / total_interviews
            avg_behavioral = sum(row[6] for row in completed_interviews) / total_interviews
            
            # Position breakdown
            position_breakdown = {}
            for row in completed_interviews:
                pos = row[2]
                if pos not in position_breakdown:
                    position_breakdown[pos] = {
                        "count": 0,
                        "avg_technical": 0.0,
                        "avg_behavioral": 0.0
                    }
                position_breakdown[pos]["count"] += 1
                position_breakdown[pos]["avg_technical"] += row[5]
                position_breakdown[pos]["avg_behavioral"] += row[6]
            
            # Calculate averages for each position
            for pos_data in position_breakdown.values():
                count = pos_data["count"]
                pos_data["avg_technical"] = round(pos_data["avg_technical"] / count, 2)
                pos_data["avg_behavioral"] = round(pos_data["avg_behavioral"] / count, 2)
            
            return {
                "total_interviews": total_interviews,
                "average_technical_score": round(avg_technical, 2),
                "average_behavioral_score": round(avg_behavioral, 2),
                "position_breakdown": position_breakdown
            }

    def add_interview_metric(self, interview_id: str, metric_name: str, metric_value: str):
        """Add a custom metric for an interview"""
        # Fix: Convert datetime to string immediately
        timestamp = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interview_analytics 
                (interview_id, metric_name, metric_value, timestamp) 
                VALUES (?, ?, ?, ?)
            """, (interview_id, metric_name, metric_value, timestamp))
            conn.commit()