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
from livekit.api import LiveKitAPI, ListRoomsRequest, CreateRoomRequest, ListEgressRequest
import boto3
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
    title="AI Interview Backend API with Recording",
    description="Backend service for AI-powered interview sessions with recording and S3 storage",
    version="1.0.0"
)

# Initialize database
db = DatabaseDriver()

# Initialize S3 client
s3_client = None
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )
    logger.info("S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    s3_client = None

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
    record_session: bool = True

class TokenResponse(BaseModel):
    token: str
    room_name: str
    interview_id: str
    recording_enabled: bool

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
    recording_url: Optional[str] = None
    transcript_url: Optional[str] = None

class RecordingInfo(BaseModel):
    egress_id: str
    room_name: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    file_url: Optional[str] = None

class AnalyticsResponse(BaseModel):
    total_interviews: int
    average_technical_score: float
    average_behavioral_score: float
    position_breakdown: dict
    recordings_count: int
    transcripts_available: int

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
    """Create a new interview room with recording capabilities"""
    try:
        lk_api = LiveKitAPI()
        
        # Create room with recording settings
        room_request = CreateRoomRequest(
            name=room_name,
            empty_timeout=300,  # 5 minutes timeout when empty
            max_participants=10,  # Max participants
        )
        
        await lk_api.room.create_room(room_request)
        await lk_api.aclose()
        return True
    except Exception as e:
        logger.error(f"Error creating room {room_name}: {e}")
        return False

def get_s3_recording_url(interview_id: str) -> Optional[str]:
    """Get S3 recording URL for an interview"""
    try:
        if not s3_client:
            return None
        
        bucket_name = os.getenv('S3_BUCKET_NAME')
        prefix = f"interviews/{interview_id}/"
        
        # List objects in the interview folder
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        # Look for video files
        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith(('.mp4', '.webm', '.mov')):
                # Generate presigned URL
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': key},
                    ExpiresIn=3600  # 1 hour
                )
                return url
        
        return None
    except Exception as e:
        logger.error(f"Error getting S3 recording URL: {e}")
        return None

def get_s3_transcript_url(interview_id: str) -> Optional[str]:
    """Get S3 transcript URL for an interview"""
    try:
        if not s3_client:
            return None
        
        bucket_name = os.getenv('S3_BUCKET_NAME')
        transcript_key = f"interviews/{interview_id}/transcript.json"
        
        # Check if transcript exists
        try:
            s3_client.head_object(Bucket=bucket_name, Key=transcript_key)
            # Generate presigned URL
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': transcript_key},
                ExpiresIn=3600  # 1 hour
            )
            return url
        except s3_client.exceptions.NoSuchKey:
            return None
        
    except Exception as e:
        logger.error(f"Error getting S3 transcript URL: {e}")
        return None

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "AI Interview Backend API with Recording is running", "status": "healthy"}

@app.post("/interview/token", response_model=TokenResponse)
async def generate_interview_token(request: TokenRequest):
    """Generate a LiveKit token for interview session with optional recording"""
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
        
        # Generate LiveKit token - Manual JWT generation
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
        
        logger.info(f"Generated token for {request.candidate_name} in room {room_name} with recording: {request.record_session}")
        
        return TokenResponse(
            token=jwt_token,
            room_name=room_name,
            interview_id=interview_id,
            recording_enabled=request.record_session
        )
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")

