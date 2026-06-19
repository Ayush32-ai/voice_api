# 🚂 Deploy to Railway - Complete Guide

## ✅ What's Already Configured

Your project has everything needed for Railway deployment:

| Component | Status | Details |
|-----------|--------|---------|
| `railway.json` | ✅ Configured | Nixpacks builder, health checks, auto-restart |
| `railway_start.py` | ✅ Ready | Production ASGI server with environment config |
| `requirements.txt` | ✅ Updated | All dependencies including new ones |
| `Dockerfile` | ✅ Available | For advanced deployments |
| `runtime.txt` | ✅ Set | Python 3.9+ |

---

## 🚀 Step-by-Step Deployment

### **Step 1: Sign Up for Railway**
1. Go to **https://railway.app**
2. Click **"Start a New Project"**
3. Sign in with **GitHub** (recommended)

### **Step 2: Create New Project & Import Repository**
1. Click **"Create New Project"**
2. Select **"Deploy from GitHub repo"**
3. Click **"Connect GitHub"** if first time
4. Select repository: **`Ayush32-ai/voice_api`**
5. Click **"Import"**

Railway will automatically detect:
- Python runtime (from `runtime.txt`)
- Build command (from `railway.json`)
- Start command: `python railway_start.py`

### **Step 3: Add Environment Variables**
1. In Railway dashboard, click **"Variables"**
2. Add the following environment variables:

```env
# Required API Keys
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ELEVENLABS_API_KEY=sk_your_elevenlabs_api_key_here
GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional: External Database (Railway provides PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=redis://user:password@host:6379
```

**Getting Your API Keys**:
- **ElevenLabs**: https://elevenlabs.io/
- **GROQ**: https://console.groq.com/
- **Google Gemini**: https://makersuite.google.com/
- **OpenAI**: https://platform.openai.com/ (optional)

### **Step 4: (Optional) Add PostgreSQL Database**
For production database instead of SQLite:

1. Click **"+ Add Database"**
2. Select **"PostgreSQL"**
3. Railway automatically adds `DATABASE_URL`
4. No manual configuration needed!

### **Step 5: Deploy**
1. Click **"Deploy"** button
2. Watch the deployment logs in real-time
3. Wait 2-5 minutes for build to complete

---

## 🧪 Verify Deployment

Once deployed, Railway provides a public URL. Test it:

```bash
# Replace YOUR_RAILWAY_URL with your actual URL
curl https://YOUR_RAILWAY_URL/health

curl https://YOUR_RAILWAY_URL/api/info

# Interactive API docs
open https://YOUR_RAILWAY_URL/docs
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "platform": "railway",
  "services": {
    "redis": "unavailable (optional)",
    "database": "configured"
  }
}
```

---

## 📊 Railway vs Vercel

| Feature | Railway | Vercel |
|---------|---------|--------|
| **Best For** | Full-stack, databases, background jobs | Static sites, simple APIs |
| **Databases** | Built-in PostgreSQL, MongoDB | External only |
| **Background Jobs** | ✅ Yes (workers) | ❌ No (functions timeout at 30s) |
| **Cron Jobs** | ✅ Yes | ❌ No |
| **Unlimited Execution Time** | ✅ Yes | ❌ Limited to 30-60s |
| **Cost** | Free tier (5GB storage) | Free tier limited |
| **Python Support** | Excellent | Good |

**Railway is BETTER for your AI Dubbing API** because:
- Long-running video processing (30+ seconds)
- Optional database & Redis
- Better for background workers
- Easier Python support

---

## 🔧 Railway Dashboard Features

Once deployed, you can:

1. **View Live Logs**
   - Click "Logs" tab
   - See real-time application output

2. **Manage Environment Variables**
   - Click "Variables"
   - Update API keys anytime

3. **Monitor Performance**
   - CPU/Memory usage
   - Request counts
   - Response times

4. **Redeploy**
   - Push changes to GitHub
   - Railway auto-redeploys
   - Or click "Redeploy"

5. **Custom Domain**
   - Go to "Settings"
   - Add custom domain
   - Example: `api.mydubbing.com`

---

## 📱 Update Your Kotlin App

Once Railway deployment is live, update your Kotlin app:

```kotlin
// Replace with your Railway URL
private const val BASE_URL = "https://your-railway-app.up.railway.app/"

// Or with custom domain
private const val BASE_URL = "https://api.mydubbing.com/"
```

---

## 🆘 Troubleshooting

### **Build Fails - "ModuleNotFoundError"**
- Check `requirements.txt` has all dependencies
- Railway shows build logs - check error message

### **App Crashes After Deploy**
- Click "Logs" tab in Railway
- Check error messages
- Verify all environment variables are set

### **Health Check Fails**
- Verify `/health` endpoint responds
- Check API is running: `GET /api/info`

### **Need More Resources**
- Click "Settings"
- Upgrade to paid tier for more CPU/Memory

---

## ✅ Deployment Checklist

- [x] Code pushed to GitHub
- [x] `railway.json` configured
- [x] `requirements.txt` updated
- [x] `railway_start.py` ready
- [ ] Sign up at Railway.app
- [ ] Connect GitHub account
- [ ] Import `Ayush32-ai/voice_api` repository
- [ ] Add environment variables
- [ ] Click Deploy
- [ ] Get Railway URL from dashboard
- [ ] Test `/health` endpoint
- [ ] Update Kotlin app base URL
- [ ] Deploy Kotlin app with new URL

---

## 🚀 Expected Deployment Flow

```
GitHub Repository
        ↓
    Railway detects push
        ↓
    Builds Docker image
        ↓
    Installs Python dependencies
        ↓
    Runs: python railway_start.py
        ↓
    Uvicorn starts on PORT 8000
        ↓
    Railway assigns public URL
        ↓
    ✅ API Live & Ready!
```

---

## 📞 Need Help?

- **Railway Docs**: https://docs.railway.app/
- **Railway Community**: https://discord.gg/railway
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Python on Railway**: https://docs.railway.app/reference/languages-frameworks/python

---

## 💡 Pro Tips

1. **Auto-Deploy on GitHub Push**
   - Railway automatically redeploys when you push to main
   - No manual redeployment needed!

2. **Use Railway CLI for Local Testing**
   ```bash
   npm install -g @railway/cli
   railway login
   railway run python railway_start.py
   ```

3. **Monitor in Real-Time**
   - Keep Railway dashboard open during deployment
   - Check logs as they appear live

4. **Database Backups**
   - If using Railway PostgreSQL
   - Go to "Database" tab
   - Configure automatic backups

---

**Your API is ready to go! Deploy now and make it live! 🚀**
