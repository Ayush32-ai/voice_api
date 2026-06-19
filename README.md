# 🎬 AI Dubbing Studio Backend

An asynchronous AI dubbing pipeline built with FastAPI, AsyncIO, Redis, PostgreSQL and external AI APIs. This backend provides automated video dubbing capabilities with provider abstractions, retry mechanisms, structured logging, caching and fault-tolerant processing for large-scale audio workflows.

## ✨ Features

- 📹 **Video Upload & Processing** - Support for MP4, AVI, MOV, MKV, WebM
- 🎙️ **Audio Extraction** - High-quality audio extraction using FFmpeg
- 📝 **Speech-to-Text** - GROQ Whisper API (faster) and OpenAI Whisper
- 🌐 **Translation** - Google Gemini AI for multilingual translation
- 🔊 **Text-to-Speech** - ElevenLabs premium voice synthesis
- 🎬 **Audio-Video Merging** - Seamless integration of dubbed audio
- 📊 **Real-time Progress Tracking** - WebSocket-like progress updates
- 🔄 **Retry Mechanisms** - Automatic retry with exponential backoff
- 📜 **Structured Logging** - Comprehensive audit trails
- 🗄️ **Caching** - Redis-powered performance optimization
- 🛡️ **Fault Tolerance** - Robust error handling and recovery

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kotlin App    │────│  FastAPI Backend │────│  AI Providers   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ PostgreSQL + DB │    │ GROQ + Gemini + │
                    │     Redis       │    │   ElevenLabs    │
                    └─────────────────┘    └─────────────────┘
```

## 🌍 Supported Languages

- 🇺🇸 **English (en)** - Source and target
- 🇮🇳 **Hindi (hi)** - Source and target  
- 🇮🇳 **Tamil (ta)** - Source and target

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and job queues
- **Docker** - Containerization
- **AsyncIO** - Asynchronous processing
- **Tenacity** - Retry mechanisms

### AI Providers
- **GROQ Whisper** - Fast speech-to-text (primary)
- **OpenAI Whisper** - Speech-to-text (fallback)
- **Google Gemini** - Translation
- **ElevenLabs** - Text-to-speech synthesis

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+**
2. **PostgreSQL 15+**
3. **Redis 7+**
4. **FFmpeg** (for audio/video processing)

### Installation

1. **Clone and setup**
```bash
cd voice_backend
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys (already configured)
```

3. **Start services with Docker**
```bash
docker-compose up -d  # Starts PostgreSQL and Redis
```

4. **Initialize database**
```bash
python -c "from app.database import create_tables; import asyncio; asyncio.run(create_tables())"
```

5. **Start the application**
```bash
# Terminal 1: API Server
python start_server.py

# Terminal 2: Background Worker  
python start_worker.py
```

### API Endpoints

The backend is now running at `http://localhost:8000`

- 📊 **API Docs**: http://localhost:8000/docs
- 🏥 **Health Check**: http://localhost:8000/health
- 📈 **API Info**: http://localhost:8000/api/info

## 📡 API Reference

### Core Endpoints

#### Create Dubbing Job
```http
POST /api/jobs
Content-Type: multipart/form-data

{
  "file": "video.mp4",
  "title": "My Video", 
  "source_language": "en",
  "target_language": "hi"
}
```

#### Get Job Status
```http
GET /api/jobs/{job_id}
```

#### List Jobs
```http
GET /api/jobs?skip=0&limit=10&status=completed
```

#### Download Results
```http
GET /api/download/{job_id}/dubbed     # Final dubbed video
GET /api/download/{job_id}/original   # Original video
GET /api/download/{job_id}/transcript # Speech-to-text result
GET /api/download/{job_id}/translation # Translation result
GET /api/download/{job_id}/dubbed-audio # Audio only
GET /api/download/{job_id}/all        # All download links
```

#### Real-time Progress
```http
GET /api/jobs/{job_id}/progress
```

#### Job Logs
```http
GET /api/jobs/{job_id}/logs?limit=50
```

### Job Status Flow

```
PENDING → PROCESSING → COMPLETED
    ↓         ↓           ↑
CANCELLED  FAILED ────────┘
              ↓
            RETRY
```

### Processing Steps

1. **UPLOADED** - Video file uploaded
2. **AUDIO_EXTRACTED** - Audio extracted from video  
3. **SPEECH_TO_TEXT** - Audio transcribed to text
4. **TRANSLATED** - Text translated to target language
5. **VOICE_GENERATED** - TTS audio generated
6. **AUDIO_MERGED** - Final video with new audio created

