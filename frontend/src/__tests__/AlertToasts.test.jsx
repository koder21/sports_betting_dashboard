import React from 'react';
import { render, screen } from '@testing-library/react';
import AlertToasts from '../components/AlertToasts.jsx';

describe('AlertToasts', () => {
  it('renders nothing when no toasts', () => {
    render(<AlertToasts />);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
