# 🚀 Deploy AI Dubbing Studio to Vercel

## 📋 Prerequisites

1. **GitHub Repository**: Code pushed to GitHub
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
3. **API Keys**: Get your AI service API keys ready

## 🔧 Required API Keys

Before deploying, you'll need:

- **ElevenLabs API Key**: Get from [ElevenLabs Console](https://elevenlabs.io/)
- **GROQ API Key**: Get from [GROQ Console](https://console.groq.com/)
- **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/)
- **OpenAI API Key**: Optional, from [OpenAI](https://platform.openai.com/)

## 🚀 Deployment Steps

### 1. Connect GitHub to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "New Project"
3. Import your GitHub repository: `https://github.com/Ayush32-ai/voice_api`
4. Select the repository and click "Import"

### 2. Configure Build Settings

Vercel should automatically detect it's a Python project. If not:

- **Framework Preset**: Other
- **Root Directory**: `./`
- **Build Command**: Leave empty
- **Output Directory**: Leave empty

### 3. Set Environment Variables

In Vercel dashboard, add these environment variables:

```env
DATABASE_URL=postgresql://username:password@host:port/database
REDIS_URL=redis://username:password@host:port
SECRET_KEY=your-super-secret-key-here
ELEVENLABS_API_KEY=sk_your_elevenlabs_key_here
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 4. Database Setup (Required)

#### Option A: Railway PostgreSQL (Recommended)
1. Go to [railway.app](https://railway.app)
2. Create new project → Add PostgreSQL
3. Copy connection string to `DATABASE_URL`

#### Option B: Neon (Serverless PostgreSQL)
1. Go to [neon.tech](https://neon.tech)
2. Create database
3. Copy connection string to `DATABASE_URL`

#### Option C: Supabase
1. Go to [supabase.com](https://supabase.com)
2. Create project
3. Get connection string from Settings → Database

### 5. Redis Setup (Optional)

#### Option A: Upstash Redis
1. Go to [upstash.com](https://upstash.com)
2. Create Redis database
3. Copy connection string to `REDIS_URL`

#### Option B: Skip Redis
- Leave `REDIS_URL` empty or remove it
- App will work without caching

### 6. Deploy

1. Click "Deploy" in Vercel
2. Wait for build to complete
3. Your API will be live at: `https://your-project.vercel.app`

## 🧪 Test Your Deployment

### 1. Health Check
```bash
curl https://your-project.vercel.app/health
```

### 2. API Documentation
Visit: `https://your-project.vercel.app/docs`

### 3. Create Test Job
```bash
curl -X POST "https://your-project.vercel.app/api/jobs" \
  -H "Content-Type: multipart/form-data" \
  -F "title=Test Job" \
  -F "source_language=en" \
  -F "target_language=hi" \
  -F "file=@test_video.mp4"
```

## 📱 Update Mobile App

Update your Kotlin app's base URL:

```kotlin
const val API_BASE_URL = "https://your-project.vercel.app"
```

## ⚠️ Vercel Limitations

### File Processing
- **File Size**: Max 50MB (serverless limit)
- **Processing Time**: Max 5 minutes per request
- **FFmpeg**: Not available (need external service)

### Solutions for Production

1. **Video Processing**: Use CloudConvert API or similar
2. **Large Files**: Implement chunked upload
3. **Long Processing**: Use background jobs with external queue

## 🔧 Advanced Configuration

### Custom Domain
1. Go to Vercel project settings
2. Add custom domain
3. Update DNS records

### Performance Optimization
1. Enable Edge Functions for better performance
2. Configure caching headers
3. Use Vercel Analytics

## 📊 Monitoring

### Vercel Dashboard
- View deployment logs
- Monitor function usage
- Check error rates

### Health Monitoring
```bash
# Set up monitoring
curl -X GET "https://your-project.vercel.app/health"
```

## 🐛 Troubleshooting

### Build Errors
1. Check Vercel build logs
2. Verify requirements.txt
3. Check Python version in runtime.txt

### Runtime Errors
1. Check Function logs in Vercel dashboard
2. Verify environment variables
3. Test database connection

### API Issues
1. Check CORS settings
2. Verify API key permissions
3. Monitor rate limits

## 🎉 Success!

Once deployed, you'll have:

- ✅ **Live API** at your Vercel URL
- ✅ **Interactive Docs** at `/docs`
- ✅ **Auto-scaling** serverless functions
- ✅ **Global CDN** for fast response times
- ✅ **HTTPS** by default

Your AI Dubbing Studio is now ready for production use! 🚀

## 📞 Quick Commands

```bash
# Test deployment
curl https://your-project.vercel.app/health

# View API docs
open https://your-project.vercel.app/docs

# Check API info
curl https://your-project.vercel.app/api/info
```

**Your backend is now live and ready for your Kotlin mobile app!** 🎬✨