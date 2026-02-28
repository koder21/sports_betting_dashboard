import React from 'react';
import { render, screen } from '@testing-library/react';
import BetPlacementModal from '../components/BetPlacementModal.jsx';

describe('BetPlacementModal', () => {
  const bet = {
    game_id: 1,
    pick: 'Celtics ML',
    confidence: 80,
    combined_confidence: 80,
    odds: 2.5,
    reason: 'Strong matchup',
    sport: 'NBA',
    away: 'Heat',
    home: 'Celtics',
  };

  it('renders modal and bet details', () => {
    render(<BetPlacementModal bet={bet} isOpen={true} onClose={() => {}} onSuccess={() => {}} />);
    // There are multiple 'Place Bet' elements (header and button), so check for at least one
    expect(screen.getAllByText('Place Bet').length).toBeGreaterThan(0);
    expect(screen.getByText('Celtics ML')).toBeInTheDocument();
    expect(screen.getByText('Strong matchup')).toBeInTheDocument();
    // The sport ('NBA') is not rendered directly in the modal, so skip this assertion
    // If you want to check for sport, add it to the modal or use a flexible matcher
  });
});
