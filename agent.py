from __future__ import annotations
import asyncio
import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, function_tool, RunContext
from livekit.plugins import deepgram, cartesia, google, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import os
import datetime
import json
import enum
from typing import Annotated
from db_driver import DatabaseDriver

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
DB = DatabaseDriver()

class InterviewPhase(enum.Enum):
    INTRODUCTION = "introduction"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CLOSING = "closing"
    COMPLETED = "completed"

class InterviewData:
    def __init__(self):
        self.candidate_name = ""
        self.position = ""
        self.start_time = datetime.datetime.now()
        self.current_phase = InterviewPhase.INTRODUCTION
        self.questions_asked = []
        self.responses = []
        self.notes = []
        self.technical_score = 0
        self.behavioral_score = 0
        self.overall_impression = ""
        self.interview_id = None

# Interview prompts and instructions
INTERVIEW_INSTRUCTIONS = """You are an AI interviewer conducting a professional job interview. Follow these guidelines:

1. INTRODUCTION PHASE: Start by welcoming the candidate warmly, ask for their name and the position they're applying for.

2. TECHNICAL PHASE: Ask 3-5 relevant technical questions based on their position:
   - For Software Engineers: coding problems, system design, algorithms
   - For Data Scientists: ML concepts, statistics, data processing
   - For Product Managers: product strategy, metrics, prioritization
   - For Designers: design process, user research, portfolio discussion

3. BEHAVIORAL PHASE: Ask 3-5 behavioral questions:
   - Tell me about a challenging project you worked on
   - How do you handle conflicts with team members?
   - Describe a time you had to learn something new quickly
   - What motivates you in your work?

4. CLOSING PHASE: Wrap up the interview, ask if they have questions, explain next steps.

IMPORTANT RULES:
- Be conversational and natural, like a human interviewer
- Listen actively and ask follow-up questions
- Score responses on a 1-5 scale (1=poor, 5=excellent)
- Take notes on interesting points
- Move through phases naturally based on conversation flow
- Be encouraging but professional
- Allow for interruptions and natural conversation flow

Use the provided functions to record information and manage the interview flow."""

WELCOME_MESSAGE = "Hello! Welcome to your interview today. I'm excited to speak with you. Could you please start by telling me your name and what position you're interviewing for?"

