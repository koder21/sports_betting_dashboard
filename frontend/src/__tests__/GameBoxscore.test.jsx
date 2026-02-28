import React from 'react';
import { render, screen } from '@testing-library/react';
import GameBoxscore from '../components/GameBoxscore.jsx';

describe('GameBoxscore', () => {
  it('renders game info', () => {
    const gameData = {
      metadata: JSON.stringify({
        home_team_name: 'Celtics',
        away_team_name: 'Heat',
        home_score: 100,
        away_score: 90,
        sport: 'NBA',
        status: 'final',
      }),
      created_at: new Date().toISOString(),
    };
    render(<GameBoxscore gameData={gameData} />);
    expect(screen.getByText('Celtics')).toBeInTheDocument();
    expect(screen.getByText('Heat')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('90')).toBeInTheDocument();
    expect(screen.getByText('NBA')).toBeInTheDocument();
    expect(screen.getByText('final')).toBeInTheDocument();
  });

  it('shows error for invalid metadata', () => {
    const gameData = { metadata: 'invalid json', created_at: new Date().toISOString() };
    render(<GameBoxscore gameData={gameData} />);
    expect(screen.getByText(/invalid game metadata/i)).toBeInTheDocument();
  });
});
