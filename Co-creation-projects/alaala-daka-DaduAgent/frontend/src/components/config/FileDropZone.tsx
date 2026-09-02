import React, { useState, useCallback, DragEvent } from 'react';
import { Upload, Loader2 } from 'lucide-react';

export const FileDropZone: React.FC<{
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
  supportedExtensions?: string[];
}> = ({ onUpload, uploading, supportedExtensions = ['.txt', '.pdf'] }) => {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      const name = file.name.toLowerCase();
      const ok = supportedExtensions.some((ext) => name.endsWith(ext));
      if (ok) {
        onUpload(file);
      } else {
        alert(`仅支持 ${supportedExtensions.join(' / ')} 文件`);
      }
    }
  }, [onUpload, supportedExtensions]);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
      className={`flex flex-col items-center justify-center gap-2 p-4 border-2 border-dashed rounded-xl
        transition-all duration-200 text-center
        ${dragOver ? 'border-[#0066CC] bg-blue-50' : 'border-[#D2D2D7] bg-[#FAFAFA]'}`}
    >
      {uploading ? (
        <>
          <Loader2 size={20} className="animate-spin text-[#0066CC]" />
          <span className="text-xs text-[#6E6E73] font-sidebar">上传中...</span>
        </>
      ) : (
        <>
          <Upload size={20} className="text-[#AEAEB2]" />
          <span className="text-xs text-[#AEAEB2] font-sidebar">
            拖拽 {supportedExtensions.join(' / ')} 文件到此处
          </span>
        </>
      )}
    </div>
  );
};
