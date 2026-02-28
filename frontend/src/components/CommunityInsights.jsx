import React from 'react';
import './CommunityInsights.css';

export function CommunityInsights() {
  return (
    <div className="community-insights">
      <div className="under-construction">
        <div className="construction-icon">🚧</div>
        <h1>Community Insights</h1>
        <h2>Under Construction</h2>
        <p>This feature is coming soon!</p>
        <div className="features-preview">
          <h3>Coming Features:</h3>
          <ul>
            <li>📊 Trending betting picks from the community</li>
            <li>🎯 Popular prop bets tracking</li>
            <li>💬 Discord integration for group insights</li>
            <li>📈 Real-time betting trends</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
