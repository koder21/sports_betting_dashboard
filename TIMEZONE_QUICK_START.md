# Quick Start: Timezone Settings

## How to Use

### Set Your Timezone

1. **Click "⚙️ Settings"** in the sidebar (bottom navigation)
2. **Select your timezone** from the dropdown
   - Organized by region (North America, Europe, Asia Pacific, UTC)
   - Live preview shows current time in your selection
3. **Click "Save Timezone"**
4. **Success!** You'll see a "✓ Saved" confirmation

### Times Now Convert Automatically

Once set, all times across the site will show in your selected timezone:

| Page | What Converts |
|------|---|
| **Live Scores** | Game start times, "Updated at" timestamp |
| **AAI Bets** | Game recommendation times |
| **Bets** | Game scheduled times, date filtering |
| **All Pages** | Future timestamps |

### Example Conversions

**If you select Pacific Time (PT):**
- Game at 5:00 PM ET displays as: `2:00 PM PT`
- Live update timestamp shows: `2:47 PM PT`

**If you select Japan Standard Time (JST):**
- Game at 5:00 PM ET displays as: `7:00 AM JST` (next day)
- Timestamps automatically convert with full date

---

## Timezone Options

### North America (Most Common)
- **Eastern (ET)**: `America/New_York` - Default
- **Central (CT)**: `America/Chicago`
- **Mountain (MT)**: `America/Denver`
- **Pacific (PT)**: `America/Los_Angeles`
- **Alaska (AKT)**: `America/Anchorage`
- **Hawaii (HST)**: `Pacific/Honolulu`

### Europe
- **GMT**: `Europe/London`
- **CET**: `Europe/Paris`
- **EET**: `Europe/Athens`

### Asia Pacific
- **IST**: `Asia/Kolkata` (India)
- **CST**: `Asia/Shanghai` (China)
- **JST**: `Asia/Tokyo` (Japan)
- **AEST**: `Australia/Sydney` (Australia)

### Coordinated Universal Time
- **UTC**: `UTC`

---

## Important Notes

✅ **Your Setting is Private**
- Stored only in your browser
- Other users see their own timezone
- No data shared with server

✅ **No Database Changes**
- Backend data stays in UTC
- This is frontend-only conversion
- Everyone sees the same actual game times, just in different timezones

✅ **Automatic DST Handling**
- Daylight Saving Time is automatically applied
- No manual adjustment needed in spring/fall

✅ **Persistent Across Sessions**
- Your timezone choice is remembered
- Works even if you close/reopen browser
- Syncs across tabs on same device

---

## Troubleshooting

### Times Not Converting?
1. Go to Settings page
2. Check your timezone is selected correctly
3. Refresh the page
4. Clear browser cache if still not working

### Timezone Not Saving?
- Check that browser allows localStorage (local storage not disabled)
- Check browser privacy settings
- Try a different timezone to test

### Wrong Time Showing?
- Verify your selected timezone matches your location
- Check system timezone on your device
- Remember: Shows time in YOUR timezone, not UTC

---

## Browser Support

Works in all modern browsers:
- ✅ Chrome/Edge (all versions)
- ✅ Firefox (all versions)
- ✅ Safari (iOS 11+)
- ✅ Mobile browsers

---

## Questions?

The Settings page includes detailed information about:
- How the feature works
- What it affects
- How it's stored

See the information section at the bottom of the Settings page for more details.
