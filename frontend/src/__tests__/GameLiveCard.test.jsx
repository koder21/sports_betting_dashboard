import React from 'react';
import { render, screen } from '@testing-library/react';
import GameLiveCard from '../components/GameLiveCard.jsx';

describe('GameLiveCard', () => {
  it('renders live badge and team names', () => {
    const gameData = {
      metadata: JSON.stringify({
        home_team_name: 'Celtics',
        away_team_name: 'Heat',
        home_score: 100,
        away_score: 90,
        sport: 'NBA',
        status: 'in',
        period: 'Q4',
        clock: '2:00',
      }),
    };
    render(<GameLiveCard gameData={gameData} />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(screen.getByText('Celtics')).toBeInTheDocument();
    expect(screen.getByText('Heat')).toBeInTheDocument();
    expect(screen.getByText('Q4')).toBeInTheDocument();
    expect(screen.getByText('2:00')).toBeInTheDocument();
  });
});
