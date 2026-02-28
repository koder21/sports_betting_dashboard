import React, { useState, useEffect, useMemo, useCallback } from "react";
import ErrorBoundary from '../components/ErrorBoundary.jsx';
import AnalyticsService from '../services/analytics.js';
import SuspenseFallback from '../components/SuspenseFallback.jsx';
import {
  getUserTimezone,
  setUserTimezone,
  getAvailableTimezones,
  convertToUserTimezone,
} from "../services/timezoneService";
import {
  getOddsFormat,
  setOddsFormat,
} from "../services/oddsService";
import "./SettingsPage.css";

// Constants
const SAVE_SUCCESS_DURATION = 3000; // 3 seconds

function SettingsPage() {
  const [currentTimezone, setCurrentTimezone] = useState(getUserTimezone());
  const [currentOddsFormat, setCurrentOddsFormat] = useState(getOddsFormat());
  const [saved, setSaved] = useState(false);

  // Memoize timezone groups (expensive operation, only calculate once)
  const timezoneGroups = useMemo(() => getAvailableTimezones(), []);

  // Track page view
  useEffect(() => {
    AnalyticsService.trackPageView('SettingsPage');
  }, []);

  // Preview time, updates when timezone changes
  const [previewTime, setPreviewTime] = useState(() =>
    convertToUserTimezone(new Date(), "time-with-tz")
  );

  useEffect(() => {
    setPreviewTime(convertToUserTimezone(new Date(), "time-with-tz"));
  }, [currentTimezone]);

  const handleTimezoneChange = useCallback((e) => {
    const newTz = e.target.value;
    setCurrentTimezone(newTz);
    setSaved(false);
  }, []);

  const handleOddsFormatChange = useCallback((e) => {
    const newFormat = e.target.value;
    setCurrentOddsFormat(newFormat);
    setSaved(false);
  }, []);

  const handleSave = useCallback(() => {
    setUserTimezone(currentTimezone);
    setOddsFormat(currentOddsFormat);
    setSaved(true);
    const timer = setTimeout(() => setSaved(false), SAVE_SUCCESS_DURATION);
    return () => clearTimeout(timer);
  }, [currentTimezone, currentOddsFormat]);

  return (
  <div className="settings-page">
    <h1>Settings</h1>

    <div className="settings-container">
      <div className="settings-section">
        <h2>Display Preferences</h2>

        {/* Timezone Setting */}
        <div className="setting-item">
          <label htmlFor="timezone-select">
            <strong>Timezone</strong>
            <p className="setting-description">
              Select your timezone. All times displayed on the site will be
              converted to this timezone. This setting only affects your
              display—it does not change any data in the database.
            </p>
          </label>
          <div className="timezone-selector">
            <select
              id="timezone-select"
              value={currentTimezone}
              onChange={handleTimezoneChange}
              className="timezone-dropdown"
              aria-label="Select your timezone"
            >
              {Object.entries(timezoneGroups).map(([region, tzs]) => (
                <optgroup label={region} key={region}>
                  {tzs.map((tz) => (
                    <option key={tz.value} value={tz.value}>
                      {tz.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          <div className="preview-section">
            <div className="preview-label">Preview (Current time):</div>
            <div className="preview-time">{previewTime}</div>
          </div>

          <button 
            onClick={handleSave} 
            className="save-button"
            aria-label={saved ? "Settings saved" : "Save timezone settings"}
          >
            {saved ? "✓ Saved" : "Save Timezone"}
          </button>
        </div>

        {/* Odds Format Setting */}
        <div className="setting-item">
          <label htmlFor="odds-format-select">
            <strong>Odds Format</strong>
            <p className="setting-description">
              Choose how odds are displayed across the site. This setting only
              affects your display—all data in the database remains in American
              format.
            </p>
          </label>

          <div className="odds-format-selector">
            <select
              id="odds-format-select"
              value={currentOddsFormat}
              onChange={handleOddsFormatChange}
              className="odds-dropdown"
              aria-label="Select odds format"
            >
              <option value="american">American (-110, +200)</option>
              <option value="decimal">Decimal (1.91, 3.0)</option>
            </select>
          </div>

          <div className="preview-section">
            <div className="preview-label">Example conversions:</div>
            <div className="preview-example">
              -110 American = 1.909 Decimal<br/>
              +200 American = 3.0 Decimal
            </div>
          </div>

          <button 
            onClick={handleSave} 
            className="save-button"
            aria-label={saved ? "Settings saved" : "Save settings"}
          >
            {saved ? "✓ Saved" : "Save Settings"}
          </button>
        </div>
      </div>

      {/* Info Section */}
      <div className="settings-section info-section">
        <h2>About Display Settings</h2>
        <div className="info-content">
          <p>
            <strong>Frontend-Only:</strong> All display preferences are applied
            only in your browser. Your backend data and database are not affected.
          </p>
          <p>
            <strong>Auto-Apply:</strong> Once set, your preferences are
            automatically applied to all times displayed across the site:
          </p>
          <ul>
            <li>Live Scores page (game start times)</li>
            <li>AAI Bets page (game times and betting data)</li>
            <li>Analytics pages (all timestamps)</li>
            <li>Alerts and notifications</li>
          </ul>
          <p>
            <strong>Storage:</strong> Your timezone preference is saved in
            your browser's local storage and persists across sessions.
          </p>
        </div>
      </div>
    </div>
  </div>
  );
}

export default function SettingsPageWrapper(props) {
  return (
    <ErrorBoundary>
      <React.Suspense fallback={<SuspenseFallback message="Loading settings..." />}>
        <SettingsPage {...props} />
      </React.Suspense>
    </ErrorBoundary>
  );
}