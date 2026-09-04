import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { ModelEntry, ModelInput, EmbeddingConfig, RerankerConfig, AuxModelUpdate } from '../types/config';

/**
 * 模型注册表状态 hook：列表 + active + 增删改切换 + embedding/reranker 辅助模型配置。
 * 每次变更后自动刷新；辅助模型配置获取失败不阻断（.catch(() => null)）；
 * 刷新失败只记日志，不抛错（避免误报"操作失败"）。
 */
export function useModels() {
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [active, setActive] = useState('');
  const [embedding, setEmbedding] = useState<EmbeddingConfig | null>(null);
  const [reranker, setReranker] = useState<RerankerConfig | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [data, emb, rrk] = await Promise.all([
        apiClient.listModels(),
        apiClient.getEmbeddingConfig().catch(() => null),
        apiClient.getRerankerConfig().catch(() => null),
      ]);
      setModels(data.models);
      setActive(data.active_model);
      setEmbedding(emb?.embedding ?? null);
      setReranker(rrk?.reranker ?? null);
    } catch (err) {
      console.error('Failed to load models:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const addModel = useCallback(async (input: ModelInput) => {
    const res = await apiClient.addModel(input);
    await refresh();
    return res;
  }, [refresh]);

  const updateModel = useCallback(async (name: string, patch: Partial<Omit<ModelEntry, 'name'>>) => {
    const res = await apiClient.updateModel(name, patch);
    await refresh();
    return res;
  }, [refresh]);

  const deleteModel = useCallback(async (name: string) => {
    const res = await apiClient.deleteModel(name);
    await refresh();
    return res;
  }, [refresh]);

  const setActiveModel = useCallback(async (name: string) => {
    const res = await apiClient.setActiveModel(name);
    await refresh();
    return res;
  }, [refresh]);

  const updateEmbedding = useCallback(async (patch: AuxModelUpdate) => {
    const res = await apiClient.updateEmbeddingConfig(patch);
    await refresh();
    return res;
  }, [refresh]);

  const updateReranker = useCallback(async (patch: AuxModelUpdate) => {
    const res = await apiClient.updateRerankerConfig(patch);
    await refresh();
    return res;
  }, [refresh]);

  return {
    models,
    active,
    embedding,
    reranker,
    loading,
    refresh,
    addModel,
    updateModel,
    deleteModel,
    setActiveModel,
    updateEmbedding,
    updateReranker,
  };
}
