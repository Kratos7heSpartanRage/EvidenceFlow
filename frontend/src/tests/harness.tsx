import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { DataBoundary } from '../components/ui/DataBoundary';
import { WorkspaceContext } from '../lib/workspace';

export function Harness({ children, reviewId = 'review-uuid' }: { children: ReactNode; reviewId?: string; }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={client}><WorkspaceContext.Provider value={{ reviewId, reportError: error => { throw error; } }}>
    <DataBoundary>{children}</DataBoundary>
  </WorkspaceContext.Provider></QueryClientProvider>;
}
