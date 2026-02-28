import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BetFilters from '../components/BetFilters.jsx';

describe('BetFilters', () => {
  const defaultProps = {
    activeTab: 'finished',
    showWins: true,
    showLosses: false,
    dateFilter: '',
    onShowWinsChange: jest.fn(),
    onShowLossesChange: jest.fn(),
    onDateFilterChange: jest.fn(),
  };

  it('renders win/loss checkboxes and date filter', () => {
    render(<BetFilters {...defaultProps} />);
    expect(screen.getByLabelText('Show wins')).toBeInTheDocument();
    expect(screen.getByLabelText('Show losses')).toBeInTheDocument();
    expect(screen.getByLabelText('Filter bets by date')).toBeInTheDocument();
  });

  it('calls onShowWinsChange when win checkbox changes', () => {
    render(<BetFilters {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Show wins'));
    expect(defaultProps.onShowWinsChange).toHaveBeenCalled();
  });
});
