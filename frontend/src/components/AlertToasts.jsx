import React, { useEffect, useRef, useState } from "react";
import api from "../services/api.js";
import "./AlertToasts.css";

const POLL_INTERVAL_MS = 15000;

function AlertToasts() {
  const [toasts, setToasts] = useState([]);
  const seenIds = useRef(new Set());
  const initialized = useRef(false);

  const dismissToast = async (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));

    try {
      await api.post(`/alerts/${id}/ack`);
      window.dispatchEvent(new Event("alertDismissed"));
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
    }
  };

  const dismissAllToasts = () => {
    toasts.forEach((toast) => {
      dismissToast(toast.id);
    });
  };

  const enqueueToast = (alert) => {
    setToasts((prev) => {
      if (prev.some((t) => t.id === alert.id)) return prev;
      return [alert, ...prev].slice(0, 5);
    });
  };

  const fetchAlerts = async () => {
    try {
      const res = await api.get("/alerts/");
      const alerts = res.data || [];

      if (!initialized.current) {
        alerts.forEach((a) => seenIds.current.add(a.id));
        initialized.current = true;
        return;
      }

      alerts.forEach((alert) => {
        if (!seenIds.current.has(alert.id)) {
          seenIds.current.add(alert.id);
          enqueueToast(alert);
        }
      });
    } catch (err) {
      console.error("Failed to fetch alerts:", err);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, POLL_INTERVAL_MS);
    
    // Add click handler to dismiss toasts when clicking anywhere on the page
    const handlePageClick = (e) => {
      // Don't dismiss if clicking on the toast itself or the close button
      if (e.target.closest('.alert-toast-container')) {
        return;
      }
      if (toasts.length > 0) {
        dismissAllToasts();
      }
    };

    document.addEventListener('click', handlePageClick);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener('click', handlePageClick);
    };
  }, [toasts]);

  if (toasts.length === 0) return null;

  return (
    <div className="alert-toast-container">
      {toasts.map((alert) => (
        <div key={alert.id} className={`alert-toast ${alert.severity || "info"}`}>
          <div className="alert-toast-header">
            <div className="alert-toast-title">
              <span className="alert-toast-severity">{alert.severity}</span>
              <span className="alert-toast-category">{alert.category}</span>
            </div>
            <button
              className="alert-toast-close"
              onClick={() => dismissToast(alert.id)}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
          <div className="alert-toast-message">{alert.message}</div>
        </div>
      ))}
    </div>
  );
}

export default AlertToasts;