@app.get("/interview/{interview_id}", response_model=InterviewSummary)
async def get_interview(interview_id: str):
    """Get interview details by ID with recording and transcript URLs"""
    try:
        interview = db.get_interview_session(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Get recording URL from S3
        recording_url = get_s3_recording_url(interview_id)
        
        # Get transcript URL from S3
        transcript_url = get_s3_transcript_url(interview_id)
        
        return InterviewSummary(
            interview_id=interview.interview_id,
            candidate_name=interview.candidate_name,
            position=interview.position,
            start_time=interview.start_time,
            end_time=interview.end_time,
            technical_score=interview.technical_score,
            behavioral_score=interview.behavioral_score,
            overall_impression=interview.overall_impression or "",
            status=interview.status,
            recording_url=recording_url,
            transcript_url=transcript_url
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
    """List recent interviews with optional filtering and recording info"""
    try:
        interviews = db.get_recent_interviews(limit=limit)
        
        # Filter by position if specified
        if position:
            interviews = [i for i in interviews if i.position.lower() == position.lower()]
        
        interview_summaries = []
        for interview in interviews:
            # Get recording and transcript URLs
            recording_url = get_s3_recording_url(interview.interview_id)
            transcript_url = get_s3_transcript_url(interview.interview_id)
            
            interview_summaries.append(
                InterviewSummary(
                    interview_id=interview.interview_id,
                    candidate_name=interview.candidate_name,
                    position=interview.position,
                    start_time=interview.start_time,
                    end_time=interview.end_time,
                    technical_score=interview.technical_score,
                    behavioral_score=interview.behavioral_score,
                    overall_impression=interview.overall_impression or "",
                    status=interview.status,
                    recording_url=recording_url,
                    transcript_url=transcript_url
                )
            )
        
        return interview_summaries
        
    except Exception as e:
        logger.error(f"Error listing interviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve interviews")

@app.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(position: Optional[str] = Query(None)):
    """Get interview analytics and statistics including recording data"""
    try:
        analytics = db.get_interview_analytics(position=position)
        
        # Count recordings and transcripts available
        recordings_count = 0
        transcripts_available = 0
        
        if s3_client:
            bucket_name = os.getenv('S3_BUCKET_NAME')
            try:
                # List all interviews to check recordings
                interviews = db.get_recent_interviews(limit=1000)  # Get all
                
                for interview in interviews:
                    # Check for recordings
                    try:
                        prefix = f"interviews/{interview.interview_id}/"
                        response = s3_client.list_objects_v2(
                            Bucket=bucket_name,
                            Prefix=prefix
                        )
                        
                        has_recording = False
                        has_transcript = False
                        
                        for obj in response.get('Contents', []):
                            key = obj['Key']
                            if key.endswith(('.mp4', '.webm', '.mov')):
                                has_recording = True
                            elif key.endswith('transcript.json'):
                                has_transcript = True
                        
                        if has_recording:
                            recordings_count += 1
                        if has_transcript:
                            transcripts_available += 1
                            
                    except Exception as e:
                        logger.debug(f"Error checking S3 for interview {interview.interview_id}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error counting recordings and transcripts: {e}")
        
        return AnalyticsResponse(
            total_interviews=analytics["total_interviews"],
            average_technical_score=analytics["average_technical_score"],
            average_behavioral_score=analytics["average_behavioral_score"],
            position_breakdown=analytics["position_breakdown"],
            recordings_count=recordings_count,
            transcripts_available=transcripts_available
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

@app.get("/recordings")
async def get_recordings(limit: int = Query(10, ge=1, le=100)):
    """Get list of active recordings"""
    try:
        lk_api = LiveKitAPI()
        egress_list = await lk_api.egress.list_egress(ListEgressRequest())
        await lk_api.aclose()
        
        recordings = []
        for egress in egress_list.items[:limit]:
            recordings.append(RecordingInfo(
                egress_id=egress.egress_id,
                room_name=egress.room_name,
                status=egress.status.name,
                started_at=str(egress.started_at),
                ended_at=str(egress.ended_at) if egress.ended_at else None,
                file_url=None  # Would need to parse from egress info
            ))
        
        return {"recordings": recordings, "total_count": len(recordings)}
        
    except Exception as e:
        logger.error(f"Error getting recordings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recordings")

@app.get("/interview/{interview_id}/transcript")
async def get_interview_transcript(interview_id: str):
    """Get detailed transcript for an interview"""
    try:
        # Check if interview exists
        interview = db.get_interview_session(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Get transcript from S3
        if not s3_client:
            raise HTTPException(status_code=503, detail="S3 service not available")
        
        bucket_name = os.getenv('S3_BUCKET_NAME')
        transcript_key = f"interviews/{interview_id}/transcript.json"
        
        try:
            # Download transcript from S3
            response = s3_client.get_object(Bucket=bucket_name, Key=transcript_key)
            transcript_data = response['Body'].read()
            
            import json
            transcript_json = json.loads(transcript_data)
            
            return {
                "interview_id": interview_id,
                "candidate_name": interview.candidate_name,
                "position": interview.position,
                "transcript": transcript_json
            }
            
        except s3_client.exceptions.NoSuchKey:
            raise HTTPException(status_code=404, detail="Transcript not found")
        except Exception as e:
            logger.error(f"Error downloading transcript: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve transcript")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcript for interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transcript")

@app.get("/interview/{interview_id}/recording")
async def get_interview_recording(interview_id: str):
    """Get recording download URL for an interview"""
    try:
        # Check if interview exists
        interview = db.get_interview_session(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Get recording URL from S3
        recording_url = get_s3_recording_url(interview_id)
        
        if not recording_url:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        return {
            "interview_id": interview_id,
            "candidate_name": interview.candidate_name,
            "recording_url": recording_url,
            "expires_in_seconds": 3600  # 1 hour
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recording for interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recording")

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
    """Delete an interview record and associated files (admin function)"""
    try:
        # Check if interview exists
        interview = db.get_interview_session(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Delete S3 files if S3 is configured
        if s3_client:
            try:
                bucket_name = os.getenv('S3_BUCKET_NAME')
                prefix = f"interviews/{interview_id}/"
                
                # List and delete all objects in the interview folder
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    delete_objects = [{'Key': obj['Key']} for obj in response['Contents']]
                    if delete_objects:
                        s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': delete_objects}
                        )
                        logger.info(f"Deleted {len(delete_objects)} S3 objects for interview {interview_id}")
                
            except Exception as s3_error:
                logger.error(f"Error deleting S3 files for interview {interview_id}: {s3_error}")
        
        return {
            "message": f"Interview {interview_id} and associated files marked for deletion",
            "interview_id": interview_id,
            "candidate_name": interview.candidate_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting interview {interview_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete interview")

@app.get("/health")
async def health_check():
    """Detailed health check endpoint including S3 and recording services"""
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
        
        # Check S3 connection
        s3_status = "healthy"
        if s3_client:
            try:
                bucket_name = os.getenv('S3_BUCKET_NAME')
                if bucket_name:
                    s3_client.head_bucket(Bucket=bucket_name)
                else:
                    s3_status = "no bucket configured"
            except Exception as e:
                s3_status = f"unhealthy: {str(e)}"
        else:
            s3_status = "not configured"
        
        # Check API keys
        api_keys_status = {
            "google_api_key": "present" if os.getenv("GOOGLE_API_KEY") else "missing",
            "deepgram_api_key": "present" if os.getenv("DEEPGRAM_API_KEY") else "missing",
            "cartesia_api_key": "present" if os.getenv("CARTESIA_API_KEY") else "missing",
            "livekit_api_key": "present" if os.getenv("LIVEKIT_API_KEY") else "missing",
            "livekit_api_secret": "present" if os.getenv("LIVEKIT_API_SECRET") else "missing",
            "aws_access_key_id": "present" if os.getenv("AWS_ACCESS_KEY_ID") else "missing",
            "aws_secret_access_key": "present" if os.getenv("AWS_SECRET_ACCESS_KEY") else "missing",
        }
        
        overall_status = "healthy" if all([
            db_status == "healthy",
            lk_status == "healthy",
            s3_status in ["healthy", "not configured"],
            all(status == "present" for status in api_keys_status.values())
        ]) else "degraded"
        
        return {
            "status": overall_status,
            "database": db_status,
            "livekit": lk_status,
            "s3": s3_status,
            "api_keys": api_keys_status,
            "recording_enabled": s3_client is not None,
            "s3_bucket": os.getenv('S3_BUCKET_NAME'),
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