import React, { useEffect, useState } from "react";
import api from "../services/api.js";
import GameBoxscore from '../components/GameBoxscore';
import BetWinCard from '../components/BetWinCard';
import GameLiveCard from '../components/GameLiveCard';
import './AlertsPage.css';

function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAlerts = () => {
    api.get("/alerts/")
      .then((res) => setAlerts(res.data || []))
      .catch((err) => console.error('Failed to fetch alerts:', err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAlerts();
    // Poll for new alerts every 5 minutes
    const interval = setInterval(loadAlerts, 300000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkAllRead = () => {
    api.post("/alerts/mark-all-read")
      .then(() => {
        setAlerts([]);
        // Notify Layout to refresh the badge
        window.dispatchEvent(new Event('alertDismissed'));
      })
      .catch((err) => console.error('Failed to mark all as read:', err));
  };

  const ack = (id) => {
    api.post(`/alerts/${id}/ack`)
      .then(() => {
        setAlerts(alerts.filter(alert => alert.id !== id));
        // Notify Layout to refresh the badge
        window.dispatchEvent(new Event('alertDismissed'));
      })
      .catch((err) => console.error('Failed to acknowledge alert:', err));
  };

  const renderAlert = (alert) => {
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
        >
          Dismiss
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="alerts-container">
        <div className="loading">Loading alerts...</div>
      </div>
    );
  }

  return (
    <div className="alerts-container">
      <div className="alerts-header">
        <h1>Alerts</h1>
        {alerts.length > 0 && (
          <button className="mark-all-read-btn" onClick={handleMarkAllRead}>
            Mark All as Read
          </button>
        )}
      </div>
      
      {alerts.length === 0 ? (
        <div className="no-alerts">
          <p>No new alerts</p>
        </div>
      ) : (
        <div className="alerts-list">
          {alerts.map(renderAlert)}
        </div>
      )}
    </div>
  );
}

export default AlertsPage;