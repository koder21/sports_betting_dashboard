import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import GameIntelPage from "./pages/GameIntelPage.jsx";
import PropExplorerPage from "./pages/PropExplorerPage.jsx";
import BetsPage from "./pages/BetsPage.jsx";
import AAIBetsPage from "./pages/AAIBetsPage.jsx";
import AlertsPage from "./pages/AlertsPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import SportsAnalyticsPage from "./pages/SportsAnalyticsPage.jsx";
import LiveScoresPage from "./pages/LiveScoresPage";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/live" replace />} />
          <Route path="/games/:gameId" element={<GameIntelPage />} />
          <Route path="/props" element={<PropExplorerPage />} />
          <Route path="/bets" element={<BetsPage />} />
          <Route path="/aai-bets" element={<AAIBetsPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/sports-analytics" element={<SportsAnalyticsPage />} />
          <Route path="/live" element={<LiveScoresPage />} /> 
          <Route path="/live/*" element={<LiveScoresPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;