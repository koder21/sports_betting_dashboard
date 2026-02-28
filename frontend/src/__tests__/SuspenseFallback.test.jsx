import React from 'react';
import { render, screen } from '@testing-library/react';
import SuspenseFallback from '../components/SuspenseFallback.jsx';

describe('SuspenseFallback', () => {
  it('renders loading message', () => {
    render(<SuspenseFallback message="Loading..." />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
