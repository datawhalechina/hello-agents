import React, { useState, useCallback } from 'react';
import { useRagFiles } from '../../hooks/useRagFiles';
import { FileListView } from './FileListView';
import { FileDropZone } from './FileDropZone';
import { Spinner } from '../shared/Spinner';

export const RagSettings: React.FC = () => {
  const { files, status, loading, refresh, deleteFile, supportedExtensions } = useRagFiles();
  const [uploading, setUploading] = useState(false);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/files/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }
      await refresh();
    } catch (err) {
      console.error('Upload failed:', err);
      alert('上传失败: ' + (err as Error).message);
    } finally {
      setUploading(false);
    }
  }, [refresh]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 状态概览 */}
      {status && (
        <div className="flex gap-2 text-[11px] text-[#6E6E73] font-sidebar">
          <span className="bg-[#ECEDF0] px-2 py-0.5 rounded-full">{status.file_count} 文件</span>
          <span className="bg-[#ECEDF0] px-2 py-0.5 rounded-full">{status.total_chunks} chunks</span>
        </div>
      )}

      {/* 文件列表 */}
      <FileListView files={files} onDelete={deleteFile} />

      {/* 上传区 */}
      <FileDropZone onUpload={handleUpload} uploading={uploading} supportedExtensions={supportedExtensions} />
    </div>
  );
};
