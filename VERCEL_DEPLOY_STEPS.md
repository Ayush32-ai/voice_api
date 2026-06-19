# 🚀 Vercel Deployment - Step by Step

## ✅ Ready for Deployment!

Your configuration issues are now fixed. Follow these exact steps:

## 📋 Step 1: Get Your API Keys Ready

You'll need these API keys. Get them now:

### 🔑 Required Keys:
1. **GROQ API Key**: You already have this
2. **ElevenLabs API Key**: You already have this
3. **Gemini API Key**: Get from https://makersuite.google.com/
4. **OpenAI API Key**: Get from https://platform.openai.com/ (optional)

### 🔐 Generate Secret Key:
```bash
# Generate a secure secret key (run this command):
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🚀 Step 2: Deploy to Vercel

### 2.1 Go to Vercel
1. Visit: **https://vercel.com**
2. Sign in with GitHub
3. Click **"New Project"**

### 2.2 Import Repository
1. Find: **`Ayush32-ai/voice_api`**
2. Click **"Import"**
3. Keep all default settings
4. **DO NOT CLICK DEPLOY YET**

### 2.3 Add Environment Variables
Before deploying, click **"Environment Variables"** and add these:

**REQUIRED (Add these exactly as shown):**
```
SECRET_KEY=paste_your_generated_secret_key_here
ELEVENLABS_API_KEY=sk_your_elevenlabs_key_here
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
```

**OPTIONAL (for enhanced features):**
```
OPENAI_API_KEY=your_openai_key_here
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=redis://user:password@host:6379
```

### 2.4 Deploy
1. Click **"Deploy"**
2. Wait 2-3 minutes for build to complete

## 🧪 Step 3: Test Your Deployment

Once deployed, you'll get a URL like: **`https://voice-api-xyz.vercel.app`**

### Test Commands:
```bash
# Replace YOUR_URL with your actual Vercel URL

# 1. Health Check
curl https://YOUR_URL.vercel.app/health

# 2. API Info
curl https://YOUR_URL.vercel.app/api/info

# 3. Interactive Docs
open https://YOUR_URL.vercel.app/docs
```

## 📱 Step 4: Update Your Kotlin App

Update your mobile app's configuration:
```kotlin
// Replace with your actual Vercel URL
const val API_BASE_URL = "https://YOUR_PROJECT_NAME.vercel.app"
```

## 🎯 Step 5: Test Job Creation

Use the interactive docs at `/docs` to test:
1. Go to `https://YOUR_URL.vercel.app/docs`
2. Find **POST /api/jobs**
3. Click **"Try it out"**
4. Upload a small video file
5. Set languages (e.g., en → hi)
6. Execute and check response

## 🔧 Troubleshooting

### Build Errors
If build fails, check:
1. All environment variables are set
2. API keys are valid and have credits
3. No typos in environment variable names

### Runtime Errors
If API returns 500 errors:
1. Check Vercel function logs in dashboard
2. Verify API keys have proper permissions
3. Check if services are within rate limits

### Missing Features
Some features need external services:
- **Video Processing**: Limited on serverless
- **Large Files**: Consider external storage
- **Long Processing**: May timeout (5-minute limit)

## 🗄️ Step 6: Optional Database Setup

For production use, add a proper database:

### Option A: Railway (Recommended)
1. Go to https://railway.app
2. Create PostgreSQL database
3. Copy connection string
4. Add as `DATABASE_URL` in Vercel environment variables
5. Redeploy

### Option B: Neon (Serverless PostgreSQL)
1. Go to https://neon.tech
2. Create database
3. Copy connection string
4. Add as `DATABASE_URL` in Vercel
5. Redeploy

## ⚡ Performance Tips

### For Better Performance:
1. **Use PostgreSQL** instead of SQLite
2. **Add Redis** for caching
3. **Enable Vercel Pro** for longer timeouts
4. **Use external storage** for large files

### Current Limits:
- **Function timeout**: 10 seconds (free), 5 minutes (pro)
- **File size**: 50MB max
- **Memory**: 1024MB max
- **Database**: SQLite in /tmp (temporary)

## 🎉 Success Indicators

You'll know it's working when:
- ✅ Health check returns `{"status": "healthy"}`
- ✅ API info shows all features
- ✅ Interactive docs load at `/docs`
- ✅ Job creation returns 201 status
- ✅ No 500 errors in function logs

## 📞 Getting Help

If deployment fails:
1. **Check Vercel logs** in dashboard
2. **Verify environment variables** are correct
3. **Test API keys** independently
4. **Check function timeout** settings

## 🎬 You're Live!

Once deployed successfully, your **AI Dubbing Studio API** is:
- 🌍 **Globally available** via Vercel's CDN
- 📈 **Auto-scaling** based on traffic
- 🔒 **HTTPS by default** with security headers
- 📊 **Monitored** via Vercel analytics
- 📱 **Ready for mobile integration**

**Your backend is now production-ready and showcases advanced AI/backend engineering!** 🚀