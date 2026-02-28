import React from 'react';
import { render, screen } from '@testing-library/react';
import CustomBetBuilder from '../components/CustomBetBuilder.jsx';

describe('CustomBetBuilder', () => {
  it('renders modal when open', () => {
    render(<CustomBetBuilder games={[]} isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Build Custom Bet')).toBeInTheDocument();
  });

  it('does not render modal when closed', () => {
    render(<CustomBetBuilder games={[]} isOpen={false} onClose={() => {}} />);
    expect(screen.queryByText('Build Custom Bet')).toBeNull();
  });
});
