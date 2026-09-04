import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { ReflectionEntry, ReflectionCreate, ReflectionUpdate } from '../types/config';

/**
 * 反思笔记状态 hook：列表 + 增删改。
 * 每次变更后自动刷新列表；刷新失败只记日志，不抛错（避免误报"操作失败"）。
 */
export function useReflections() {
  const [reflections, setReflections] = useState<ReflectionEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.listReflections();
      setReflections(data.reflections);
    } catch (err) {
      console.error('Failed to load reflections:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(async (input: ReflectionCreate) => {
    const res = await apiClient.createReflection(input);
    await refresh();
    return res;
  }, [refresh]);

  const update = useCallback(async (refId: string, patch: ReflectionUpdate) => {
    const res = await apiClient.updateReflection(refId, patch);
    await refresh();
    return res;
  }, [refresh]);

  const remove = useCallback(async (refId: string) => {
    const res = await apiClient.deleteReflection(refId);
    await refresh();
    return res;
  }, [refresh]);

  return { reflections, loading, refresh, create, update, remove };
}
