import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorMessage from '../components/ErrorMessage.jsx';

describe('ErrorMessage', () => {
  it('renders error message and icon', () => {
    render(<ErrorMessage message="Something went wrong" type="error" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('❌')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = jest.fn();
    render(<ErrorMessage message="Retry?" type="error" onRetry={onRetry} />);
    fireEvent.click(screen.getByLabelText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });
});
