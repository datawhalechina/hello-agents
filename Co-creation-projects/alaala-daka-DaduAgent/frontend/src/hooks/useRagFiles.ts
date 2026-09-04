import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '../api/client';

interface RagFile {
  file_name: string;
  file_path: string;
  chunk_count: number;
  uploaded_at: string;
}

interface RagStatus {
  file_count: number;
  total_chunks: number;
  vector_count: number;
  supported_extensions: string[];
}

export function useRagFiles() {
  const [files, setFiles] = useState<RagFile[]>([]);
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [filesData, statusData] = await Promise.all([
        apiClient.listRagFiles(),
        apiClient.getRagStatus(),
      ]);
      setFiles((filesData.files || []) as RagFile[]);
      setStatus(statusData);
    } catch (err) {
      console.error('Failed to load RAG files:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteFile = useCallback(async (name: string) => {
    await apiClient.deleteRagFile(name);
    await refresh();
  }, [refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const supportedExtensions = status?.supported_extensions ?? ['.txt', '.pdf'];

  return { files, status, loading, refresh, deleteFile, supportedExtensions };
}
