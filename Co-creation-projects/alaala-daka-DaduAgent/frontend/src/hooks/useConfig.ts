import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { ConfigValues, ConfigSchemas } from '../types/config';

export function useConfig() {
  const [schemas] = useState<ConfigSchemas>({});
  const [currentConfig, setCurrentConfig] = useState<Record<string, ConfigValues>>({});
  const [loading, setLoading] = useState(false);

  const loadConfig = useCallback(async (name: string) => {
    setLoading(true);
    try {
      const data = await apiClient.getConfig(name);
      setCurrentConfig(prev => ({ ...prev, [name]: data.values }));
    } catch (err) {
      console.error(`Failed to load config '${name}':`, err);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfig = useCallback(async (name: string, values: ConfigValues) => {
    try {
      await apiClient.updateConfig(name, values);
      setCurrentConfig(prev => ({ ...prev, [name]: { ...prev[name], ...values } }));
      return true;
    } catch (err) {
      console.error(`Failed to update config '${name}':`, err);
      return false;
    }
  }, []);

  return { schemas, currentConfig, loading, loadConfig, updateConfig };
}
