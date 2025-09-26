# 🏟️ SI-HQ Production Setup Guide

**Complete step-by-step guide to configure SI-HQ for production use**

## 🚀 Quick Setup (10 minutes)

### Step 1: Copy Configuration Template
```bash
cd /path/to/SI-HQ
cp .env.production .env
```

### Step 2: Get Your API Keys

#### 🔥 Firebase Setup (Required)
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing
3. Go to Project Settings → General → Your apps
4. Copy the configuration values:
   - Project ID
   - App ID  
   - API Key
   - Auth Domain
   - Storage Bucket
   - Messaging Sender ID

5. Go to Project Settings → Service Accounts
6. Click "Generate new private key"
7. Download the JSON file
8. Rename it to `production_service_account.json`
9. Place it in your SI-HQ root directory

#### 📊 Sports API Setup (Required)
**Option A: The Odds API (Recommended)**
1. Sign up at [The Odds API](https://the-odds-api.com/)
2. Get your API key from the dashboard
3. Free tier: 500 requests/month
4. Paid plans available for higher limits

**Option B: SportRadar**
1. Sign up at [SportRadar](https://developer.sportradar.com/)
2. Choose your sports packages
3. Get API credentials

### Step 3: Update Your .env File

Open `.env` and replace ALL placeholder values:

```bash
# Critical Production Settings
DISABLE_DEMO_MODE=true
SECRET_KEY=generate-a-strong-secret-key-here

# Firebase Configuration
FIREBASE_PROJECT_ID=your-actual-project-id
FIREBASE_API_KEY=your-actual-api-key
FIREBASE_APP_ID=your-actual-app-id
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-actual-sender-id
GOOGLE_APPLICATION_CREDENTIALS=./production_service_account.json

# Sports API
SPORTS_API_KEY=your-actual-sports-api-key
```

### Step 4: Test Your Configuration
```bash
python deploy_production.py --check-only
```

**Expected output:**
```
🏟️  SI-HQ Production Deployment Script
==================================================
🔍 Checking production requirements...
✅ All production requirements met!

✅ Production readiness check completed!
```

**If you see errors:**
- ❌ Missing or placeholder value → Replace the placeholder in .env
- ❌ Invalid GOOGLE_APPLICATION_CREDENTIALS → Check file path and content

### Step 5: Start Production Server
```bash
cd dashboard
python app.py
```

**Look for these success messages:**
```
✅ FIREBASE CONNECTED - Using real database
✅ SPORTS API CONNECTED - Using real data
🚫 DEMO MODE DISABLED - Production only
```

## 🔧 Detailed Configuration

### Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DISABLE_DEMO_MODE` | ✅ | Must be `true` for production | `true` |
| `SECRET_KEY` | ✅ | Flask secret key (generate unique) | `your-secret-123` |
| `FIREBASE_PROJECT_ID` | ✅ | Your Firebase project ID | `my-sports-app` |
| `FIREBASE_API_KEY` | ✅ | Firebase web API key | `AIza...` |
| `SPORTS_API_KEY` | ✅ | Sports data API key | `abc123...` |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | Path to service account JSON | `./service_account.json` |

### Optional Configuration

```bash
# Optional Sports APIs
ODDS_API_KEY=your-odds-api-key
WEATHER_API_KEY=your-weather-api-key

# Optional Sportsbook APIs (for live betting)
DRAFTKINGS_API_KEY=your-draftkings-api-key
FANDUEL_API_KEY=your-fanduel-api-key
BETMGM_API_KEY=your-betmgm-api-key

# Performance Settings
RATE_LIMIT_PER_HOUR=500
API_TIMEOUT_SECONDS=30
ENABLE_MODEL_CACHING=true
```

## 🔐 Security Best Practices

### 1. Secret Key Generation
```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Firebase Security Rules
Set up proper Firestore security rules:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only authenticated users can read/write
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

### 3. API Key Security
- Store API keys in environment variables only
- Never commit real API keys to git
- Use different keys for development/production
- Enable API key restrictions when possible

## 🚨 Troubleshooting

### Common Issues

#### "Missing .env file"
```bash
cp .env.production .env
```

#### "Invalid Firebase credentials" 
- Check that `production_service_account.json` exists
- Verify the JSON format is correct
- Ensure the service account has proper permissions

#### "Sports API returning no data"
- Verify your API key is active
- Check API usage limits
- Test API key directly with curl:
```bash
curl "https://api.the-odds-api.com/v4/sports/?apiKey=YOUR_KEY"
```

#### "Demo mode still active"
- Ensure `DISABLE_DEMO_MODE=true` (not `false`)
- Restart the application after changing .env
- Check for console warnings about demo/fake data

### Debug Commands

```bash
# Test environment loading
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Demo mode disabled:', os.getenv('DISABLE_DEMO_MODE'))
print('Firebase project:', os.getenv('FIREBASE_PROJECT_ID'))
"

# Test Firebase connection
python -c "
import firebase_admin
from firebase_admin import credentials
cred = credentials.Certificate('./production_service_account.json')
firebase_admin.initialize_app(cred)
print('Firebase connected successfully!')
"
```

## 📊 Monitoring Production

### Health Check Endpoints
```bash
# Check system status
curl http://localhost:5000/api/system/status

# Verify real data usage
curl http://localhost:5000/api/investments
# Should show "real_data": true
```

### Log Monitoring
```bash
# Watch application logs
tail -f dashboard/logs/app.log

# Check for errors
grep -i error dashboard/logs/app.log
```

## 🎯 Next Steps

After successful setup:

1. **Create your first strategy** via the web interface
2. **Set up automated investors** for your strategies  
3. **Monitor performance** through the dashboard
4. **Scale up** with additional API credits as needed

## 🆘 Support

If you encounter issues:

1. **Check the deployment script**: `python deploy_production.py --check-only`
2. **Review logs** for specific error messages
3. **Test API connections** individually
4. **Refer to API provider documentation** for specific errors

---

**🎉 Congratulations! Your SI-HQ platform is ready for production sports investment!**