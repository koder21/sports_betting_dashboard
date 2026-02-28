import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BetTabs from '../components/BetTabs.jsx';

describe('BetTabs', () => {
  it('renders all tabs', () => {
    render(<BetTabs activeTab="pending" onTabChange={() => {}} />);
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Finished')).toBeInTheDocument();
    expect(screen.getByText('Voided')).toBeInTheDocument();
  });

  it('calls onTabChange when a tab is clicked', () => {
    const onTabChange = jest.fn();
    render(<BetTabs activeTab="pending" onTabChange={onTabChange} />);
    fireEvent.click(screen.getByText('Finished'));
    expect(onTabChange).toHaveBeenCalledWith('finished');
  });
});
