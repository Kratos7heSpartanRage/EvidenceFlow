import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { HistoryDiffView } from '../features/history/HistoryDiffView';
import { mockDiffSummary } from '../mocks/mockData';

describe('Level 2 Query Evolution & Decision Preservation Diff View', () => {
  it('renders all key diff indicators correctly based on stored snapshot state', async () => {
    render(<HistoryDiffView />);

    await waitFor(() => {
      expect(screen.getByText('Query Evolution & Decision Preservation')).toBeInTheDocument();
    });

    // Check diff metric cards
    expect(screen.getByText('+45')).toBeInTheDocument(); // records added
    expect(screen.getByText('500')).toBeInTheDocument(); // already present
    expect(screen.getByText('498')).toBeInTheDocument(); // decisions preserved
    expect(screen.getByText('+42')).toBeInTheDocument(); // inherited
    expect(screen.getByText('1')).toBeInTheDocument();   // conflicts opened
  });

  it('opens confirmation modal when clicking Exact Revert to v1', async () => {
    render(<HistoryDiffView />);

    await waitFor(() => {
      expect(screen.getByText('Exact Revert to v1')).toBeInTheDocument();
    });

    const revertBtn = screen.getByText('Exact Revert to v1');
    fireEvent.click(revertBtn);

    expect(screen.getByText('Confirm Exact Revert to v1')).toBeInTheDocument();
    expect(screen.getByText(/Zero external API requests will be performed/i)).toBeInTheDocument();

    const executeBtn = screen.getByRole('button', { name: /Execute Revert/i });
    expect(executeBtn).toBeInTheDocument();
  });
});
