import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query';
import type { Dispatch, SetStateAction } from 'react';
import { createContext, useContext } from 'react';
import type { EntityId } from '../types/api';

export const WorkspaceContext = createContext<{
  reviewId: EntityId; reportError: (error: unknown) => void;
}>({ reviewId: '', reportError: () => undefined });

export function useWorkspace() { return useContext(WorkspaceContext); }

export function useData<T>(key: readonly unknown[], loader: () => Promise<T>) {
  const { reviewId } = useWorkspace();
  const client = useQueryClient();
  const queryKey = ['workspace', reviewId, ...key];
  const { data } = useSuspenseQuery({ queryKey, queryFn: loader, retry: false });
  const setData: Dispatch<SetStateAction<T>> = (value) => {
    client.setQueryData<T>(queryKey, previous => typeof value === 'function' ? (value as (data: T) => T)(previous ?? data) : value);
  };
  const reload = () => client.fetchQuery({ queryKey, queryFn: loader, staleTime: 0 });
  return [data, setData, reload] as const;
}

export function useAction<Args extends unknown[]>(action: (...args: Args) => Promise<unknown>) {
  const { reportError } = useWorkspace();
  const client = useQueryClient();
  return async (...args: Args) => {
    try {
      await action(...args);
      await client.invalidateQueries({ queryKey: ['workspace'] });
      await client.invalidateQueries({ queryKey: ['reviews'] });
    } catch (error) { reportError(error); }
  };
}
