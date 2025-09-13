# Investment Caching and Manual Refresh System

## Overview

This document describes the new investment data caching system implemented to optimize API usage and improve user experience in the Sports Betting Dashboard application.

## Problem Solved

**Before**: The Available Investments page made 12 API requests to the sports odds API every time a user clicked "Available Investments", leading to:
- Excessive API usage and costs
- Slow page load times
- Loss of data when app was closed/reopened
- No user control over data refresh timing

**After**: Intelligent caching system with manual refresh control that:
- Reduces API calls from 12 per page load to 0 (until manual refresh)
- Persists investment data between sessions
- Gives users control over when to fetch fresh data
- Provides configurable user preferences

## New Features

### 1. Manual Refresh Control
- **Refresh Data Button**: Users manually trigger fresh data fetching
- **Visual Loading States**: Spinning refresh icon and disabled button during refresh
- **Cache Status Indicator**: Shows data freshness (cached vs fresh vs no data)
- **API Call Tracking**: Displays number of API calls made during refresh

### 2. Data Persistence
- **Firebase Integration**: Investment data cached in `users/{userId}/cached_investments`
- **Session Continuity**: Data persists when app is closed and reopened
- **Metadata Tracking**: Cache includes timestamp, API call count, and game statistics

### 3. User Preferences
- **Settings Modal**: Accessible via gear icon on investments page
- **Auto-refresh Toggle**: Choose between auto-refresh on login vs cached data
- **Cache Expiry Configuration**: Set cache validity period (15 min to 24 hours)
- **Real-time Statistics**: View cache status, last refresh time, and API calls saved

### 4. Demo Mode Support
- **Local Testing**: Full functionality without Firebase credentials
- **Realistic Data**: Generated demo games for NBA, NFL, MLB
- **No API Dependencies**: Works offline for development and testing

## Technical Implementation

### Backend APIs

#### Investment Data Endpoint
```http
GET /api/investments?user_id={userId}&refresh={true|false}
```
- `refresh=false`: Returns cached data if available
- `refresh=true`: Fetches fresh data from sports API and updates cache

**Response Format:**
```json
{
  "success": true,
  "investments": [...],
  "cached": false,
  "last_refresh": "2025-01-01T12:00:00Z",
  "api_calls_made": 5,
  "demo_mode": false
}
```

#### User Settings Endpoints
```http
GET /api/user-settings?user_id={userId}
POST /api/user-settings
```

**Settings Structure:**
```json
{
  "auto_refresh_on_login": true,
  "cache_expiry_minutes": 30,
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### Cache Statistics Endpoint
```http
GET /api/investments/stats?user_id={userId}
```

**Stats Response:**
```json
{
  "success": true,
  "has_cache": true,
  "last_refresh": "2025-01-01T12:00:00Z",
  "total_games": 15,
  "api_calls_saved": 12
}
```

### Database Schema

```
users/{userId}/
├── cached_investments/
│   └── latest                    # Latest investment data with metadata
├── settings/
│   └── preferences              # User preference settings
└── bets/                        # User's placed bets (existing)
    └── {betId}
```

### Frontend Components

#### Cache Status Indicator
- **Green Circle**: Data is from cache
- **Blue Circle**: Fresh data just fetched
- **Gray Circle**: No data available

#### Settings Modal
- Auto-refresh on login checkbox
- Cache expiry dropdown (15min, 30min, 1hr, 2hr, 24hr)
- Real-time cache statistics display
- Save button with validation

## Usage Instructions

### For Users

1. **Viewing Investments**:
   - Click "Available Investments" tab
   - Page loads cached data instantly (if available)
   - Check cache status indicator for data freshness

2. **Refreshing Data**:
   - Click "Refresh Data" button to fetch latest odds
   - Button shows loading state during refresh
   - Success message displays API calls made

3. **Configuring Preferences**:
   - Click "Settings" button (gear icon)
   - Toggle auto-refresh on login preference
   - Adjust cache expiry time as needed
   - View cache statistics in settings panel

### For Developers

1. **Environment Setup**:
   ```bash
   # Required environment variables
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_API_KEY=your-api-key
   SPORTS_API_KEY=your-sports-api-key
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   ```

2. **Demo Mode**:
   ```bash
   # For testing without Firebase/API credentials
   # Use demo values in .env file
   FIREBASE_PROJECT_ID=demo-project
   SPORTS_API_KEY=demo_sports_api_key
   ```

3. **Testing**:
   ```bash
   python /tmp/test_investment_caching.py
   ```

## Benefits Achieved

### Performance
- **Reduced API Calls**: From 12 calls per page load to 0
- **Faster Load Times**: Cached data loads instantly
- **Cost Savings**: Significant reduction in API usage costs

### User Experience
- **Offline Capability**: View previously cached data without internet
- **User Control**: Manual refresh puts users in control of when to fetch fresh data
- **Persistent Data**: No data loss when closing/reopening app

### Developer Experience
- **Demo Mode**: Easy local development and testing
- **Extensible Design**: Ready for additional caching features
- **Clean APIs**: RESTful endpoints with consistent responses

## Future Enhancements

### Planned Features
1. **Bot Investment Tracking**: Show which bots have backed specific investments
2. **Cache Expiration Policies**: Automatic cache invalidation based on game start times
3. **Batch Refresh Options**: Refresh specific sports or markets only
4. **Investment History**: Track and display investment data over time
5. **Advanced Filtering**: More sophisticated filtering and sorting options

### Technical Improvements
1. **Background Refresh**: Optional background updates while viewing cached data
2. **Compression**: Compress cached data to reduce storage usage
3. **Partial Updates**: Update only changed games instead of full refresh
4. **Offline Indicators**: Better visual feedback for offline/cached states

## Troubleshooting

### Common Issues
1. **"No data available"**: Click "Refresh Data" to fetch initial data
2. **Settings not saving**: Check Firebase configuration and authentication
3. **Slow refresh**: Verify sports API key and internet connection
4. **JavaScript errors**: Ensure external CDN resources are loading

### Debug Mode
Enable debug logging by setting `setLogLevel('Debug')` in the JavaScript console.

## API Rate Limiting

The new system respects API rate limits by:
- Caching responses to minimize repeated requests
- Providing user control over refresh timing
- Displaying API usage statistics
- Supporting demo mode for development

## Security Considerations

- User data is isolated by Firebase security rules
- API keys are server-side only (not exposed to frontend)
- Demo mode uses no real credentials
- Cache data includes no sensitive information

---

**Implementation Date**: September 2025
**Version**: 1.0.0
**Compatibility**: Requires Firebase Firestore and Sports Odds API
**Last Updated**: 9/13/2025