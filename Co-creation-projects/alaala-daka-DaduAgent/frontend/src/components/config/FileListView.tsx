import React from 'react';
import { Trash2, FileText } from 'lucide-react';

interface RagFile {
  file_name: string;
  file_path: string;
  chunk_count: number;
  uploaded_at: string;
}

export const FileListView: React.FC<{
  files: RagFile[];
  onDelete: (name: string) => void;
}> = ({ files, onDelete }) => {
  if (files.length === 0) {
    return (
      <div className="text-center py-6 text-[#AEAEB2] text-sm font-sidebar">
        <FileText size={24} className="mx-auto mb-2 opacity-40" />
        知识库为空 — 拖拽文件到此处上传
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="text-xs font-medium text-[#6E6E73] font-sidebar mb-2">
        已上传文件 ({files.length})
      </div>
      {files.map((f) => (
        <div
          key={f.file_name}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white border border-[#E5E5EA]"
        >
          <FileText size={14} className="text-[#AEAEB2] flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-[#1D1D1F] truncate font-sidebar">
              {f.file_name}
            </div>
            <div className="text-[10px] text-[#AEAEB2] font-sidebar">
              {f.chunk_count} chunks · {f.uploaded_at?.slice(0, 16)}
            </div>
          </div>
          <button
            onClick={() => onDelete(f.file_name)}
            className="p-1 rounded hover:bg-red-50 text-[#AEAEB2] hover:text-[#FF3B30] transition-colors"
            title="删除"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
    </div>
  );
};
