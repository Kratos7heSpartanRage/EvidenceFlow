import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { HistoryDiffView } from '../features/history/HistoryDiffView';
import { Harness } from './harness';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const queries = [1, 2, 3].map(n => ({
  id: `query-${n}`, review_id: 'review-uuid', version_number: n,
  parent_id: n > 1 ? `query-${n - 1}` : null, label: `Search ${n}`, expression: 'search', source: 'europe_pmc',
  status: 'approved', imported_count: 0, hit_count: 0, created_at: '', expand_synonyms: false, title_abstract_only: false
}));
function installApi() {
  return vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/queries')) return Response.json(queries);
    if (url.includes('/diff?')) return Response.json({
      new_records_count: 45, retained_records_count: 500,
      dropped_records_count: 0, already_screened_retained_count: 498, potential_conflicts_count: 1
    });
    if (url.endsWith('/revert')) return Response.json({ status: 'reverted', restored_version_id: 'query-1', restored_records_count: 0, hidden_records_count: 5 });
    throw new Error(`Unexpected request ${url}`);
  }));
}
describe('Stored query history', () => {
  it('compares selected UUID versions and shows only metrics supplied by the backend', async () => {
    installApi(); render(<Harness><HistoryDiffView /></Harness>);
    expect(await screen.findByText('Query Evolution & Decision Preservation')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument(); expect(screen.getByText('498')).toBeInTheDocument();
    expect(screen.queryByText('Inherited Decisions')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('To version'), { target: { value: 'query-2' } });
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/queries/query-2/diff?against=query-1', expect.anything()));
  });
  it('confirms a restore and displays returned zero counts', async () => {
    installApi(); render(<Harness><HistoryDiffView /></Harness>);
    fireEvent.click(await screen.findByRole('button', { name: 'Restore v1' }));
    expect(screen.getByText(/Zero external API requests will be performed/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Execute restore' }));
    expect(await screen.findByText('Restored v1: 0 records visible, 5 hidden. No source requests were made.')).toBeInTheDocument();
  });
});
