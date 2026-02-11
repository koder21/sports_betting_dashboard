import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import GameDetailPage from "./pages/GameDetailPage.jsx";
import PropExplorerPage from "./pages/PropExplorerPage.jsx";
import BetsPage from "./pages/BetsPage.jsx";
import AAIBetsPage from "./pages/AAIBetsPage.jsx";
import AlertsPage from "./pages/AlertsPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import SportsAnalyticsPage from "./pages/SportsAnalyticsPage.jsx";
import LiveScoresPage from "./pages/LiveScoresPage";
import SettingsPage from "./pages/SettingsPage";

// Redirect component that properly handles path parameters
function GameRedirect() {
  const { gameId } = useParams();
  return <Navigate to={`/games/${gameId}/details`} replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/live" replace />} />
          <Route path="/games/:gameId" element={<GameRedirect />} />
          <Route path="/games/:gameId/details" element={<GameDetailPage />} />
          <Route path="/props" element={<PropExplorerPage />} />
          <Route path="/bets" element={<BetsPage />} />
          <Route path="/aai-bets" element={<AAIBetsPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/sports-analytics" element={<SportsAnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/live" element={<LiveScoresPage />} /> 
          <Route path="/live/*" element={<LiveScoresPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
