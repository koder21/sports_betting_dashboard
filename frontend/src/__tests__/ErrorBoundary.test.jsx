import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../components/ErrorBoundary.jsx';

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Test Child</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Test Child')).toBeInTheDocument();
  });

  it('renders fallback UI on error', () => {
    const ProblemChild = () => {
      throw new Error('Test error');
    };
    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});
