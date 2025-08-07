# config.py - Configuration management with S3 and Recording support
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Config:
    """Configuration class for AI Interview Backend with Recording"""
    
    # LiveKit Configuration
    LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
    
    # AI Service API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
    
    # AWS S3 Configuration for Recording Storage
    AWS_ACCESS_KEY_ID = os.getenv("YUPCHA_S3__ACCESS_KEY", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("YUPCHA_S3__SECRET_KEY", "")
    AWS_REGION = os.getenv("YUPCHA_S3__REGION", "us-east-1")
    S3_BUCKET_NAME = os.getenv("YUPCHA_S3__BUCKET_NAME", "")
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # Interview Configuration
    INTERVIEW_DURATION_MINUTES = int(os.getenv("INTERVIEW_DURATION_MINUTES", 30))
    MAX_CONCURRENT_INTERVIEWS = int(os.getenv("MAX_CONCURRENT_INTERVIEWS", 10))
    
    # Recording Configuration
    ENABLE_RECORDING = os.getenv("ENABLE_RECORDING", "true").lower() == "true"
    RECORDING_FORMAT = os.getenv("RECORDING_FORMAT", "mp4")  # mp4, webm
    RECORDING_QUALITY = os.getenv("RECORDING_QUALITY", "high")  # low, medium, high
    SAVE_TRANSCRIPT = os.getenv("SAVE_TRANSCRIPT", "true").lower() == "true"
    
    # Database Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", "ai_interview_db.sqlite")
    
    # Audio Processing Configuration
    AUDIO_SETTINGS = {
        "sample_rate": 24000,
        "channels": 1,
        "noise_reduction": True,
        "echo_cancellation": True,
        "auto_gain_control": True,
    }
    
    # Recording Layout Configuration
    RECORDING_LAYOUT_CONFIG = {
        "speaker-dark": {
            "background_color": "#1a1a1a",
            "participant_border_width": 2,
            "participant_border_color": "#4a90e2"
        },
        "grid": {
            "background_color": "#ffffff",
            "participant_border_width": 1,
            "participant_border_color": "#cccccc"
        }
    }
    
    # Turn Detection Configuration
    TURN_DETECTION_SETTINGS = {
        "detection_threshold": 0.5,
        "min_silence_duration": 0.8,
        "max_silence_duration": 3.0,
        "utterance_end_ms": 1000,
    }
    
    # STT Configuration (Deepgram)
    STT_CONFIG = {
        "model": "nova-2-conversationalai",
        "language": "en",
        "smart_format": True,
        "interim_results": True,
        "noise_reduction": True,
        "profanity_filter": False,
    }
    
    # LLM Configuration (Gemini)
    LLM_CONFIG = {
        "model": "gemini-1.5-flash",
        "temperature": 0.7,
        "max_output_tokens": 1024,
    }
    
    # TTS Configuration (Cartesia)
    TTS_CONFIG = {
        "voice": "79a125e8-cd45-4c13-8a67-188112f4dd22",  # Professional female voice
        "model": "sonic-2",
        "sample_rate": 24000,
        "speed": 1.0,
        "emotion": ["positivity:medium", "curiosity:medium"]
    }
    
    # Recording Egress Configuration
    EGRESS_CONFIG = {
        "layout": "speaker-dark",  # Layout template for recording
        "audio_only": False,       # Set to True for audio-only recordings
        "video_only": False,       # Set to True for video-only recordings
        "file_format": "mp4",      # Output format
        "resolution": {            # Video resolution
            "width": 1920,
            "height": 1080
        },
        "bitrate": {              # Bitrate settings
            "video": 3000000,     # 3 Mbps
            "audio": 128000       # 128 kbps
        }
    }
    
    # S3 Upload Configuration
    S3_CONFIG = {
        "multipart_upload": True,
        "multipart_threshold": 64 * 1024 * 1024,  # 64MB
        "multipart_chunksize": 16 * 1024 * 1024,  # 16MB
        "max_concurrency": 4,
        "use_threads": True
    }
    
    # Transcript Configuration
    TRANSCRIPT_CONFIG = {
        "format": "json",           # json, txt, srt
        "include_timestamps": True,
        "include_speaker_labels": True,
        "include_confidence_scores": True,
        "word_level_timestamps": False
    }
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate that all required configuration is present"""
        missing_configs = []
        warnings = []
        
        required_configs = [
            ("LIVEKIT_URL", cls.LIVEKIT_URL),
            ("LIVEKIT_API_KEY", cls.LIVEKIT_API_KEY),
            ("LIVEKIT_API_SECRET", cls.LIVEKIT_API_SECRET),
            ("GOOGLE_API_KEY", cls.GOOGLE_API_KEY),
            ("DEEPGRAM_API_KEY", cls.DEEPGRAM_API_KEY),
            ("CARTESIA_API_KEY", cls.CARTESIA_API_KEY),
        ]
        
        # S3 configs are required only if recording is enabled
        if cls.ENABLE_RECORDING:
            required_configs.extend([
                ("AWS_ACCESS_KEY_ID", cls.AWS_ACCESS_KEY_ID),
                ("AWS_SECRET_ACCESS_KEY", cls.AWS_SECRET_ACCESS_KEY),
                ("S3_BUCKET_NAME", cls.S3_BUCKET_NAME),
            ])
        else:
            warnings.append("Recording is disabled - S3 configuration not required")
        
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)
        
        # Check optional configs
        if not cls.AWS_REGION:
            warnings.append("AWS_REGION not set, using default: us-east-1")
        
        return {
            "valid": len(missing_configs) == 0,
            "missing_configs": missing_configs,
            "warnings": warnings,
            "config_status": {
                "livekit": bool(cls.LIVEKIT_URL and cls.LIVEKIT_API_KEY and cls.LIVEKIT_API_SECRET),
                "google": bool(cls.GOOGLE_API_KEY),
                "deepgram": bool(cls.DEEPGRAM_API_KEY),
                "cartesia": bool(cls.CARTESIA_API_KEY),
                "s3": bool(cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY and cls.S3_BUCKET_NAME),
                "recording_enabled": cls.ENABLE_RECORDING,
                "transcript_enabled": cls.SAVE_TRANSCRIPT
            }
        }
    
    @classmethod
    def get_s3_path(cls, interview_id: str, file_type: str = "recording") -> str:
        """Generate S3 path for interview files"""
        if file_type == "recording":
            return f"interviews/{interview_id}/recording_{interview_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{cls.RECORDING_FORMAT}"
        elif file_type == "transcript":
            return f"interviews/{interview_id}/transcript.json"
        else:
            return f"interviews/{interview_id}/{file_type}"
    
    @classmethod
    def get_recording_settings(cls) -> Dict[str, Any]:
        """Get recording settings based on quality"""
        base_settings = cls.EGRESS_CONFIG.copy()
        
        if cls.RECORDING_QUALITY == "low":
            base_settings["resolution"] = {"width": 1280, "height": 720}
            base_settings["bitrate"]["video"] = 1500000  # 1.5 Mbps
        elif cls.RECORDING_QUALITY == "medium":
            base_settings["resolution"] = {"width": 1920, "height": 1080}
            base_settings["bitrate"]["video"] = 2500000  # 2.5 Mbps
        else:  # high quality
            base_settings["resolution"] = {"width": 1920, "height": 1080}
            base_settings["bitrate"]["video"] = 4000000  # 4 Mbps
        
        return base_settings

# Export configuration instance
config = Config()

# Validate configuration on import
config_validation = config.validate_config()
if not config_validation["valid"]:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Configuration validation failed: {config_validation}")

from datetime import datetime