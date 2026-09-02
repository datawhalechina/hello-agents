import { useState, useCallback, useEffect } from 'react';
import type { Session } from '../types/session';
import { apiClient } from '../api/client';

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await apiClient.listSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Failed to list sessions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createSession = useCallback(async (name: string) => {
    const data = await apiClient.createSession(name);
    await refresh();
    return data.session_id;
  }, [refresh]);

  const deleteSession = useCallback(async (id: string) => {
    await apiClient.deleteSession(id);
    await refresh();
  }, [refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { sessions, loading, refresh, createSession, deleteSession };
}