## 🔧 Configuration

### API Keys (Already Configured)

The following API keys need to be configured in your `.env` file:

```env
# AI Service Keys - Replace with your actual keys
ELEVENLABS_API_KEY=sk_your_elevenlabs_key_here
GROQ_API_KEY=gsk_your_groq_key_here
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
```

### Processing Settings

```env
CHUNK_SIZE=8192
MAX_WORKERS=4
MAX_FILE_SIZE=104857600  # 100MB
```

## 🐳 Docker Deployment

### Full Stack
```bash
docker-compose up -d
```

This starts:
- ✅ PostgreSQL database 
- ✅ Redis server
- ✅ FastAPI backend
- ✅ Celery worker

### Individual Services
```bash
docker-compose up -d db redis    # Just databases
docker-compose up -d api         # Just API server  
docker-compose up -d worker      # Just background worker
```

## 📊 Monitoring & Health

### Health Endpoints
```http
GET /health                 # Overall system health
GET /api/jobs/{id}/logs     # Job-specific logs
GET /api/jobs/{id}/progress # Real-time progress
```

### Redis Monitoring
```bash
redis-cli monitor  # Watch Redis operations
```

### Database Monitoring  
```sql
-- Active jobs
SELECT status, COUNT(*) FROM dubbing_jobs GROUP BY status;

-- Recent activity
SELECT * FROM job_logs ORDER BY timestamp DESC LIMIT 20;
```

## 🔄 Development Workflow

### Adding New Languages

1. Update `Language` enum in `app/models.py`
2. Add voice mappings in `ElevenLabsProvider`
3. Update language map in `GeminiProvider`
4. Test with new language codes

### Adding New AI Providers

1. Create new provider class inheriting `AIProvider`
2. Implement required `process()` method
3. Add to `AIProviderFactory`
4. Update configuration and tests

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations  
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 🧪 Testing

### API Testing
```bash
# Test job creation
curl -X POST "http://localhost:8000/api/jobs" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_video.mp4" \
  -F "title=Test Job" \
  -F "source_language=en" \
  -F "target_language=hi"

# Check health
curl http://localhost:8000/health
```

### Load Testing
```bash
# Install dependencies for testing
pip install pytest httpx pytest-asyncio

# Run tests  
python -m pytest tests/ -v
```

## 📈 Performance Optimization

### Redis Caching Strategy
- Job metadata cached for 1 hour
- Progress updates cached for 5 minutes
- Logs cached for most recent 100 entries

### Database Optimization
- Indexed on job_id, status, created_at
- Partitioned job_logs by date
- Connection pooling enabled

### File Processing
- Async I/O for all file operations
- Streaming for large video files
- Automatic cleanup of temporary files

## 🛡️ Security Features

- Input validation on all endpoints
- File type verification  
- Size limits enforced
- SQL injection protection
- CORS properly configured
- Rate limiting ready

## 📚 API Documentation

Complete interactive documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐛 Troubleshooting

### Common Issues

1. **FFmpeg not found**
   ```bash
   # Install FFmpeg
   # Windows: Download from https://ffmpeg.org/
   # MacOS: brew install ffmpeg  
   # Linux: sudo apt install ffmpeg
   ```

2. **Redis connection failed**
   ```bash
   # Start Redis
   # Windows: redis-server.exe
   # MacOS: brew services start redis
   # Linux: sudo service redis-server start
   ```

3. **Database connection error**
   ```bash
   # Check PostgreSQL is running
   # Update DATABASE_URL in .env file
   ```

4. **API key errors**
   ```bash
   # Verify API keys in .env file
   # Check API key permissions and credits
   ```

### Logs Location
- Application logs: Console output
- Job logs: Database `job_logs` table  
- Redis logs: Redis server logs
- Worker logs: Celery worker output

## 🚀 Production Deployment

### Environment Variables
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://host:6379
SECRET_KEY=production-secret-key
```

### Docker Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes
```yaml
# Example k8s deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dubbing-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dubbing-api
```

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create GitHub issue
- Check documentation at `/docs`
- Review logs for error details

---

**Built for Sarvam AI - Showcase of backend/AI engineering capabilities** 🚀#   v o i c e _ a p i 
 
 #   v o i c e _ a p i  
 #   v o i c e _ a p i  
 #   v o i c e _ a p i  
 