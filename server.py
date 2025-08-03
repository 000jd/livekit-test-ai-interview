import os
import uuid
import time
import jwt  # PyJWT for manual token generation
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from livekit import api
from livekit.api import LiveKitAPI, ListRoomsRequest, CreateRoomRequest
# Note: We'll use manual JWT generation instead of the problematic AccessToken class
from dotenv import load_dotenv
from db_driver import DatabaseDriver, InterviewSession
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Interview Backend API",
    description="Backend service for AI-powered interview sessions using LiveKit",
    version="1.0.0"
)

# Initialize database
db = DatabaseDriver()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class TokenRequest(BaseModel):
    candidate_name: str
    position: str
    room_name: Optional[str] = None

class TokenResponse(BaseModel):
    token: str
    room_name: str
    interview_id: str

class InterviewSummary(BaseModel):
    interview_id: str
    candidate_name: str
    position: str
    start_time: str
    end_time: Optional[str]
    technical_score: int
    behavioral_score: int
    overall_impression: str
    status: str

class AnalyticsResponse(BaseModel):
    total_interviews: int
    average_technical_score: float
    average_behavioral_score: float
    position_breakdown: dict

# Helper functions
def generate_livekit_token(api_key: str, api_secret: str, room_name: str, identity: str, name: str) -> str:
    """Generate LiveKit JWT token manually using PyJWT"""
    current_time = int(time.time())
    
    # Token payload following LiveKit specification
    payload = {
        "iss": api_key,              # API Key (issuer)
        "sub": identity,             # Participant identity (subject)
        "iat": current_time,         # Issued at
        "exp": current_time + 7200,  # Expires in 2 hours
        "nbf": current_time,         # Not before (valid from now)
        "name": name,                # Participant display name
        "video": {                   # Video grants
            "room": room_name,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
            "canUpdateOwnMetadata": True
        }
    }
    
    # Generate JWT token
    token = jwt.encode(payload, api_secret, algorithm="HS256")
    return token

async def generate_unique_room_name() -> str:
    """Generate a unique room name"""
    while True:
        room_name = f"interview-{str(uuid.uuid4())[:8]}"
        try:
            lk_api = LiveKitAPI()
            rooms = await lk_api.room.list_rooms(ListRoomsRequest())
            existing_rooms = [room.name for room in rooms.rooms]
            await lk_api.aclose()
            
            if room_name not in existing_rooms:
                return room_name
        except Exception as e:
            logger.error(f"Error checking existing rooms: {e}")
            return room_name  # Return anyway if we can't check

async def create_interview_room(room_name: str) -> bool:
    """Create a new interview room with basic settings"""
    try:
        lk_api = LiveKitAPI()
        
        # Create room with basic settings (RoomOptions not available in newer versions)
        # We'll use CreateRoomRequest with the available parameters
        room_request = CreateRoomRequest(
            name=room_name,
            empty_timeout=300,  # 5 minutes timeout when empty
            max_participants=10,  # Max participants
            # Note: Audio settings like echo_cancellation are handled client-side
            # or through the agent configuration, not room creation
        )
        
        await lk_api.room.create_room(room_request)
        await lk_api.aclose()
        return True
    except Exception as e:
        logger.error(f"Error creating room {room_name}: {e}")
        return False

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "AI Interview Backend API is running", "status": "healthy"}

@app.post("/interview/token", response_model=TokenResponse)
async def generate_interview_token(request: TokenRequest):
    """Generate a LiveKit token for interview session"""
    try:
        # Generate or use provided room name
        room_name = request.room_name or await generate_unique_room_name()
        
        # Create the interview room
        room_created = await create_interview_room(room_name)
        if not room_created:
            logger.warning(f"Could not create room {room_name}, proceeding anyway")
        
        # Create interview session in database
        interview_id = db.create_interview_session(
            candidate_name=request.candidate_name,
            position=request.position
        )
        
        # Generate LiveKit token - Manual JWT generation (bypasses LiveKit SDK issues)
        try:
            # Get API credentials
            api_key = os.getenv("LIVEKIT_API_KEY")
            api_secret = os.getenv("LIVEKIT_API_SECRET")
            
            if not api_key or not api_secret:
                raise HTTPException(status_code=500, detail="LiveKit credentials not configured")
            
            # Generate token manually
            jwt_token = generate_livekit_token(
                api_key=api_key,
                api_secret=api_secret,
                room_name=room_name,
                identity=f"candidate-{interview_id}",
                name=request.candidate_name
            )
            
        except Exception as token_error:
            logger.error(f"Token generation error: {token_error}")
            raise HTTPException(status_code=500, detail=f"Token generation failed: {str(token_error)}")
        
        logger.info(f"Generated token for {request.candidate_name} in room {room_name}")
        
        return TokenResponse(
            token=jwt_token,
            room_name=room_name,
            interview_id=interview_id
        )
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")

