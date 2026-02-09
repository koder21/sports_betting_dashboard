import React, { useState, useEffect } from "react";
import LiveTicker from "./LiveTicker";
import AlertToasts from "./AlertToasts";
import { Link, useLocation } from "react-router-dom";
import api from "../services/api.js";

function Layout({ children }) {
  const location = useLocation();
  const [alertCount, setAlertCount] = useState(0);

  const loadAlertCount = async () => {
    try {
      const res = await api.get("/alerts/");
      setAlertCount(res.data?.length || 0);
    } catch (err) {
      console.error('Failed to fetch alert count:', err);
    }
  };

  useEffect(() => {
    loadAlertCount();
    // Poll for new alerts every 30 seconds (faster than 5 minutes)
    const interval = setInterval(loadAlertCount, 30000);
    
    // Listen for custom event when alerts are dismissed
    const handleAlertDismissed = () => {
      loadAlertCount();
    };
    window.addEventListener('alertDismissed', handleAlertDismissed);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('alertDismissed', handleAlertDismissed);
    };
  }, []);

  const navItems = [
    { path: "/live", label: "Live Scores"},
    { path: "/props", label: "Prop Explorer" },
    { path: "/bets", label: "Bets" },
    { path: "/aai-bets", label: "AAI Bets" },
    { path: "/analytics", label: "Bet Analytics" },
    { path: "/sports-analytics", label: "Sports Analytics" },
  ];

  const alertItem = { path: "/alerts", label: "Alerts", badge: alertCount };

  return (
    <div className="app-root">
      <aside className="sidebar">
        <div className="logo">Sports Intel</div>
        <nav className="nav-main">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={
                location.pathname.startsWith(item.path)
                  ? "nav-link active"
                  : "nav-link"
              }
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <nav className="nav-bottom">
          <Link
            to={alertItem.path}
            className={
              location.pathname.startsWith(alertItem.path)
                ? "nav-link active"
                : "nav-link"
            }
          >
            {alertItem.label}
            {alertItem.badge > 0 && (
              <span className="alert-badge">{alertItem.badge}</span>
            )}
          </Link>
        </nav>
      </aside>
      <main className="main-content">
        <LiveTicker />   {/* ⭐ NEW — always visible */}
        {children}
      </main>
      <AlertToasts />
    </div>
  );
}

export default Layout;