# config.py - Configuration management
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Config:
    """Configuration class for AI Interview Backend"""
    
    # LiveKit Configuration
    LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
    
    # AI Service API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # Interview Configuration
    INTERVIEW_DURATION_MINUTES = int(os.getenv("INTERVIEW_DURATION_MINUTES", 30))
    MAX_CONCURRENT_INTERVIEWS = int(os.getenv("MAX_CONCURRENT_INTERVIEWS", 10))
    
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
        "model": "sonic-english",
        "sample_rate": 24000,
        "speed": 1.0,
        "emotion": ["positivity:medium", "curiosity:medium"]
    }
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate that all required configuration is present"""
        missing_configs = []
        
        required_configs = [
            ("LIVEKIT_URL", cls.LIVEKIT_URL),
            ("LIVEKIT_API_KEY", cls.LIVEKIT_API_KEY),
            ("LIVEKIT_API_SECRET", cls.LIVEKIT_API_SECRET),
            ("GOOGLE_API_KEY", cls.GOOGLE_API_KEY),
            ("DEEPGRAM_API_KEY", cls.DEEPGRAM_API_KEY),
            ("CARTESIA_API_KEY", cls.CARTESIA_API_KEY),
        ]
        
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)
        
        return {
            "valid": len(missing_configs) == 0,
            "missing_configs": missing_configs,
            "config_status": {
                "livekit": bool(cls.LIVEKIT_URL and cls.LIVEKIT_API_KEY and cls.LIVEKIT_API_SECRET),
                "google": bool(cls.GOOGLE_API_KEY),
                "deepgram": bool(cls.DEEPGRAM_API_KEY),
                "cartesia": bool(cls.CARTESIA_API_KEY),
            }
        }

# Export configuration instance
config = Config()