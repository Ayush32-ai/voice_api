# 🚀 Deploy to Vercel - Quick Guide

## ✅ Vercel Configuration Fixed!

Your `vercel.json` has been updated and the conflicting properties have been resolved. You're now ready to deploy!

## 🚀 Deployment Steps

### 1. Go to Vercel
Visit: **https://vercel.com** and sign in with GitHub

### 2. Import Repository
1. Click **"New Project"**
2. Select **"Import Git Repository"**
3. Choose: `https://github.com/Ayush32-ai/voice_api`
4. Click **"Import"**

### 3. Configure Project Settings
Vercel should auto-detect Python. If not:
- **Framework Preset**: Other
- **Root Directory**: `./` (leave empty)
- **Build Command**: (leave empty)
- **Output Directory**: (leave empty)

### 4. Add Environment Variables
Click **"Environment Variables"** and add:

```env
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ELEVENLABS_API_KEY=sk_your_elevenlabs_api_key_here
GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Optional (for production):**
```env
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=redis://user:password@host:6379
```

### 5. Deploy!
Click **"Deploy"** and wait 2-3 minutes.

## 🔑 Get Your Missing API Keys

### Gemini API (Required for Translation)
1. Go to: https://makersuite.google.com/
2. Sign in with Google account
3. Create API key
4. Copy and add to Vercel environment variables

### OpenAI API (Optional)
1. Go to: https://platform.openai.com/
2. Sign in and go to API keys
3. Create new key
4. Copy and add to Vercel environment variables

## 🧪 Test Your Deployment

Once deployed, your API will be at:
**`https://your-project-name.vercel.app`**

### Quick Tests:
```bash
# Health check
curl https://your-project-name.vercel.app/health

# API info  
curl https://your-project-name.vercel.app/api/info

# Interactive docs
open https://your-project-name.vercel.app/docs
```

## 📱 Update Your Kotlin App

Update your mobile app's base URL:
```kotlin
const val API_BASE_URL = "https://your-project-name.vercel.app"
```

## 🗄️ Database Setup (Optional but Recommended)

For production, set up a PostgreSQL database:

### Option 1: Railway (Recommended)
1. Go to: https://railway.app
2. Create new project → Add PostgreSQL
3. Copy connection string to `DATABASE_URL` in Vercel

### Option 2: Neon (Serverless PostgreSQL)
1. Go to: https://neon.tech
2. Create database
3. Copy connection string to `DATABASE_URL` in Vercel

### Option 3: Supabase
1. Go to: https://supabase.com
2. Create project
3. Get connection string from Settings → Database
4. Add to `DATABASE_URL` in Vercel

## ⚡ Performance Notes

### Vercel Limits:
- **Function timeout**: 10 seconds (Hobby), 60 seconds (Pro)
- **File size**: 50MB max upload
- **Memory**: 1024MB max

### For Large Files/Long Processing:
Consider using external services like:
- **CloudConvert** for video processing
- **AWS S3** for file storage
- **Background job queue** for long tasks

## 🎉 Success!

Once deployed, you'll have:
- ✅ **Global API** with auto-scaling
- ✅ **HTTPS** by default
- ✅ **Fast response times** via CDN
- ✅ **Interactive documentation** at `/docs`
- ✅ **Mobile-ready endpoints** for your Kotlin app

## 📞 Common Issues & Solutions

### Build Errors
- Check requirements.txt has correct package versions
- Verify Python version in runtime.txt

### Runtime Errors  
- Check environment variables are set correctly
- Verify API keys have proper permissions
- Check function logs in Vercel dashboard

### Import Errors
- Ensure all required packages are in requirements.txt
- Check Python path configuration

## 🎬 You're Live!

Your **AI Dubbing Studio** is now running on Vercel's global infrastructure, ready to serve your Kotlin mobile app and showcase your backend/AI engineering skills!

**Next: Connect your mobile app and start dubbing videos!** ✨