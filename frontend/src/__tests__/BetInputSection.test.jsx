import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BetInputSection from '../components/BetInputSection.jsx';

describe('BetInputSection', () => {
  const defaultProps = {
    rawText: '',
    onTextChange: jest.fn(),
    onPlaceBets: jest.fn(),
    onCopyForAI: jest.fn(),
    onRetryClipboardCopy: jest.fn(),
    onDeleteAllPending: jest.fn(),
    loading: false,
    copyingAI: false,
    showCopyRetry: false,
    activeTab: 'pending',
    pendingCount: 2,
  };

  it('renders textarea and buttons', () => {
    render(<BetInputSection {...defaultProps} />);
    expect(screen.getByLabelText('Enter bet details')).toBeInTheDocument();
    expect(screen.getByLabelText('Place bets from text input')).toBeInTheDocument();
    expect(screen.getByLabelText('Copy game context for AI analysis')).toBeInTheDocument();
    expect(screen.getByLabelText('Delete all 2 pending bets')).toBeInTheDocument();
  });

  it('calls onTextChange when textarea changes', () => {
    render(<BetInputSection {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('Enter bet details'), { target: { value: 'test' } });
    expect(defaultProps.onTextChange).toHaveBeenCalledWith('test');
  });
});
