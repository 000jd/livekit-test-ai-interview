import enum
import logging
import datetime
from typing import List, Dict, Any

logger = logging.getLogger("interview-data")
logger.setLevel(logging.INFO)

class InterviewPhase(enum.Enum):
    INTRODUCTION = "introduction"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CLOSING = "closing"
    COMPLETED = "completed"

class InterviewData:
    """Data structure to hold interview session information"""
    
    def __init__(self):
        self.candidate_name = ""
        self.position = ""
        self.start_time = datetime.datetime.now()
        self.current_phase = InterviewPhase.INTRODUCTION
        self.questions_asked: List[Dict[str, Any]] = []
        self.responses: List[Dict[str, Any]] = []
        self.notes: List[Dict[str, Any]] = []
        self.technical_score = 0
        self.behavioral_score = 0
        self.overall_impression = ""
        self.interview_id = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert interview data to dictionary for serialization"""
        return {
            "candidate_name": self.candidate_name,
            "position": self.position,
            "start_time": self.start_time.isoformat(),
            "current_phase": self.current_phase.value,
            "questions_asked": self.questions_asked,
            "responses": self.responses,
            "notes": self.notes,
            "technical_score": self.technical_score,
            "behavioral_score": self.behavioral_score,
            "overall_impression": self.overall_impression,
            "interview_id": self.interview_id
        }

    def get_duration_minutes(self) -> int:
        """Get interview duration in minutes"""
        duration = datetime.datetime.now() - self.start_time
        return int(duration.total_seconds() / 60)

    def get_total_questions(self) -> int:
        """Get total number of questions asked"""
        return len(self.questions_asked)

    def get_average_technical_score(self) -> float:
        """Get average technical score"""
        technical_responses = [r for r in self.responses if r.get("phase") == "technical"]
        if not technical_responses:
            return 0.0
        return sum(r["quality_score"] for r in technical_responses) / len(technical_responses)

    def get_average_behavioral_score(self) -> float:
        """Get average behavioral score"""
        behavioral_responses = [r for r in self.responses if r.get("phase") == "behavioral"]
        if not behavioral_responses:
            return 0.0
        return sum(r["quality_score"] for r in behavioral_responses) / len(behavioral_responses)

class InterviewMetrics:
    """Class to calculate interview metrics and analytics"""
    
    @staticmethod
    def calculate_completion_rate(interview_data: InterviewData) -> float:
        """Calculate interview completion rate as percentage"""
        total_phases = len(InterviewPhase) - 1  # Exclude COMPLETED
        current_phase_index = list(InterviewPhase).index(interview_data.current_phase)
        return (current_phase_index / total_phases) * 100

    @staticmethod
    def get_phase_summary(interview_data: InterviewData) -> Dict[str, Any]:
        """Get summary of each interview phase"""
        summary = {}
        
        for phase in InterviewPhase:
            if phase == InterviewPhase.COMPLETED:
                continue
                
            phase_questions = [q for q in interview_data.questions_asked if q.get("phase") == phase.value]
            phase_responses = [r for r in interview_data.responses if r.get("phase") == phase.value]
            
            summary[phase.value] = {
                "questions_count": len(phase_questions),
                "responses_count": len(phase_responses),
                "average_score": sum(r["quality_score"] for r in phase_responses) / len(phase_responses) if phase_responses else 0,
                "completed": len(phase_questions) > 0
            }
        
        return summary

    @staticmethod
    def generate_interview_report(interview_data: InterviewData) -> Dict[str, Any]:
        """Generate a comprehensive interview report"""
        return {
            "interview_summary": {
                "candidate_name": interview_data.candidate_name,
                "position": interview_data.position,
                "duration_minutes": interview_data.get_duration_minutes(),
                "completion_rate": InterviewMetrics.calculate_completion_rate(interview_data),
                "current_phase": interview_data.current_phase.value
            },
            "scoring": {
                "technical_score": interview_data.technical_score,
                "behavioral_score": interview_data.behavioral_score,
                "average_technical": interview_data.get_average_technical_score(),
                "average_behavioral": interview_data.get_average_behavioral_score(),
                "total_questions": interview_data.get_total_questions()
            },
            "phase_breakdown": InterviewMetrics.get_phase_summary(interview_data),
            "overall_impression": interview_data.overall_impression,
            "notes_count": len(interview_data.notes)
        }