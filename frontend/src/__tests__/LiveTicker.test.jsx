import React from 'react';
import { render, screen } from '@testing-library/react';
import LiveTicker from '../components/LiveTicker.jsx';
import { MemoryRouter } from 'react-router-dom';

describe('LiveTicker', () => {
  it('renders empty ticker when no games', () => {
    render(
      <MemoryRouter>
        <LiveTicker />
      </MemoryRouter>
    );
    expect(screen.getByText('No live games right now')).toBeInTheDocument();
  });
});
