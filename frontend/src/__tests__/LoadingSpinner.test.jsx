import React from 'react';
import { render, screen } from '@testing-library/react';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

describe('LoadingSpinner', () => {
  it('renders loading message', () => {
    render(<LoadingSpinner message="Loading..." />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
