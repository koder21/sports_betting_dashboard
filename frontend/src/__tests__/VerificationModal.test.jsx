import React from 'react';
import { render, screen } from '@testing-library/react';
import VerificationModal from '../components/VerificationModal.jsx';

describe('VerificationModal', () => {
  const results = {
    total_graded: 5,
    discrepancies_found: 1,
    discrepancies: [
      {
        type: 'single',
        selection: 'Celtics ML',
        current_status: 'pending',
        expected_status: 'won',
        stake: 100,
        odds: 2.5,
        reason: 'Grading error',
      },
    ],
  };

  it('renders modal and discrepancy', () => {
    render(<VerificationModal results={results} onClose={() => {}} onApply={() => {}} />);
    expect(screen.getByText(/Bet Verification Results/)).toBeInTheDocument();
    expect(screen.getByText('Celtics ML')).toBeInTheDocument();
    expect(screen.getByText('Grading error')).toBeInTheDocument();
  });
});
