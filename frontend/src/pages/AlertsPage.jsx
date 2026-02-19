import React, { useEffect, useState, useCallback } from "react";
import api from "../services/api.js";
import GameBoxscore from '../components/GameBoxscore';
import BetWinCard from '../components/BetWinCard';
import GameLiveCard from '../components/GameLiveCard';
import './AlertsPage.css';

// Constants
const POLL_INTERVAL = 300000; // 5 minutes

function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAlerts = useCallback(() => {
    api.get("/api/alerts/")
      .then((res) => {
        setAlerts(res.data || []);
        setError(null);
      })
      .catch((err) => {
        console.error('Failed to fetch alerts:', err);
        setError('Failed to load alerts. Please try again.');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadAlerts();
    
    // Poll for new alerts every 5 minutes
    const interval = setInterval(loadAlerts, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [loadAlerts]);

  const handleMarkAllRead = useCallback(() => {
    // Optimistic update - clear UI immediately
    setAlerts([]);
    
    // Notify Layout to refresh the badge
    window.dispatchEvent(new Event('alertDismissed'));
    
    // Make API call in background (non-blocking)
    api.post("/api/alerts/mark-all-read")
      .catch((err) => {
        console.error('Failed to mark all as read:', err);
        // Could show error toast here
      });
  }, []);

  const ack = useCallback((id) => {
    // Optimistic update using functional setState to avoid stale closure
    setAlerts(prevAlerts => prevAlerts.filter(alert => alert.id !== id));
    
    // Notify Layout to refresh the badge
    window.dispatchEvent(new Event('alertDismissed'));
    
    // Make API call in background (non-blocking)
    api.post(`/api/alerts/${id}/ack`)
      .catch((err) => {
        console.error(`Failed to acknowledge alert ${id}:`, err);
        // Could show error toast here
      });
  }, []);

  const renderAlert = useCallback((alert) => {
    const category = alert.category?.toLowerCase() || '';
    
    if (category.includes('live')) {
      return <GameLiveCard key={alert.id} gameData={alert} />;
    } else if (category.includes('game') || category.includes('result')) {
      return <GameBoxscore key={alert.id} gameData={alert} />;
    } else if (category.includes('bet') || category.includes('win')) {
      return <BetWinCard key={alert.id} betData={alert} />;
    }
    
    // Fallback for other alert types
    return (
      <div key={alert.id} className="generic-alert">
        <div className="alert-header">
          <span className="severity-badge">{alert.severity}</span>
          <span className="category-badge">{alert.category}</span>
        </div>
        <div className="alert-message">{alert.message}</div>
        <button 
          className="ack-button"
          onClick={() => ack(alert.id)}
          aria-label={`Dismiss ${alert.category} alert`}
        >
          Dismiss
        </button>
      </div>
    );
  }, [ack]);

  if (loading) {
    return (
      <div className="alerts-container">
        <div className="loading" role="status" aria-live="polite">
          Loading alerts...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alerts-container">
        <div className="error-message" role="alert">
          {error}
          <button onClick={loadAlerts} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Defensive: handle null/undefined alerts
  if (!alerts || !Array.isArray(alerts)) {
    return (
      <div className="alerts-container">
        <div className="no-alerts">
          <p>No alert data available.</p>
          <button onClick={loadAlerts} className="retry-button">
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="alerts-container">
      <div className="alerts-header">
        <h1>Alerts</h1>
        {alerts.length > 0 && (
          <button 
            className="mark-all-read-btn" 
            onClick={handleMarkAllRead}
            aria-label="Mark all alerts as read"
          >
            Mark All as Read
          </button>
        )}
      </div>
      {alerts.length === 0 ? (
        <div className="no-alerts">
          <p>No new alerts</p>
        </div>
      ) : (
        <div className="alerts-list" role="list">
          {alerts.map(renderAlert)}
        </div>
      )}
    </div>
  );
}

export default AlertsPage;