class InterviewAgent(Agent):
    """AI Interview Agent using LiveKit Agents 1.0+"""
    
    def __init__(self):
        super().__init__(instructions=INTERVIEW_INSTRUCTIONS)
        
        # Interview state management
        self.interview_data = InterviewData()
        self.question_count = 0
        self.max_questions_per_phase = 5
        
    @function_tool()
    async def record_candidate_info(self, ctx: RunContext, name: str, position: str):
        """Record candidate's basic information
        
        Args:
            name: The candidate's full name
            position: The position they're interviewing for
        """
        logger.info(f"Recording candidate info - Name: {name}, Position: {position}")
        self.interview_data.candidate_name = name
        self.interview_data.position = position.lower()
        
        # Save to database
        interview_id = DB.create_interview_session(name, position)
        self.interview_data.interview_id = interview_id
        
        return f"Thank you, {name}! I've recorded that you're interviewing for the {position} position. Let's begin with some general questions about your background."
    
    @function_tool()
    async def record_question(self, ctx: RunContext, question: str):
        """Record a question that was asked to the candidate
        
        Args:
            question: The question that was asked
        """
        logger.info(f"Recording question: {question}")
        self.interview_data.questions_asked.append({
            "question": question,
            "timestamp": datetime.datetime.now().isoformat(),
            "phase": self.interview_data.current_phase.value
        })
        self.question_count += 1
        return "Question recorded."
    
    @function_tool()
    async def record_response(self, ctx: RunContext, response: str, quality_score: int):
        """Record the candidate's response to a question
        
        Args:
            response: The candidate's response
            quality_score: Quality score from 1-5 for the response
        """
        logger.info(f"Recording response with score {quality_score}")
        self.interview_data.responses.append({
            "response": response,
            "quality_score": quality_score,
            "timestamp": datetime.datetime.now().isoformat(),
            "phase": self.interview_data.current_phase.value
        })
        
        # Update scores based on phase
        if self.interview_data.current_phase == InterviewPhase.TECHNICAL:
            self.interview_data.technical_score += quality_score
        elif self.interview_data.current_phase == InterviewPhase.BEHAVIORAL:
            self.interview_data.behavioral_score += quality_score
            
        return "Response recorded and scored."
    
    @function_tool()
    async def add_interviewer_note(self, ctx: RunContext, note: str):
        """Add interviewer notes about the candidate
        
        Args:
            note: Observation or note about the candidate
        """
        logger.info(f"Adding interviewer note: {note}")
        self.interview_data.notes.append({
            "note": note,
            "timestamp": datetime.datetime.now().isoformat(),
            "phase": self.interview_data.current_phase.value
        })
        return "Note added."
    
    @function_tool()
    async def advance_interview_phase(self, ctx: RunContext):
        """Move to the next phase of the interview"""
        current_phase = self.interview_data.current_phase
        
        if current_phase == InterviewPhase.INTRODUCTION:
            self.interview_data.current_phase = InterviewPhase.TECHNICAL
            self.question_count = 0
            return "Moving to technical questions phase."
        elif current_phase == InterviewPhase.TECHNICAL:
            self.interview_data.current_phase = InterviewPhase.BEHAVIORAL
            self.question_count = 0
            return "Moving to behavioral questions phase."
        elif current_phase == InterviewPhase.BEHAVIORAL:
            self.interview_data.current_phase = InterviewPhase.CLOSING
            return "Moving to closing phase."
        elif current_phase == InterviewPhase.CLOSING:
            self.interview_data.current_phase = InterviewPhase.COMPLETED
            return "Interview completed."
        else:
            return "Interview already completed."
    
    @function_tool()
    async def get_interview_status(self, ctx: RunContext):
        """Get the current interview status and phase"""
        duration = datetime.datetime.now() - self.interview_data.start_time
        return {
            "candidate_name": self.interview_data.candidate_name,
            "position": self.interview_data.position,
            "current_phase": self.interview_data.current_phase.value,
            "duration_minutes": int(duration.total_seconds() / 60),
            "questions_asked": len(self.interview_data.questions_asked),
            "questions_in_current_phase": self.question_count
        }
    
    @function_tool()
    async def complete_interview(self, ctx: RunContext, overall_impression: str):
        """Complete the interview and generate final summary
        
        Args:
            overall_impression: Overall impression of the candidate
        """
        logger.info("Completing interview")
        self.interview_data.overall_impression = overall_impression
        self.interview_data.current_phase = InterviewPhase.COMPLETED
        
        # Save final data to database
        if hasattr(self.interview_data, 'interview_id') and self.interview_data.interview_id:
            DB.complete_interview_session(
                self.interview_data.interview_id,
                self.interview_data.technical_score,
                self.interview_data.behavioral_score,
                overall_impression,
                json.dumps({
                    "questions_asked": self.interview_data.questions_asked,
                    "responses": self.interview_data.responses,
                    "notes": self.interview_data.notes
                })
            )
        
        return "Interview completed and data saved. Thank you for your time!"
    
    def should_advance_phase(self) -> bool:
        """Check if we should move to the next interview phase"""
        return (self.question_count >= self.max_questions_per_phase and 
                self.interview_data.current_phase != InterviewPhase.COMPLETED)

def prewarm_process(proc: agents.JobProcess):
    """Prewarm function to load models and components ahead of time"""
    logger.info("Prewarming process: loading models...")
    
    # Prewarm VAD model
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("VAD model loaded")
    
    # You could also prewarm other models here
    # proc.userdata["turn_detector"] = MultilingualModel()
    
    logger.info("Process prewarming completed")

async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the AI interview agent using Agents 1.0+"""
    
    logger.info("Starting AI Interview Agent")
    
    # Create the interview agent
    agent = InterviewAgent()
    
    # Create AgentSession with AI components
    session = AgentSession(
        # Speech-to-Text: Deepgram
        stt=deepgram.STT(
            model="nova-2-conversationalai",
            language="en",
            smart_format=True,
            interim_results=True,
            utterance_end_ms=1000,
            vad_events=True,
            noise_reduction=True,
            profanity_filter=False,
        ),
        
        # Large Language Model: Google Gemini
        llm=google.LLM(
            model="gemini-1.5-flash",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.7,
            max_output_tokens=1024,
        ),
        
        # Text-to-Speech: Cartesia
        tts=cartesia.TTS(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Professional female voice
            model="sonic-english",
            sample_rate=24000,
            speed=1.0,
            emotion=["positivity:medium", "curiosity:medium"]
        ),
        
        # Voice Activity Detection: Use prewarmed VAD if available
        vad=ctx.proc.userdata.get("vad", silero.VAD.load()),
        
        # Turn Detection: Enhanced end-of-turn detection
        turn_detection=MultilingualModel(),
    )
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent
    )
    
    # Send welcome message
    await session.say(WELCOME_MESSAGE)
    
    logger.info("AI Interview Agent is ready and waiting for participants")

if __name__ == "__main__":
    # Define worker options with correct parameters
    worker_options = agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        # Add prewarm function to load models ahead of time for better performance
        prewarm_fnc=prewarm_process,
        # Optional: Custom load function for resource management
        # load_fnc=compute_load,
        # load_threshold=0.8,
    )
    
    # Start the worker
    agents.cli.run_app(worker_options)