import React from 'react';
import { render, screen } from '@testing-library/react';
import Toast from '../components/Toast.jsx';

describe('Toast', () => {
  it('renders success toast', () => {
    render(<Toast message="Success!" type="success" onClose={() => {}} />);
    expect(screen.getByText('Success!')).toBeInTheDocument();
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('renders error toast', () => {
    render(<Toast message="Error!" type="error" onClose={() => {}} />);
    expect(screen.getByText('Error!')).toBeInTheDocument();
    expect(screen.getByText('✕')).toBeInTheDocument();
  });
});
