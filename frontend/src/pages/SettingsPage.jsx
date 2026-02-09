import React, { useState, useEffect } from "react";
import {
  getUserTimezone,
  setUserTimezone,
  getAvailableTimezones,
  getTzDisplayName,
  convertToUserTimezone,
} from "../services/timezoneService";
import {
  getOddsFormat,
  setOddsFormat,
  getOddsFormatLabel,
} from "../services/oddsService";

function SettingsPage() {
  const [currentTimezone, setCurrentTimezone] = useState(getUserTimezone());
  const [currentOddsFormat, setCurrentOddsFormat] = useState(getOddsFormat());
  const [saved, setSaved] = useState(false);
  const [timezoneGroups, setTimezoneGroups] = useState({});

  useEffect(() => {
    setTimezoneGroups(getAvailableTimezones());
  }, []);

  const handleTimezoneChange = (e) => {
    const newTz = e.target.value;
    setCurrentTimezone(newTz);
    setSaved(false);
  };

  const handleOddsFormatChange = (e) => {
    const newFormat = e.target.value;
    setCurrentOddsFormat(newFormat);
    setSaved(false);
  };

  const handleSave = () => {
    setUserTimezone(currentTimezone);
    setOddsFormat(currentOddsFormat);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const getPreviewTime = () => {
    const now = new Date();
    return convertToUserTimezone(now, "time-with-tz");
  };

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <div className="settings-container">
        <div className="settings-section">
          <h2>Display Preferences</h2>

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
              <div className="preview-time">{getPreviewTime()}</div>
            </div>

            <button onClick={handleSave} className="save-button">
              {saved ? "✓ Saved" : "Save Timezone"}
            </button>
          </div>

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

            <button onClick={handleSave} className="save-button">
              {saved ? "✓ Saved" : "Save Settings"}
            </button>
          </div>
        </div>

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

      <style>{`
        .settings-page {
          padding: 30px;
          max-width: 900px;
          margin: 0 auto;
        }

        .settings-page h1 {
          font-size: 2rem;
          margin-bottom: 30px;
          color: #1f2937;
        }

        .settings-container {
          display: grid;
          gap: 30px;
        }

        .settings-section {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 25px;
        }

        .settings-section h2 {
          font-size: 1.3rem;
          margin-bottom: 20px;
          color: #374151;
          border-bottom: 2px solid #e5e7eb;
          padding-bottom: 10px;
        }

        .setting-item {
          margin-bottom: 20px;
        }

        .setting-item label {
          display: block;
          margin-bottom: 15px;
        }

        .setting-item strong {
          font-size: 1.1rem;
          color: #1f2937;
          display: block;
          margin-bottom: 8px;
        }

        .setting-description {
          font-size: 0.95rem;
          color: #6b7280;
          margin: 0;
          line-height: 1.5;
        }

        .timezone-selector {
          margin: 20px 0;
        }

        .timezone-dropdown {
          width: 100%;
          max-width: 400px;
          padding: 12px;
          font-size: 1rem;
          border: 2px solid #d1d5db;
          border-radius: 6px;
          background: white;
          color: #1f2937;
          cursor: pointer;
          transition: border-color 0.2s ease;
        }

        .timezone-dropdown:hover {
          border-color: #9ca3af;
        }

        .timezone-dropdown:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .preview-section {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          padding: 15px;
          margin: 20px 0;
        }

        .preview-label {
          font-size: 0.9rem;
          color: #6b7280;
          margin-bottom: 8px;
          font-weight: 500;
        }

        .preview-time {
          font-size: 1.3rem;
          font-weight: 600;
          color: #3b82f6;
          font-family: "Monaco", "Courier New", monospace;
        }

        .save-button {
          background: #3b82f6;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 6px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s ease, transform 0.1s ease;
          margin-top: 15px;
        }

        .save-button:hover {
          background: #2563eb;
          transform: translateY(-1px);
        }

        .save-button:active {
          transform: translateY(0);
        }

        .info-section {
          background: #eff6ff;
          border-color: #bfdbfe;
        }

        .info-section h2 {
          border-bottom-color: #bfdbfe;
        }

        .info-content {
          color: #1e40af;
          line-height: 1.7;
        }

        .info-content p {
          margin: 12px 0;
        }

        .info-content strong {
          color: #1e3a8a;
        }

        .info-content ul {
          margin: 12px 0 12px 20px;
          padding: 0;
        }

        .info-content li {
          margin: 6px 0;
        }

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
          .settings-page {
            background: #0a0a0a;
            color: #e0e0e0;
          }

          .settings-page h1 {
            color: #ffffff;
          }

          .settings-container {
            background: #121212;
          }

          .settings-section {
            background: #1e1e1e;
            border-color: #333;
          }

          .settings-section h2 {
            color: #ffffff;
            border-bottom-color: #333;
          }

          .setting-item strong {
            color: #ffffff;
          }

          .setting-description {
            color: #9ca3af;
          }

          .timezone-dropdown,
          .odds-dropdown {
            background: #2a2a2a;
            color: #e0e0e0;
            border-color: #444;
          }

          .timezone-dropdown:hover,
          .odds-dropdown:hover {
            border-color: #555;
          }

          .timezone-dropdown:focus,
          .odds-dropdown:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          }

          .preview-section {
            background: #2a2a2a;
            border-color: #444;
          }

          .preview-label {
            color: #9ca3af;
          }

          .preview-time {
            color: #60a5fa;
          }

          .preview-example {
            color: #e0e0e0;
          }

          .save-button {
            background: #3b82f6;
          }

          .save-button:hover {
            background: #2563eb;
          }

          .info-section {
            background: #1a2332;
            border-color: #2a3f5f;
          }

          .info-section h2 {
            border-bottom-color: #2a3f5f;
          }

          .info-content {
            color: #93c5fd;
          }

          .info-content strong {
            color: #bfdbfe;
          }
        }

        @media (max-width: 768px) {
          .settings-page {
            padding: 20px;
          }

          .settings-page h1 {
            font-size: 1.5rem;
            margin-bottom: 20px;
          }

          .timezone-dropdown {
            max-width: 100%;
          }

          .settings-section {
            padding: 20px;
          }
        }
      `}</style>
    </div>
  );
}

export default SettingsPage;
