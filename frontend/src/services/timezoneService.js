/**
 * Timezone service for frontend-only timezone management
 * Users can select their preferred timezone and all times are converted for display
 * Does NOT affect backend/database - purely client-side transformation
 */

const STORAGE_KEY = "user_timezone_preference";
const DEFAULT_TIMEZONE = "America/New_York"; // EST/EDT

// Get all available timezones
export const getAvailableTimezones = () => {
  // Common timezone options grouped by region
  return {
    "North America": [
      { label: "Eastern Time (ET)", value: "America/New_York" },
      { label: "Central Time (CT)", value: "America/Chicago" },
      { label: "Mountain Time (MT)", value: "America/Denver" },
      { label: "Pacific Time (PT)", value: "America/Los_Angeles" },
      { label: "Alaska Time (AKT)", value: "America/Anchorage" },
      { label: "Hawaii Time (HST)", value: "Pacific/Honolulu" },
    ],
    "Central & South America": [
      { label: "São Paulo, Brazil (BRST)", value: "America/Sao_Paulo" },
      { label: "Buenos Aires, Argentina (ART)", value: "America/Argentina/Buenos_Aires" },
      { label: "Lima, Peru (PET)", value: "America/Lima" },
      { label: "Bogotá, Colombia (COT)", value: "America/Bogota" },
      { label: "Mexico City (CST)", value: "America/Mexico_City" },
      { label: "Caracas, Venezuela (VET)", value: "America/Caracas" },
    ],
    Europe: [
      { label: "Greenwich Mean Time (GMT)", value: "Europe/London" },
      { label: "Central European Time (CET)", value: "Europe/Paris" },
      { label: "Eastern European Time (EET)", value: "Europe/Athens" },
      { label: "Irish Standard Time (IST)", value: "Europe/Dublin" },
      { label: "Central European Time (CET)", value: "Europe/Berlin" },
      { label: "Moscow Standard Time (MSK)", value: "Europe/Moscow" },
    ],
    "Asia Pacific": [
      { label: "India Standard Time (IST)", value: "Asia/Kolkata" },
      { label: "China Standard Time (CST)", value: "Asia/Shanghai" },
      { label: "Japan Standard Time (JST)", value: "Asia/Tokyo" },
      { label: "Australian Eastern Time (AEST)", value: "Australia/Sydney" },
      { label: "Bangkok, Thailand (ICT)", value: "Asia/Bangkok" },
      { label: "Singapore (SGT)", value: "Asia/Singapore" },
      { label: "Hong Kong (HKT)", value: "Asia/Hong_Kong" },
      { label: "Dubai, UAE (GST)", value: "Asia/Dubai" },
    ],
    "Middle East & Africa": [
      { label: "Istanbul, Turkey (EET)", value: "Europe/Istanbul" },
      { label: "Cairo, Egypt (EET)", value: "Africa/Cairo" },
      { label: "Johannesburg, South Africa (SAST)", value: "Africa/Johannesburg" },
      { label: "Lagos, Nigeria (WAT)", value: "Africa/Lagos" },
    ],
    UTC: [
      { label: "Coordinated Universal Time (UTC)", value: "UTC" },
    ],
  };
};

// Get user's selected timezone or return default
export const getUserTimezone = () => {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored || DEFAULT_TIMEZONE;
};

// Set user's timezone preference
export const setUserTimezone = (timezone) => {
  localStorage.setItem(STORAGE_KEY, timezone);
};

// Convert a datetime string (ISO format) to user's timezone
// Input: "2026-02-10T03:00:00Z" or Date object
// Output: formatted string like "2:00 AM ET" or "10:00 AM IST"
export const convertToUserTimezone = (datetimeInput, format = "short") => {
  try {
    let date;

    // Handle different input types
    if (!datetimeInput) {
      return "";
    }

    if (typeof datetimeInput === "string") {
      // Handle ISO strings with Z suffix
      date = new Date(datetimeInput);
    } else if (datetimeInput instanceof Date) {
      date = datetimeInput;
    } else {
      return "";
    }

    if (isNaN(date.getTime())) {
      return "";
    }

    const userTz = getUserTimezone();

    // Use Intl API for timezone conversion
    const formatter = new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
      timeZone: userTz,
    });

    const parts = formatter.formatToParts(date);
    const partMap = {};
    parts.forEach((p) => {
      partMap[p.type] = p.value;
    });

    const month = partMap.month;
    const day = partMap.day;
    const year = partMap.year;
    const hour = partMap.hour;
    const minute = partMap.minute;
    const second = partMap.second;
    const period = partMap.dayPeriod;

    if (format === "short") {
      // Return just time: "2:00 AM"
      return `${hour}:${minute} ${period}`;
    } else if (format === "date") {
      // Return date: "02/10/2026"
      return `${month}/${day}/${year}`;
    } else if (format === "full") {
      // Return full datetime: "02/10/2026 2:00:00 AM"
      return `${month}/${day}/${year} ${hour}:${minute}:${second} ${period}`;
    } else if (format === "time-with-tz") {
      // Return time with timezone abbreviation: "2:00 AM ET"
      const tzAbbrev = getTzAbbreviation(userTz, date);
      return `${hour}:${minute} ${period} ${tzAbbrev}`;
    }

    return `${month}/${day}/${year} ${hour}:${minute}`;
  } catch (error) {
    console.error("Error converting timezone:", error);
    return "";
  }
};

// Get timezone abbreviation (EST, EDT, PST, PDT, etc.)
export const getTzAbbreviation = (timezone, date = new Date()) => {
  try {
    const tzFormatter = new Intl.DateTimeFormat("en-US", {
      timeZoneName: "short",
      timeZone: timezone,
    });

    const parts = tzFormatter.formatToParts(date);
    const tzPart = parts.find((p) => p.type === "timeZoneName");

    return tzPart ? tzPart.value : timezone.split("/")[1] || timezone;
  } catch (error) {
    return timezone.split("/")[1] || timezone;
  }
};

// Get timezone display name (for UI purposes)
export const getTzDisplayName = (timezone) => {
  const timezones = getAvailableTimezones();
  for (const region of Object.values(timezones)) {
    const found = region.find((tz) => tz.value === timezone);
    if (found) {
      return found.label;
    }
  }
  return timezone;
};
