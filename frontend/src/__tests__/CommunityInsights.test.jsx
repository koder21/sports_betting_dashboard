import React from 'react';
import { render, screen } from '@testing-library/react';
import { CommunityInsights } from '../components/CommunityInsights.jsx';

describe('CommunityInsights', () => {
  it('renders under construction message', () => {
    render(<CommunityInsights />);
    expect(screen.getByText('Community Insights')).toBeInTheDocument();
    expect(screen.getByText('Under Construction')).toBeInTheDocument();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });
});
