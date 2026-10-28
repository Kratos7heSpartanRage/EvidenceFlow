import { QueryErrorResetBoundary } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { Component, Suspense } from 'react';

class ErrorView extends Component<{ children: ReactNode; onRetry: () => void; }, { error: Error | null; }> {
  state: { error: Error | null; } = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) return <div role="alert" className="rounded-xl border border-rose-800 bg-slate-900 p-6 space-y-3">
      <p>{this.state.error.message}</p>
      <button className="px-4 py-2 rounded-lg bg-brand-600" onClick={() => {
        this.props.onRetry(); this.setState({ error: null });
      }}>Retry</button>
    </div>;
    return this.props.children;
  }
}
export function DataBoundary({ children }: { children: ReactNode; }) {
  return <QueryErrorResetBoundary>{({ reset }) => <ErrorView onRetry={reset}>
    <Suspense fallback={<p role="status" className="p-6 text-slate-400">Loading workspace…</p>}>{children}</Suspense>
  </ErrorView>}</QueryErrorResetBoundary>;
}
