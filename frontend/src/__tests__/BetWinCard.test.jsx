import React from 'react';
import { render, screen } from '@testing-library/react';
import BetWinCard from '../components/BetWinCard.jsx';

describe('BetWinCard', () => {
  it('renders win and loss badges', () => {
    const betData = {
      metadata: JSON.stringify({
        selection: 'Celtics ML',
        odds: 2.5,
        stake: 100,
        profit: 150,
        bet_type: 'moneyline',
        sport: 'NBA',
        status: 'won',
      }),
      created_at: new Date().toISOString(),
    };
    render(<BetWinCard betData={betData} />);
    expect(screen.getByText('✓ WON')).toBeInTheDocument();
    expect(screen.getByText('Celtics ML')).toBeInTheDocument();
    expect(screen.getByText('NBA')).toBeInTheDocument();
  });
});
