import React from 'react';
import { render, screen } from '@testing-library/react';
import Layout from '../components/Layout.jsx';
import { MemoryRouter } from 'react-router-dom';

describe('Layout', () => {
  it('renders sidebar and main content', () => {
    render(
      <MemoryRouter>
        <Layout><div>Test Content</div></Layout>
      </MemoryRouter>
    );
    expect(screen.getByText('Sports Intel')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });
});
