import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../app/App';
import { RunLogDrawer } from '../features/search/RunLogDrawer';
import { Harness } from './harness';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });
const review = (id: string, title: string) => ({
  id, title, question: `Question ${title}`, pico: {}, created_at: '', updated_at: '',
  counts: { total_records: 0, unique_studies: 0, screened_included: 0, screened_excluded: 0, screened_maybe: 0, unscreened: 0, open_conflicts: 0 }
});
function renderApp() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><App /></QueryClientProvider>);
}
describe('Workspace connectivity', () => {
  it('creates a review from an empty database and uses its UUID with real zero counts', async () => {
    let reviews: ReturnType<typeof review>[] = [];
    const fetcher = vi.fn(async (url: string, options: RequestInit) => {
      if (url === '/api/health') return Response.json({ status: 'ok', db: 'ok' });
      if (url === '/api/reviews' && options.method === 'POST') {
        const data = JSON.parse(String(options.body)); reviews = [review('created-uuid', data.title)]; return Response.json(reviews[0]);
      }
      if (url === '/api/reviews') return Response.json(reviews);
      if (url.includes('duplicate-pairs')) return Response.json([]);
      if (url === '/api/reviews/created-uuid') return Response.json(reviews[0]);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetcher); renderApp();
    fireEvent.click(screen.getByRole('button', { name: 'Enter Workspace' }));
    expect(await screen.findByText(/Create a review to define your question/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'New review' }));
    fireEvent.change(screen.getByLabelText('Review title'), { target: { value: 'My protocol' } });
    fireEvent.change(screen.getByLabelText('Research question'), { target: { value: 'My question' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create review' }));
    expect(await screen.findByRole('heading', { name: 'My protocol' })).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(localStorage.getItem('evidenceflow_review')).toBe('created-uuid');
    expect(fetcher.mock.calls.some(([url]) => url.includes('/reviews/1'))).toBe(false);
  });
  it('switches to a different stored review without reusing the first review data', async () => {
    const first = review('first-uuid', 'First protocol'), second = review('second-uuid', 'Second protocol');
    vi.stubGlobal('fetch', vi.fn(async (url: string) => Response.json(url === '/api/reviews' ? [first, second]
      : url.includes('duplicate-pairs') ? [] : url.includes('second-uuid') ? second : url.includes('first-uuid') ? first : { status: 'ok' })));
    renderApp(); fireEvent.click(screen.getByRole('button', { name: 'Enter Workspace' }));
    await screen.findByRole('heading', { name: 'First protocol' });
    fireEvent.change(screen.getByLabelText('Review'), { target: { value: 'second-uuid' } });
    expect(await screen.findByRole('heading', { name: 'Second protocol' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'First protocol' })).not.toBeInTheDocument();
  });
  it('shows connection failure and allows retry instead of displaying sample records', async () => {
    let offline = true;
    vi.stubGlobal('fetch', vi.fn(async () => { if (offline) throw new Error('offline'); return Response.json([]); }));
    renderApp(); fireEvent.click(screen.getByRole('button', { name: 'Enter Workspace' }));
    expect(await screen.findByText('Cannot reach the backend. Start the backend server, then retry.')).toBeInTheDocument();
    offline = false; fireEvent.click(screen.getByRole('button', { name: 'Retry connection' }));
    expect(await screen.findByText(/Create a review to define your question/)).toBeInTheDocument();
  });
  it('polls queued import runs until completion and stops polling', async () => {
    let calls = 0;
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({
      id: 'run-uuid', review_id: 'review-uuid', query_version_id: 'query-uuid', run_type: 'import',
      status: ++calls === 1 ? 'queued' : 'completed', progress_percent: calls === 1 ? 0 : 100,
      started_at: '2026-10-28T10:00:00Z', completed_at: null, steps: []
    })));
    render(<Harness><RunLogDrawer runId="run-uuid" isOpen onClose={() => undefined} /></Harness>);
    expect(await screen.findByText('queued')).toBeInTheDocument();
    expect(await screen.findByText('completed', {}, { timeout: 2500 })).toBeInTheDocument();
    await waitFor(() => expect(calls).toBe(2));
  });
});
