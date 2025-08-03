# livekit-test-ai-interview# AI Interview Backend

A sophisticated AI-powered interview system built with LiveKit, FastAPI, and modern AI services. This backend provides real-time voice interviews with advanced features like turn detection, noise reduction, and intelligent conversation flow.

## 🚀 Features

- **Real-time Voice Interviews**: Seamless voice communication using LiveKit
- **Advanced AI Integration**:
  - **LLM**: Google Gemini 1.5 Flash for intelligent conversation
  - **STT**: Deepgram Nova-2 for high-quality speech recognition
  - **TTS**: Cartesia Sonic for natural voice synthesis
- **Smart Audio Processing**:
  - Turn detection with EOT (End of Turn) models
  - Noise reduction and echo cancellation
  - Auto gain control for optimal audio quality
- **Structured Interview Flow**:
  - Introduction → Technical → Behavioral → Closing phases
  - Automatic phase transitions based on conversation progress
  - Real-time scoring and evaluation
- **FastAPI Backend**: Modern, fast API with automatic documentation
- **Database Integration**: SQLite for storing interview data and analytics
- **Analytics Dashboard**: Interview statistics and performance metrics

## 📋 Prerequisites

Before running this application, ensure you have:

1. **Python 3.11+**
2. **API Keys** for:
   - [LiveKit](https://livekit.io/) - For real-time communication
   - [Google AI](https://ai.google.dev/) - For Gemini LLM
   - [Deepgram](https://deepgram.com/) - For speech-to-text
   - [Cartesia](https://cartesia.ai/) - For text-to-speech

## 🛠 Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-interview-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-url.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# AI Service API Keys
GOOGLE_API_KEY=your-google-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key
CARTESIA_API_KEY=your-cartesia-api-key

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Interview Configuration
INTERVIEW_DURATION_MINUTES=30
MAX_CONCURRENT_INTERVIEWS=10
```

### 3. Database Initialization

The database will be automatically created when you first run the application. The SQLite database will store:
- Interview sessions and metadata
- Candidate responses and scores
- Interview analytics and metrics

## 🚀 Running the Application

### Option 1: Direct Python Execution

```bash
# Start the FastAPI server
python server.py

# In another terminal, start the LiveKit agent
python agent.py
```

### Option 2: Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d
```

The API will be available at:
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### Interview Management

```bash
# Generate interview token
POST /interview/token
{
  "candidate_name": "John Doe",
  "position": "Software Engineer",
  "room_name": "optional-custom-room"
}

# Get interview details
GET /interview/{interview_id}

# List recent interviews
GET /interviews?limit=10&position=software_engineer

# Get analytics
GET /analytics?position=data_scientist
```

### System Management

```bash
# Health check
GET /health

# Active rooms
GET /rooms/active
```

## 🎯 Interview Flow

The AI interviewer follows a structured approach:

### 1. **Introduction Phase**
- Welcomes the candidate
- Collects basic information (name, position)
- Sets expectations for the interview

### 2. **Technical Phase**
- Position-specific technical questions
- Problem-solving scenarios
- Skills assessment based on role

### 3. **Behavioral Phase**
- Situational questions
- Team collaboration scenarios
- Cultural fit assessment

### 4. **Closing Phase**
- Wrap-up and next steps
- Candidate questions
- Final impressions

## 🔧 Advanced Configuration

### Audio Processing Settings

The system includes advanced audio processing:

```python
# In config.py
AUDIO_SETTINGS = {
    "sample_rate": 24000,
    "channels": 1,
    "noise_reduction": True,
    "echo_cancellation": True,
    "auto_gain_control": True,
}

TURN_DETECTION_SETTINGS = {
    "detection_threshold": 0.5,
    "min_silence_duration": 0.8,
    "max_silence_duration": 3.0,
    "utterance_end_ms": 1000,
}
```

### Model Configuration

Each AI service can be configured:

```python
# STT (Deepgram) Configuration
STT_CONFIG = {
    "model": "nova-2-conversationalai",
    "language": "en",
    "smart_format": True,
    "noise_reduction": True,
}

# LLM (Gemini) Configuration
LLM_CONFIG = {
    "model": "gemini-1.5-flash",
    "temperature": 0.7,
    "max_output_tokens": 1024,
}

# TTS (Cartesia) Configuration
TTS_CONFIG = {
    "voice": "79a125e8-cd45-4c13-8a67-188112f4dd22",
    "model": "sonic-english",
    "sample_rate": 24000,
    "speed": 1.0,
}
```

## 📊 Analytics and Reporting

The system provides comprehensive analytics:

- **Interview Metrics**: Duration, phase completion, response quality
- **Scoring System**: Technical and behavioral scores (1-5 scale)
- **Position Analytics**: Performance breakdown by job role
- **Trend Analysis**: Interview success rates over time

Access analytics via:
```bash
GET /analytics
GET /analytics?position=software_engineer
```

## 🔐 Security Considerations

- **API Keys**: Store securely and rotate regularly
- **Token Expiration**: LiveKit tokens expire after 2 hours
- **CORS**: Configure properly for production environments
- **Rate Limiting**: Implement for production usage
- **Data Privacy**: Interview data contains sensitive information

## 🐛 Troubleshooting

### Common Issues

1. **Audio Quality Problems**
   - Check microphone permissions
   - Verify network stability
   - Ensure proper audio device selection

2. **API Connection Issues**
   - Validate all API keys in `.env`
   - Check network connectivity
   - Review LiveKit server status

3. **Database Errors**
   - Ensure write permissions for SQLite file
   - Check disk space availability
   - Verify database file path

### Debug Mode

Enable detailed logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or modify in config
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Optimization

### For High-Volume Usage

1. **Database**: Consider PostgreSQL for production
2. **Caching**: Implement Redis for session management
3. **Load Balancing**: Use multiple agent instances
4. **Monitoring**: Add application monitoring (Prometheus/Grafana)

### Audio Optimization

- **Bandwidth**: Optimize for low-bandwidth scenarios
- **Latency**: Configure turn detection for responsiveness
- **Quality**: Balance audio quality with performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the [API documentation](http://localhost:8000/docs)
- Review [LiveKit documentation](https://docs.livekit.io/)
- Create an issue in the repository

---

**Built with ❤️ using LiveKit, FastAPI, and modern AI services**