@app.get("/interview/{interview_id}", response_model=InterviewSummary)
async def get_interview(interview_id: str):
    """Get interview details by ID"""
    try:
        interview = db.get_interview_session(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        return InterviewSummary(
            interview_id=interview.interview_id,
            candidate_name=interview.candidate_name,
            position=interview.position,
            start_time=interview.start_time,
            end_time=interview.end_time,
            technical_score=interview.technical_score,
            behavioral_score=interview.behavioral_score,
            overall_impression=interview.overall_impression or "",
            status=interview.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve interview")

@app.get("/interviews", response_model=List[InterviewSummary])
async def list_interviews(
    limit: int = Query(10, ge=1, le=100),
    position: Optional[str] = Query(None)
):
    """List recent interviews with optional filtering"""
    try:
        interviews = db.get_recent_interviews(limit=limit)
        
        # Filter by position if specified
        if position:
            interviews = [i for i in interviews if i.position.lower() == position.lower()]
        
        return [
            InterviewSummary(
                interview_id=interview.interview_id,
                candidate_name=interview.candidate_name,
                position=interview.position,
                start_time=interview.start_time,
                end_time=interview.end_time,
                technical_score=interview.technical_score,
                behavioral_score=interview.behavioral_score,
                overall_impression=interview.overall_impression or "",
                status=interview.status
            )
            for interview in interviews
        ]
        
    except Exception as e:
        logger.error(f"Error listing interviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve interviews")

@app.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(position: Optional[str] = Query(None)):
    """Get interview analytics and statistics"""
    try:
        analytics = db.get_interview_analytics(position=position)
        
        return AnalyticsResponse(
            total_interviews=analytics["total_interviews"],
            average_technical_score=analytics["average_technical_score"],
            average_behavioral_score=analytics["average_behavioral_score"],
            position_breakdown=analytics["position_breakdown"]
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

@app.get("/rooms/active")
async def get_active_rooms():
    """Get list of active LiveKit rooms"""
    try:
        lk_api = LiveKitAPI()
        rooms = await lk_api.room.list_rooms(ListRoomsRequest())
        await lk_api.aclose()
        
        active_rooms = [
            {
                "name": room.name,
                "num_participants": room.num_participants,
                "creation_time": room.creation_time,
                "empty_timeout": room.empty_timeout,
            }
            for room in rooms.rooms
        ]
        
        return {"active_rooms": active_rooms, "total_count": len(active_rooms)}
        
    except Exception as e:
        logger.error(f"Error getting active rooms: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active rooms")

@app.delete("/interview/{interview_id}")
async def delete_interview(interview_id: str):
    """Delete an interview record (admin function)"""
    try:
        # Note: This is a simple implementation
        # In production, you'd want proper authentication and authorization
        interview = db.get_interview_session(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # For now, we'll just mark as deleted (you could implement soft delete)
        # db.delete_interview_session(interview_id)  # Implement this method
        
        return {"message": f"Interview {interview_id} deletion requested"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete interview")

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    try:
        # Check database connection
        db_status = "healthy"
        recent_interviews = []
        try:
            recent_interviews = db.get_recent_interviews(limit=1)
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check LiveKit connection
        lk_status = "healthy"
        try:
            lk_api = LiveKitAPI()
            await lk_api.room.list_rooms(ListRoomsRequest())
            await lk_api.aclose()
        except Exception as e:
            lk_status = f"unhealthy: {str(e)}"
        
        # Check API keys
        api_keys_status = {
            "google_api_key": "present" if os.getenv("GOOGLE_API_KEY") else "missing",
            "deepgram_api_key": "present" if os.getenv("DEEPGRAM_API_KEY") else "missing",
            "cartesia_api_key": "present" if os.getenv("CARTESIA_API_KEY") else "missing",
            "livekit_api_key": "present" if os.getenv("LIVEKIT_API_KEY") else "missing",
            "livekit_api_secret": "present" if os.getenv("LIVEKIT_API_SECRET") else "missing",
        }
        
        overall_status = "healthy" if all([
            db_status == "healthy",
            lk_status == "healthy",
            all(status == "present" for status in api_keys_status.values())
        ]) else "degraded"
        
        return {
            "status": overall_status,
            "database": db_status,
            "livekit": lk_status,
            "api_keys": api_keys_status,
            "timestamp": recent_interviews[0].start_time if recent_interviews else None
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,  # Set to False in production
        log_level="info",
        access_log=True,
    )