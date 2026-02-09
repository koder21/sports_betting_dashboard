# Timezone Settings Feature

## Overview

Users can now set their preferred timezone in the **Settings** page, and all times displayed across the frontend will automatically convert to that timezone. This is a **frontend-only feature** - it does not affect any backend data or database records.

## Key Features

### 1. **User Timezone Selection**
- Located in the Settings page (⚙️ Settings in the sidebar)
- Users can select from timezones across multiple regions:
  - **North America**: EST, CST, MST, PST, AKT, HST
  - **Europe**: GMT, CET, EET
  - **Asia Pacific**: IST, CST, JST, AEST
  - **UTC**: UTC

### 2. **Persistent Storage**
- Timezone preference is stored in browser's `localStorage`
- Default timezone: `America/New_York` (EST/EDT)
- Preference persists across browser sessions

### 3. **Automatic Conversion**
All times across the application are converted to the user's selected timezone:
- **Live Scores page**: Game start times
- **AAI Bets page**: Game times and timestamps
- **Bets page**: Game scheduled times and date filtering
- **Last updated timestamps**: All refresh times

### 4. **Display Formats**
The `convertToUserTimezone()` function supports multiple output formats:
- `"short"` - Time only: `"2:00 AM"`
- `"date"` - Date only: `"02/10/2026"`
- `"full"` - Full datetime: `"02/10/2026 2:00:00 AM"`
- `"time-with-tz"` - Time with abbreviation: `"2:00 AM ET"`

## Technical Implementation

### Files Added

#### 1. `frontend/src/services/timezoneService.js`
Core timezone management service with functions:
- `getUserTimezone()` - Get user's selected timezone from localStorage
- `setUserTimezone(tz)` - Save user's timezone preference
- `convertToUserTimezone(datetime, format)` - Convert any datetime to user's timezone
- `getTzAbbreviation(tz)` - Get timezone abbreviation (ET, PT, etc.)
- `getTzDisplayName(tz)` - Get full timezone display name
- `getAvailableTimezones()` - Get all available timezone options

**Implementation Details**:
- Uses `Intl.DateTimeFormat` for timezone conversion (no external dependencies)
- Handles multiple input types: ISO strings, Date objects, timestamps
- Robust error handling for invalid inputs

#### 2. `frontend/src/pages/SettingsPage.jsx`
New settings page with timezone selector
- Dropdown organized by region (optgroup)
- Live preview of current time in selected timezone
- Save button with success feedback
- Information section explaining the feature

### Files Modified

#### 1. `frontend/src/App.jsx`
- Added import for `SettingsPage`
- Added route: `/settings` → `SettingsPage`

#### 2. `frontend/src/components/Layout.jsx`
- Added "⚙️ Settings" link to bottom navigation
- Navigation link highlights active state

#### 3. `frontend/src/pages/LiveScoresPage.jsx`
- Imported `convertToUserTimezone` from timezoneService
- Updated game start time display to use user's timezone
- Updated "Updated at" timestamp to use user's timezone

#### 4. `frontend/src/pages/AAIBetsPage.jsx`
- Imported `convertToUserTimezone` from timezoneService
- Updated recommendation timestamps to use `"full"` format with user's timezone

#### 5. `frontend/src/pages/BetsPage.jsx`
- Imported `convertToUserTimezone` from timezoneService
- Refactored `toPST()` function to use timezone service
- Updated `formatDate()` function to use timezone service
- All bet dates now display in user's selected timezone

## User Experience

### Settings Page Flow
1. User clicks "⚙️ Settings" in sidebar
2. "Display Preferences" section shows timezone selector
3. User selects their timezone from dropdown
4. Preview shows current time in selected timezone with abbreviation
5. User clicks "Save Timezone"
6. Success indicator appears ("✓ Saved")
7. All times across application automatically convert

### No Backend Impact
- User timezone selection is **only stored in browser localStorage**
- Backend data remains unchanged
- Database times continue to be stored in UTC/original format
- No API calls needed for timezone changes

## Timezone Conversion Logic

The conversion uses the browser's `Intl.DateTimeFormat` API with the `timeZone` option:

```javascript
const formatter = new Intl.DateTimeFormat('en-US', {
  timeZone: userTimezone, // e.g., "America/Los_Angeles"
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: true
});

const localizedString = formatter.format(dateObject);
```

This ensures:
- Automatic DST (Daylight Saving Time) handling
- Correct timezone offsets
- No external timezone libraries needed

## Available Timezones

### North America
- Eastern Time (ET): `America/New_York`
- Central Time (CT): `America/Chicago`
- Mountain Time (MT): `America/Denver`
- Pacific Time (PT): `America/Los_Angeles`
- Alaska Time (AKT): `America/Anchorage`
- Hawaii Time (HST): `Pacific/Honolulu`

### Europe
- Greenwich Mean Time (GMT): `Europe/London`
- Central European Time (CET): `Europe/Paris`
- Eastern European Time (EET): `Europe/Athens`

### Asia Pacific
- India Standard Time (IST): `Asia/Kolkata`
- China Standard Time (CST): `Asia/Shanghai`
- Japan Standard Time (JST): `Asia/Tokyo`
- Australian Eastern Time (AEST): `Australia/Sydney`

### UTC
- Coordinated Universal Time: `UTC`

## Storage Details

**Key**: `user_timezone_preference`  
**Location**: Browser's `localStorage`  
**Format**: Timezone string (e.g., `"America/Los_Angeles"`)  
**Default**: `"America/New_York"`  
**Persistence**: Across browser sessions and tabs

## Testing the Feature

1. Navigate to Settings page
2. Select a timezone different from default
3. Click "Save Timezone"
4. Verify "✓ Saved" message appears
5. Go to Live Scores page - times should show in selected timezone
6. Go to AAI Bets page - timestamps should show in selected timezone
7. Go to Bets page - all dates should show in selected timezone
8. Refresh page - timezone preference should persist
9. Try another timezone - times should update automatically

## Future Enhancements

Potential improvements:
- Add timezone display next to all times throughout the app
- Add quick-select timezone buttons (EST, PST, GMT, etc.)
- Add user preference for time format (12-hour vs 24-hour)
- Add option to show both user timezone and UTC
- Display timezone offset from UTC (e.g., "ET (UTC-5)")
