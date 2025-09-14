# SI-HQ Quick Production Deployment Guide

## Overview

This guide provides step-by-step instructions to deploy the SI-HQ Sports Investment Platform from demo mode to full production with real data and live betting capabilities.

## Prerequisites

- Python 3.8+
- Firebase project with valid credentials
- Sports data API access (The Odds API, SportRadar, or ESPN)
- Sportsbook API access (DraftKings, FanDuel, etc.) for live betting

## Quick Start (30 minutes to production)

### Step 1: Configure Production Environment (5 minutes)

1. **Copy production configuration template:**
   ```bash
   cp .env.production .env
   ```

2. **Update the `.env` file with your production values:**
   ```bash
   # Critical Production Settings
   DISABLE_DEMO_MODE=true
   FIREBASE_PROJECT_ID=your-real-project-id
   FIREBASE_API_KEY=your-real-api-key
   GOOGLE_APPLICATION_CREDENTIALS=./your_real_service_account.json
   SPORTS_API_KEY=your-sports-api-key
   SECRET_KEY=your-secure-secret-key
   ```

### Step 2: API Setup (10 minutes)

#### The Odds API (Recommended)
1. Sign up at [The Odds API](https://the-odds-api.com/)
2. Get your API key
3. Add to `.env`: `SPORTS_API_KEY=your-odds-api-key`

#### Alternative: SportRadar
1. Sign up at [SportRadar](https://developer.sportradar.com/)
2. Get API access for your sports
3. Add to `.env`: `SPORTS_API_KEY=your-sportradar-key`

#### Firebase Setup
1. Create Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. Generate service account key
3. Download as `production_service_account.json`
4. Update `.env` with project details

### Step 3: Deploy and Validate (5 minutes)

1. **Run production readiness check:**
   ```bash
   python deploy_production.py --check-only
   ```

2. **Install dependencies if needed:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run comprehensive tests:**
   ```bash
   python -m pytest test_sports_api_integration.py -v
   ```

### Step 4: Start Production Server (5 minutes)

1. **Start in production mode:**
   ```bash
   python deploy_production.py
   ```

   Or manually:
   ```bash
   python production.py
   ```

2. **Verify production status:**
   ```bash
   curl http://localhost:5000/api/system/demo-mode
   ```

   Should return:
   ```json
   {
     "success": true,
     "demo_mode": false,
     "demo_mode_disabled": true,
     "firebase_available": true,
     "database_connected": true
   }
   ```

### Step 5: Validate Real Data (5 minutes)

1. **Check investment recommendations use real data:**
   ```bash
   curl http://localhost:5000/api/investments
   ```

   Look for `"real_data": true` in the response.

2. **Verify sports data is live:**
   ```bash
   curl http://localhost:5000/api/system/status
   ```

   Should show sports_api as "production" status.

## Production Deployment Modes

### Level 1: Basic Production (Real Sports Data)
- ✅ Real sports games and odds
- ✅ Production database
- ✅ Live investment recommendations
- ❌ Simulated betting (no real money)

**Use case**: Testing strategies with real data, no financial risk

### Level 2: Full Production (Live Betting)
- ✅ Real sports games and odds
- ✅ Production database
- ✅ Live investment recommendations
- ✅ Real betting execution

**Use case**: Full production with real money betting

## Configuration Options

### Sports Data APIs

#### The Odds API (Most Popular)
```bash
SPORTS_API_KEY=your-odds-api-key
SPORTS_API_PROVIDER=the-odds-api
```
- **Pros**: Comprehensive odds, multiple sportsbooks, good rate limits
- **Cons**: Paid service (~$40/month for basic plan)
- **Sports**: NFL, NBA, MLB, NHL, Soccer, Tennis

#### SportRadar
```bash
SPORTS_API_KEY=your-sportradar-key
SPORTS_API_PROVIDER=sportradar
```
- **Pros**: Official data partner, very reliable
- **Cons**: More expensive, requires approval
- **Sports**: All major sports with detailed stats

#### ESPN (Free Tier)
```bash
# No API key needed for basic data
SPORTS_API_PROVIDER=espn
```
- **Pros**: Free, good for basic game results
- **Cons**: Limited odds data, rate limited
- **Sports**: Most major sports, basic data only

### Sportsbook APIs (Live Betting)

#### DraftKings
```bash
DRAFTKINGS_API_KEY=your-dk-api-key
ENABLE_REAL_BETTING=true
```

#### FanDuel
```bash
FANDUEL_API_KEY=your-fd-api-key
ENABLE_REAL_BETTING=true
```

#### BetMGM
```bash
BETMGM_API_KEY=your-betmgm-api-key
ENABLE_REAL_BETTING=true
```

## Security and Compliance

### Production Security Checklist
- [ ] Secret key is not default value
- [ ] Firebase credentials are valid and not demo
- [ ] API keys are stored securely
- [ ] HTTPS is enabled for production domain
- [ ] CORS origins are properly configured
- [ ] Rate limiting is enabled

### Compliance Considerations
- **Gambling Regulations**: Ensure compliance with local gambling laws
- **API Terms of Service**: Review sportsbook API usage terms
- **Data Protection**: Implement proper user data protection
- **Financial Regulations**: Consider financial services regulations

## Monitoring and Maintenance

### Production Monitoring
1. **API Usage Monitoring:**
   ```bash
   # Check API rate limits and usage
   curl http://localhost:5000/api/system/status
   ```

2. **Error Monitoring:**
   ```bash
   # View error logs
   tail -f logs/post9_errors.log
   ```

3. **Performance Monitoring:**
   ```bash
   # Check system performance
   curl http://localhost:5000/api/system/health
   ```

### Daily Maintenance Tasks
- Monitor API rate limit usage
- Review error logs for issues
- Verify betting performance and risk management
- Update models with new training data

### Weekly Maintenance Tasks
- Review and optimize strategy performance
- Update API keys if rotating
- Backup user data and configurations
- Review compliance with regulations

## Troubleshooting

### Common Issues

#### "Cannot disable demo mode without Firebase dependencies"
```bash
pip install firebase-admin
```

#### "API rate limit exceeded"
- Reduce API call frequency
- Upgrade API plan
- Implement better caching

#### "Invalid Firebase credentials"
- Verify service account file path
- Check Firebase project permissions
- Ensure service account has necessary roles

#### "Sports API returning no data"
- Verify API key is valid
- Check API usage limits
- Review API provider status page

### Debug Mode
Enable debug mode for troubleshooting:
```bash
FLASK_DEBUG=true
LOG_LEVEL=DEBUG
```

## Cost Estimates

### API Costs (Monthly)
- **The Odds API**: $40-200/month depending on usage
- **SportRadar**: $500-2000/month for comprehensive data
- **ESPN**: Free for basic usage
- **Sportsbook APIs**: Usually free but require approval

### Infrastructure Costs
- **Firebase**: $25-100/month depending on usage
- **Server Hosting**: $20-200/month depending on scale
- **SSL Certificates**: Free with Let's Encrypt
- **Monitoring Tools**: $20-100/month optional

### Total Monthly Cost
- **Basic Production**: $85-320/month
- **Full Featured**: $565-2400/month

## Next Steps After Deployment

1. **Monitor Performance**: Track system performance for first week
2. **Optimize Strategies**: Tune betting strategies based on real data
3. **Scale Infrastructure**: Add load balancing and auto-scaling
4. **Enhance Features**: Implement P1-P4 features from project plan
5. **User Testing**: Conduct thorough user acceptance testing

## Support and Documentation

- **Technical Documentation**: See `PRODUCTION_PROJECT_PLAN.md`
- **API Documentation**: Available at `/api/docs` endpoint
- **Architecture Guide**: See `ARCHITECTURE_AND_SYSTEM_DESIGN.md`
- **Demo Mode Guide**: See `DEMO_MODE_CONTROL.md`

## Emergency Contacts

In case of production issues:
1. Check system status: `GET /api/system/status`
2. Review error logs: `logs/post9_errors.log`
3. Enable emergency demo mode: Set `DISABLE_DEMO_MODE=false`
4. Contact API providers for service issues

---

**Remember**: Always test in a staging environment before deploying to production with real money!