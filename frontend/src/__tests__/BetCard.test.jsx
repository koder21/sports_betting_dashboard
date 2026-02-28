import React from 'react';
import { render, screen } from '@testing-library/react';
import BetCard from '../components/BetCard.jsx';

describe('BetCard', () => {
  it('renders bet selection and odds', () => {
    const bet = {
      selection: 'Celtics ML',
      odds: 2.5,
      stake: 100,
      status: 'won',
      placed_at: new Date().toISOString(),
    };
    render(<BetCard bet={bet} />);
    expect(screen.getByText('Celtics ML')).toBeInTheDocument();
    expect(screen.getByText(/Odds/)).toBeInTheDocument();
    expect(screen.getByText(/Stake/)).toBeInTheDocument();
  });
});
