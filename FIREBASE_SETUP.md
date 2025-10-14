# Firebase Setup Guide

## Issue: "Missing or insufficient permissions" Errors

If you see errors like:
```
Error fetching investors: FirebaseError: Missing or insufficient permissions.
Error fetching strategies: FirebaseError: Missing or insufficient permissions.
```

This means your Firebase Firestore security rules are not configured to allow authenticated users to access their data.

## Solution: Deploy Firestore Security Rules

### Option 1: Using Firebase Console (Easiest)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Click on **Firestore Database** in the left sidebar
4. Click on the **Rules** tab
5. Replace the existing rules with the content from `firestore.rules` file in this repository
6. Click **Publish** to deploy the rules

### Option 2: Using Firebase CLI

1. Install Firebase CLI if you haven't already:
   ```bash
   npm install -g firebase-tools
   ```

2. Login to Firebase:
   ```bash
   firebase login
   ```

3. Initialize Firebase in your project (if not already done):
   ```bash
   firebase init firestore
   ```
   - Select your Firebase project
   - Use `firestore.rules` as the rules file

4. Deploy the security rules:
   ```bash
   firebase deploy --only firestore:rules
   ```

## Understanding the Security Rules

The provided `firestore.rules` file contains two rule options:

### Option 1: User-Scoped Access (Recommended for Production)
```javascript
match /users/{userId}/{document=**} {
  allow read, write: if request.auth != null && request.auth.uid == userId;
}
```
This rule ensures that:
- Only authenticated users can access data
- Users can only access their own data (data under `/users/{their-uid}/`)
- Provides better security and data isolation

### Option 2: Simple Authenticated Access (Development/Demo)
```javascript
match /{document=**} {
  allow read, write: if request.auth != null;
}
```
This rule allows:
- Any authenticated user (including anonymous) to read/write all data
- Simpler setup for development and testing
- Less secure - only use for development/demo environments

**To use Option 2**: Uncomment the second rule set in `firestore.rules` and comment out Option 1.

## What the App Does When Permissions Are Denied

The SI-HQ application now includes graceful fallback behavior:

1. **Automatic Demo Mode**: If Firebase permissions are denied, the app automatically switches to demo mode
2. **Clear Messaging**: Users see a friendly message: "Firebase permissions not configured. Loading demo data instead."
3. **No Disruption**: The app continues to work with demo data while you configure Firebase

## Testing Your Setup

After deploying the security rules:

1. Refresh your application
2. Sign in (or allow anonymous authentication)
3. You should no longer see permission errors
4. Your data should load from Firebase instead of demo mode

## Common Issues

### Issue: Rules deployed but still getting errors
**Solution**: 
- Wait 1-2 minutes for rules to propagate
- Clear browser cache and refresh
- Check Firebase Console → Firestore Database → Rules tab to verify deployment

### Issue: Anonymous authentication not enabled
**Solution**:
1. Go to Firebase Console → Authentication
2. Click on "Sign-in method" tab
3. Enable "Anonymous" authentication provider

### Issue: Firebase web API key restrictions
**Solution**:
- Ensure your Firebase API key has proper application restrictions configured
- Check Firebase Console → Project Settings → API Keys

## Need Help?

If you continue to experience issues:
1. Check the browser console for detailed error messages
2. Review Firebase Console → Firestore Database → Usage tab for access attempts
3. Verify your Firebase configuration in `.env` file matches your Firebase project
4. Ensure `DISABLE_DEMO_MODE` is not set to `true` if you want fallback behavior

## Related Documentation

- [PRODUCTION_SETUP_GUIDE.md](PRODUCTION_SETUP_GUIDE.md) - Complete production setup
- [PRODUCTION_MODE_GUIDE.md](PRODUCTION_MODE_GUIDE.md) - Production mode configuration
- [Firebase Security Rules Documentation](https://firebase.google.com/docs/firestore/security/get-started)
