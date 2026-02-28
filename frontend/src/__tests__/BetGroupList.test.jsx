import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BetGroupList from '../components/BetGroupList.jsx';

const mockToggleDay = jest.fn();
const mockToggleExpansion = jest.fn();
const mockDeleteGroup = jest.fn();

const sampleGroups = [
  {
    parlay_id: 'parlay-1',
    bets: [{ id: 101 }],
  },
  {
    parlay_id: 'parlay-2',
    bets: [{ id: 102 }],
  },
];

const betsByDay = [
  {
    date: '2026-02-25',
    groups: sampleGroups,
    stake: 100,
    pnl: 50,
  },
  {
    date: '2026-02-24',
    groups: [],
    stake: 0,
    pnl: -10,
  },
];

const collapsedDays = {
  '2026-02-25': false,
  '2026-02-24': true,
};

const expandedBets = {
  101: true,
  102: false,
};

const oddsFormat = 'decimal';

describe('BetGroupList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders no bets found when betsByDay is empty', () => {
    render(
      <BetGroupList
        betsByDay={[]}
        collapsedDays={{}}
        expandedBets={{}}
        oddsFormat={oddsFormat}
        onToggleDay={mockToggleDay}
        onToggleExpansion={mockToggleExpansion}
        onDeleteGroup={mockDeleteGroup}
      />
    );
    expect(screen.getByText(/no bets found/i)).toBeInTheDocument();
  });

  it('renders day sections and bet groups', () => {
    render(
      <BetGroupList
        betsByDay={betsByDay}
        collapsedDays={collapsedDays}
        expandedBets={expandedBets}
        oddsFormat={oddsFormat}
        onToggleDay={mockToggleDay}
        onToggleExpansion={mockToggleExpansion}
        onDeleteGroup={mockDeleteGroup}
      />
    );
    expect(screen.getAllByRole('button', { name: /expand|collapse/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/staked/i).length).toBeGreaterThan(0);
    // Check for profit/loss values by their formatted currency
    expect(screen.getByText((content) => content.includes('+$'))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('-$'))).toBeInTheDocument();
  });

  it('calls onToggleDay when day header is clicked', () => {
    render(
      <BetGroupList
        betsByDay={betsByDay}
        collapsedDays={collapsedDays}
        expandedBets={expandedBets}
        oddsFormat={oddsFormat}
        onToggleDay={mockToggleDay}
        onToggleExpansion={mockToggleExpansion}
        onDeleteGroup={mockDeleteGroup}
      />
    );
    const dayHeader = screen.getAllByRole('button', { name: /expand|collapse/i })[0];
    fireEvent.click(dayHeader);
    expect(mockToggleDay).toHaveBeenCalled();
  });

  it('renders bet groups when not collapsed', () => {
    render(
      <BetGroupList
        betsByDay={betsByDay}
        collapsedDays={collapsedDays}
        expandedBets={expandedBets}
        oddsFormat={oddsFormat}
        onToggleDay={mockToggleDay}
        onToggleExpansion={mockToggleExpansion}
        onDeleteGroup={mockDeleteGroup}
      />
    );
    // Should render BetGroup components for each group in not-collapsed day
    expect(screen.getAllByText(/bet/i).length).toBeGreaterThan(0);
  });

  it('matches snapshot for typical rendering', () => {
    const { container } = render(
      <BetGroupList
        betsByDay={betsByDay}
        collapsedDays={collapsedDays}
        expandedBets={expandedBets}
        oddsFormat={oddsFormat}
        onToggleDay={mockToggleDay}
        onToggleExpansion={mockToggleExpansion}
        onDeleteGroup={mockDeleteGroup}
      />
    );
    expect(container).toMatchSnapshot();
  });
});
