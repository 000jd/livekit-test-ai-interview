import sqlite3
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
import datetime
import uuid
import json

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
    recording_id: Optional[str] = None
    recording_url: Optional[str] = None
    transcript_url: Optional[str] = None
    recording_status: Optional[str] = None

@dataclass
class RecordingInfo:
    recording_id: str
    interview_id: str
    egress_id: str
    room_name: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    file_size: Optional[int] = None
    duration_seconds: Optional[int] = None
    s3_url: Optional[str] = None

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
            
            # Create interview_sessions table with recording fields
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
                    status TEXT DEFAULT 'in_progress',
                    recording_id TEXT,
                    recording_url TEXT,
                    transcript_url TEXT,
                    recording_status TEXT DEFAULT 'pending'
                )
            """)
            
            # Create recordings table for detailed recording info
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordings (
                    recording_id TEXT PRIMARY KEY,
                    interview_id TEXT,
                    egress_id TEXT,
                    room_name TEXT,
                    status TEXT DEFAULT 'recording',
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    file_size INTEGER,
                    duration_seconds INTEGER,
                    s3_url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (interview_id) REFERENCES interview_sessions (interview_id)
                )
            """)
            
            # Create transcripts table for transcript metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    transcript_id TEXT PRIMARY KEY,
                    interview_id TEXT,
                    s3_url TEXT,
                    word_count INTEGER,
                    character_count INTEGER,
                    duration_seconds INTEGER,
                    language TEXT DEFAULT 'en',
                    confidence_score REAL,
                    processing_status TEXT DEFAULT 'processing',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (interview_id) REFERENCES interview_sessions (interview_id)
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
        start_time = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interview_sessions 
                (interview_id, candidate_name, position, start_time, status, recording_status) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (interview_id, candidate_name, position, start_time, 'in_progress', 'pending'))
            conn.commit()
            
        return interview_id

    def create_recording_entry(
        self, 
        interview_id: str, 
        egress_id: str, 
        room_name: str
    ) -> str:
        """Create a recording entry and return recording ID"""
        recording_id = str(uuid.uuid4())
        start_time = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recordings 
                (recording_id, interview_id, egress_id, room_name, status, start_time) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (recording_id, interview_id, egress_id, room_name, 'recording', start_time))
            
            # Update interview session with recording ID
            cursor.execute("""
                UPDATE interview_sessions 
                SET recording_id = ?, recording_status = 'recording'
                WHERE interview_id = ?
            """, (recording_id, interview_id))
            
            conn.commit()
            
        return recording_id

    def update_recording_status(
        self, 
        recording_id: str, 
        status: str, 
        s3_url: Optional[str] = None,
        file_size: Optional[int] = None,
        duration_seconds: Optional[int] = None
    ) -> bool:
        """Update recording status and metadata"""
        end_time = datetime.datetime.now().isoformat() if status == 'completed' else None
        updated_at = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE recordings 
                SET status = ?, end_time = ?, s3_url = ?, file_size = ?, 
                    duration_seconds = ?, updated_at = ?
                WHERE recording_id = ?
            """, (status, end_time, s3_url, file_size, duration_seconds, updated_at, recording_id))
            
            # Update interview session recording status
            cursor.execute("""
                UPDATE interview_sessions 
                SET recording_status = ?, recording_url = ?
                WHERE recording_id = ?
            """, (status, s3_url, recording_id))
            
            conn.commit()
            return cursor.rowcount > 0

    def create_transcript_entry(
        self, 
        interview_id: str, 
        s3_url: str,
        word_count: int = 0,
        character_count: int = 0,
        confidence_score: float = 0.0
    ) -> str:
        """Create a transcript entry and return transcript ID"""
        transcript_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transcripts 
                (transcript_id, interview_id, s3_url, word_count, character_count, 
                 confidence_score, processing_status, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (transcript_id, interview_id, s3_url, word_count, character_count, 
                  confidence_score, 'completed', created_at, created_at))
            
            # Update interview session with transcript URL
            cursor.execute("""
                UPDATE interview_sessions 
                SET transcript_url = ?
                WHERE interview_id = ?
            """, (s3_url, interview_id))
            
            conn.commit()
            
        return transcript_id

    def complete_interview_session(
        self, 
        interview_id: str, 
        technical_score: int, 
        behavioral_score: int,
        overall_impression: str,
        interview_data: str
    ) -> bool:
        """Mark an interview session as completed with final scores"""
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
        """Get an interview session by ID with recording info"""
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
                overall_impression=row[7] or "",
                interview_data=row[8] or "",
                status=row[9],
                recording_id=row[10] if len(row) > 10 else None,
                recording_url=row[11] if len(row) > 11 else None,
                transcript_url=row[12] if len(row) > 12 else None,
                recording_status=row[13] if len(row) > 13 else None
            )

    def get_recording_info(self, recording_id: str) -> Optional[RecordingInfo]:
        """Get recording information by recording ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recordings WHERE recording_id = ?", (recording_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return RecordingInfo(
                recording_id=row[0],
                interview_id=row[1],
                egress_id=row[2],
                room_name=row[3],
                status=row[4],
                start_time=row[5],
                end_time=row[6],
                file_size=row[7],
                duration_seconds=row[8],
                s3_url=row[9]
            )

    def get_recent_interviews(self, limit: int = 10, include_recordings: bool = True) -> List[InterviewSession]:
        """Get recent interview sessions with optional recording info"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if include_recordings:
                query = """
                    SELECT i.*, r.s3_url as recording_s3_url, t.s3_url as transcript_s3_url
                    FROM interview_sessions i
                    LEFT JOIN recordings r ON i.recording_id = r.recording_id
                    LEFT JOIN transcripts t ON i.interview_id = t.interview_id
                    ORDER BY i.start_time DESC 
                    LIMIT ?
                """
            else:
                query = """
                    SELECT * FROM interview_sessions 
                    ORDER BY start_time DESC 
                    LIMIT ?
                """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            
            interviews = []
            for row in rows:
                interview = InterviewSession(
                    interview_id=row[0],
                    candidate_name=row[1],
                    position=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    technical_score=row[5],
                    behavioral_score=row[6],
                    overall_impression=row[7] or "",
                    interview_data=row[8] or "",
                    status=row[9],
                    recording_id=row[10] if len(row) > 10 else None,
                    recording_url=row[11] if len(row) > 11 else None,
                    transcript_url=row[12] if len(row) > 12 else None,
                    recording_status=row[13] if len(row) > 13 else None
                )
                
                # If we have additional recording/transcript info from JOIN
                if include_recordings and len(row) > 14:
                    if row[14]:  # recording_s3_url
                        interview.recording_url = row[14]
                    if row[15]:  # transcript_s3_url  
                        interview.transcript_url = row[15]
                
                interviews.append(interview)
            
            return interviews

    def get_interview_analytics(self, position: str = None, include_recording_stats: bool = True) -> dict:
        """Get analytics data for interviews including recording statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Base query for completed interviews
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
                    "position_breakdown": {},
                    "recording_stats": {
                        "total_recordings": 0,
                        "completed_recordings": 0,
                        "failed_recordings": 0,
                        "total_storage_mb": 0
                    }
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
            
            # Recording statistics
            recording_stats = {"total_recordings": 0, "completed_recordings": 0, "failed_recordings": 0, "total_storage_mb": 0}
            
            if include_recording_stats:
                # Get recording statistics
                cursor.execute("SELECT status, file_size FROM recordings")
                recording_rows = cursor.fetchall()
                
                recording_stats["total_recordings"] = len(recording_rows)
                
                for r_row in recording_rows:
                    status = r_row[0]
                    file_size = r_row[1] or 0
                    
                    if status == 'completed':
                        recording_stats["completed_recordings"] += 1
                    elif status == 'failed':
                        recording_stats["failed_recordings"] += 1
                    
                    recording_stats["total_storage_mb"] += file_size / (1024 * 1024) if file_size else 0
                
                recording_stats["total_storage_mb"] = round(recording_stats["total_storage_mb"], 2)
            
            return {
                "total_interviews": total_interviews,
                "average_technical_score": round(avg_technical, 2),
                "average_behavioral_score": round(avg_behavioral, 2),
                "position_breakdown": position_breakdown,
                "recording_stats": recording_stats
            }

    def get_recordings_by_status(self, status: str = None) -> List[RecordingInfo]:
        """Get recordings filtered by status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("SELECT * FROM recordings WHERE status = ? ORDER BY start_time DESC", (status,))
            else:
                cursor.execute("SELECT * FROM recordings ORDER BY start_time DESC")
            
            rows = cursor.fetchall()
            return [
                RecordingInfo(
                    recording_id=row[0],
                    interview_id=row[1],
                    egress_id=row[2],
                    room_name=row[3],
                    status=row[4],
                    start_time=row[5],
                    end_time=row[6],
                    file_size=row[7],
                    duration_seconds=row[8],
                    s3_url=row[9]
                ) for row in rows
            ]

    def add_interview_metric(self, interview_id: str, metric_name: str, metric_value: str):
        """Add a custom metric for an interview"""
        timestamp = datetime.datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interview_analytics 
                (interview_id, metric_name, metric_value, timestamp) 
                VALUES (?, ?, ?, ?)
            """, (interview_id, metric_name, metric_value, timestamp))
            conn.commit()

    def cleanup_old_interviews(self, days_old: int = 30) -> int:
        """Clean up interviews older than specified days (soft delete)"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        cutoff_iso = cutoff_date.isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE interview_sessions 
                SET status = 'archived'
                WHERE start_time < ? AND status != 'archived'
            """, (cutoff_iso,))
            
            archived_count = cursor.rowcount
            conn.commit()
            
        return archived_count

    def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get recording storage usage
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_recordings,
                    SUM(file_size) as total_bytes,
                    AVG(file_size) as avg_file_size,
                    SUM(duration_seconds) as total_duration_seconds
                FROM recordings 
                WHERE status = 'completed' AND file_size IS NOT NULL
            """)
            recording_stats = cursor.fetchone()
            
            # Get transcript count
            cursor.execute("SELECT COUNT(*) FROM transcripts WHERE processing_status = 'completed'")
            transcript_count = cursor.fetchone()[0]
            
            # Get interviews by month for trend analysis
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', start_time) as month,
                    COUNT(*) as interview_count
                FROM interview_sessions 
                WHERE status = 'completed'
                GROUP BY strftime('%Y-%m', start_time)
                ORDER BY month DESC
                LIMIT 12
            """)
            monthly_trends = cursor.fetchall()
            
            return {
                "recording_storage": {
                    "total_recordings": recording_stats[0] or 0,
                    "total_size_gb": round((recording_stats[1] or 0) / (1024**3), 2),
                    "average_file_size_mb": round((recording_stats[2] or 0) / (1024**2), 2),
                    "total_duration_hours": round((recording_stats[3] or 0) / 3600, 2)
                },
                "transcript_count": transcript_count,
                "monthly_trends": [{"month": row[0], "count": row[1]} for row in monthly_trends]
            }