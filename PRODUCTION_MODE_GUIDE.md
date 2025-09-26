# SI-HQ Production Mode Setup Guide

## Overview
This guide explains how to run the SI-HQ sports investing platform in production mode with real data and no fake/demo fallbacks.

## Prerequisites

### 1. Firebase Setup (Required)
```bash
# Ensure you have a valid Firebase project with:
- Firestore Database enabled
- Authentication enabled
- Valid service account credentials
```

### 2. Sports API Setup (Required)
```bash
# Set your sports data API key:
export SPORTS_API_KEY="your_real_api_key_here"

# Supported providers:
- The Odds API (recommended)
- ESPN API
- Custom sports data provider
```

### 3. Environment Configuration
```bash
# Create .env file with production settings:
DISABLE_DEMO_MODE=true
FIREBASE_CREDENTIALS_PATH=/path/to/service-account.json
SPORTS_API_KEY=your_real_api_key
DATABASE_URL=your_firebase_project_url
```

## Production Mode Activation

### Step 1: Disable Demo Mode
```bash
# Set environment variable to force production mode
export DISABLE_DEMO_MODE=true

# Or set in your .env file
echo "DISABLE_DEMO_MODE=true" >> .env
```

### Step 2: Verify Firebase Credentials
```bash
# Test Firebase connection
python -c "
import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate('path/to/service-account.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
print('✅ Firebase connected successfully')
"
```

### Step 3: Verify Sports API
```bash
# Test sports API connection
curl -H "X-API-Key: $SPORTS_API_KEY" \
  "https://api.the-odds-api.com/v4/sports/upcoming/odds"

# Should return real sports data, not demo data
```

## Running in Production Mode

### 1. Start the Application
```bash
cd dashboard
python app.py
```

### 2. Verify Production Mode
Look for these log messages:
```
✅ FIREBASE CONNECTED - Using real database
✅ SPORTS API CONNECTED - Using real data
🚫 DEMO MODE DISABLED - Production only
```

**NOT these demo messages:**
```
⚠️ DEMO MODE - Using fake data
🟡 FIREBASE UNAVAILABLE - Using mock data
```

### 3. Test Real Data Flow

#### A. Authentication Test
1. Go to the application URL
2. Should see authentication gate (no anonymous access)
3. Sign up with real email
4. Verify user appears in Firebase Authentication console

#### B. Strategy Creation Test
```bash
# Test via API
curl -X POST http://localhost:5000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "name": "Production Test Strategy",
    "type": "aggressive",
    "description": "Testing production mode",
    "parameters": {
      "min_confidence": 65
    }
  }'

# Should return: success: true (not "Database not initialized")
```

#### C. Real Recommendations Test
```bash
# Test recommendations endpoint
curl "http://localhost:5000/api/investments?user_id=test_user"

# Verify response contains:
# - real_data: true
# - data_source: 'real'
# - No demo/fake data messages
```

## Production Checklist

### ✅ Required for Production
- [ ] `DISABLE_DEMO_MODE=true` set
- [ ] Valid Firebase credentials configured
- [ ] Sports API key configured and tested
- [ ] Authentication gate blocks anonymous access
- [ ] Real recommendations endpoint returns `real_data: true`
- [ ] Strategy creation works without demo fallbacks
- [ ] No console warnings about demo/fake data

### 🚫 Remove Demo Fallbacks
The following demo fallbacks are automatically disabled in production mode:
- [ ] Demo investor recommendations
- [ ] Fake sports data generation
- [ ] Mock Firebase operations
- [ ] Anonymous user access
- [ ] Demo strategy templates

### 🔍 Validation Commands

#### Check Demo Mode Status
```bash
# Should show "Production Mode" not "Demo Mode"
curl -s http://localhost:5000/api/system/status | grep -i mode
```

#### Verify Real Data Sources
```bash
# Check investments endpoint
curl -s "http://localhost:5000/api/investments?user_id=real_user" | \
  jq '.real_data, .data_source'

# Should return: true, "real"
```

#### Test Strategy Operations
```bash
# Create strategy (should work without Firebase issues)
curl -X POST http://localhost:5000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","name":"Prod Test","type":"basic"}'

# Should return success without "Database not initialized" errors
```

## Troubleshooting

### Issue: "Database not initialized" 
**Solution:** Check Firebase credentials path and permissions
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### Issue: Still seeing demo data
**Solution:** Verify environment variables are loaded
```bash
echo $DISABLE_DEMO_MODE  # Should output "true"
echo $SPORTS_API_KEY     # Should output your real API key
```

### Issue: Authentication not working
**Solution:** Check Firebase Authentication settings
- Ensure Email/Password provider is enabled
- Check Firebase project configuration
- Verify service account has correct permissions

### Issue: No real sports data
**Solution:** Verify sports API integration
```bash
# Test API key directly
curl -H "X-API-Key: $SPORTS_API_KEY" \
  "https://api.the-odds-api.com/v4/sports"
```

## Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.11
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY dashboard/ /app/
WORKDIR /app
ENV DISABLE_DEMO_MODE=true
CMD ["python", "app.py"]
```

### Environment Variables for Deployment
```bash
# Required production environment variables
DISABLE_DEMO_MODE=true
FIREBASE_CREDENTIALS_PATH=/app/credentials/service-account.json
SPORTS_API_KEY=your_real_api_key
DATABASE_URL=https://your-project.firebaseio.com
FLASK_ENV=production
```

## Security Notes

1. **Never commit real API keys** to version control
2. **Use environment variables** for all credentials
3. **Enable Firebase security rules** in production
4. **Use HTTPS** for all production deployments
5. **Set up proper error monitoring** for production issues

## Support

If you encounter issues with production mode:
1. Check the application logs for error messages
2. Verify all environment variables are set correctly
3. Test Firebase and Sports API connections independently
4. Ensure the authentication gate is blocking unauthorized access

**Remember: In production mode, there are no fallbacks to demo data. All features require proper API credentials and database connectivity.**