# Demo Mode Control Documentation

## Overview

The SI-HQ application includes a comprehensive demo mode system that allows users to explore functionality with mock data. A new configuration option `DISABLE_DEMO_MODE` provides an easy way to force the application into production mode, helping users identify which areas are fully functional without demo data.

## Configuration

### Environment Variable

Add to your `.env` file or environment:

```bash
DISABLE_DEMO_MODE=true
```

**Values:**
- `true` - Disables demo mode, forces production mode
- `false` - Allows demo mode (default behavior)

### Requirements for Disabling Demo Mode

When `DISABLE_DEMO_MODE=true`, the following requirements must be met:

1. **Firebase Dependencies**: Firebase libraries must be available
2. **Valid Credentials**: A real Firebase service account file must exist
3. **No Demo Credentials**: Service account path cannot contain 'demo'
4. **Valid Configuration**: All required Firebase configuration variables must be set

### Error Handling

If demo mode is disabled but requirements aren't met, the application will:
- Log detailed error messages
- Refuse to start
- Provide clear guidance on what's missing

## Usage Examples

### Demo Mode Enabled (Default)
```bash
# .env file
FIREBASE_PROJECT_ID=demo-project
GOOGLE_APPLICATION_CREDENTIALS=./demo_service_account.json
# DISABLE_DEMO_MODE not set or false
```

**Result**: Application runs in demo mode with mock data

### Demo Mode Disabled (Production Only)
```bash
# .env file
DISABLE_DEMO_MODE=true
FIREBASE_PROJECT_ID=your-real-project
GOOGLE_APPLICATION_CREDENTIALS=./real_service_account.json
FIREBASE_API_KEY=your-real-api-key
# ... other real Firebase config
```

**Result**: Application runs in production mode with real data

### Configuration Error
```bash
# .env file
DISABLE_DEMO_MODE=true
GOOGLE_APPLICATION_CREDENTIALS=./demo_service_account.json  # Error: demo credentials
```

**Result**: Application fails to start with clear error message

## API Endpoints

### Check Demo Mode Status
```
GET /api/system/demo-mode
```

**Response:**
```json
{
  "success": true,
  "demo_mode": false,
  "demo_mode_disabled": true,
  "firebase_available": true,
  "database_connected": true,
  "can_disable_demo": true,
  "message": "Production mode enabled (demo disabled)"
}
```

### System Status
The existing `/api/system/status` endpoint now includes demo configuration:

```json
{
  "success": true,
  "system_status": {
    "overall_mode": "production",
    "demo_config": {
      "disable_demo_mode": true,
      "demo_mode_active": false,
      "firebase_available": true,
      "database_connected": true
    },
    "warnings": [
      "Demo mode explicitly DISABLED - using production data only"
    ]
  }
}
```

## UI Indicators

The dashboard system status page shows:

### Production Only Mode
- 🔒 Blue indicator with "Production Only" text
- Information box explaining demo mode is disabled
- Clear warnings about using production data

### Configuration Error
- 🚨 Red indicator with "ERROR: Demo Disabled" text
- Critical warning about configuration mismatch
- Instructions to fix the issue

## Benefits

1. **Clear Production Validation**: Easily identify which features work without demo data
2. **Fail-Fast Configuration**: Prevents accidentally running with incomplete configuration
3. **Transparent Status**: Clear UI indicators show the current mode and configuration
4. **Safe Defaults**: Demo mode remains available unless explicitly disabled

## Migration Guide

### From Demo to Production

1. Set up real Firebase project and credentials
2. Add `DISABLE_DEMO_MODE=true` to environment
3. Test that all required features work
4. Deploy with confidence

### Troubleshooting

**Error: "Cannot disable demo mode without Firebase dependencies"**
- Install Firebase libraries: `pip install firebase-admin`

**Error: "Cannot disable demo mode without valid Firebase credentials"**
- Check `GOOGLE_APPLICATION_CREDENTIALS` path exists
- Verify the file contains valid service account JSON

**Error: "Cannot disable demo mode while using demo credentials"**
- Remove 'demo' from credential file path
- Use real service account file

## Security Notes

- Production mode uses real Firebase connections and API keys
- Ensure proper access controls are in place
- Monitor usage and costs when using real APIs
- Demo mode remains safe for development and testing