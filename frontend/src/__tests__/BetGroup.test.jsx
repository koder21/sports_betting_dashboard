import React from 'react';
import { render, screen } from '@testing-library/react';
import BetGroup from '../components/BetGroup.jsx';

describe('BetGroup', () => {
  it('renders parlay group and legs', () => {
    const group = {
      bets: [
        { id: 1, selection: 'Celtics ML', odds: 2.5, stake: 100, status: 'won', parlay_id: 123, bet_type: 'moneyline', game_id: 1, player_id: 1, result_value: null, final_score: 'Final: 100-90' },
        { id: 2, selection: 'Heat ML', odds: 1.8, stake: 100, status: 'lost', parlay_id: 123, bet_type: 'moneyline', game_id: 2, player_id: 2, result_value: null, final_score: 'Final: 90-100' },
      ],
      isParlay: true,
      status: 'finished',
      stake: 100,
      pnl: 50,
    };
    render(<BetGroup group={group} oddsFormat="american" />);
    expect(screen.getByText('2-Leg Parlay')).toBeInTheDocument();
    expect(screen.getByText('Celtics ML')).toBeInTheDocument();
    expect(screen.getByText('Heat ML')).toBeInTheDocument();
    expect(screen.getByText(/100-90/)).toBeInTheDocument();
    expect(screen.getByText(/90-100/)).toBeInTheDocument();
  });
});
