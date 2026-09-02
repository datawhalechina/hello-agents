import React, { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { Send, Square, Paperclip, File, X, Loader2 } from 'lucide-react';
import { apiClient } from '../../api/client';
import { formatSize, extOf } from '../../utils/format';
import type { ChatAttachment } from '../../types/chat';

const MAX_UPLOAD_SIZE = 10 * 1024 * 1024; // 10MB，与后端一致

interface ChatInputProps {
  onSend: (content: string, attachments?: ChatAttachment[]) => void;
  onCancel: () => void;
  streaming: boolean;
  disabled: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, onCancel, streaming, disabled }) => {
  const [value, setValue] = useState('');
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    // 流式生成期间忽略回车发送，防止 flushPending 截断正在输出的气泡并排队第二个回合
    if ((!trimmed && attachments.length === 0) || disabled || streaming || uploading) return;
    onSend(trimmed, attachments);
    setValue('');
    setAttachments([]);
    setFileError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, attachments, disabled, streaming, uploading, onSend]);

  const handleFiles = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    e.target.value = ''; // 允许重选同一文件
    if (selected.length === 0) return;
    setUploading(true);
    let error = '';
    for (const file of selected) {
      if (file.size >= MAX_UPLOAD_SIZE) {
        error = `${file.name}: 文件大小超过 10MB，无法上传`;
        continue;
      }
      try {
        const att = await apiClient.uploadChatFile(file);
        setAttachments(prev => [...prev, att]);
      } catch (err) {
        error = err instanceof Error ? err.message : `上传 ${file.name} 失败`;
      }
    }
    setFileError(error || null);
    setUploading(false);
  }, []);

  const removeAttachment = useCallback((path: string) => {
    setAttachments(prev => prev.filter(a => a.path !== path));
  }, []);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
  };

  return (
    <div className="max-w-3xl mx-auto">
      {fileError && (
        <div className="mb-1 px-1 text-[13px] text-[#FF3B30]">{fileError}</div>
      )}
      <div
        className={`bg-white rounded-2xl border flex flex-col shadow-sm transition-all duration-300
          ${streaming ? 'border-[#0066CC] animate-breathe-border' : 'border-[#E5E5EA] hover:border-[#D2D2D7]'}
          ${disabled ? 'opacity-50' : ''}`}
      >
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-4 pt-3 pb-1 max-h-24 overflow-y-auto">
            {attachments.map(a => (
              <span
                key={a.path}
                className="inline-flex items-center gap-1.5 bg-[#ECEDF0] text-[#1D1D1F] text-[12px] rounded-full pl-2.5 pr-1 py-0.5"
              >
                <File size={12} className="text-[#0066CC]" />
                <span className="font-medium max-w-[160px] truncate">{a.name}</span>
                {extOf(a.name) && <span className="text-[#6E6E73]">.{extOf(a.name)}</span>}
                <span className="text-[#6E6E73]">· {formatSize(a.size)}</span>
                <button
                  onClick={() => removeAttachment(a.path)}
                  title="移除"
                  className="p-0.5 rounded-full text-[#6E6E73] hover:bg-[#D2D2D7]"
                >
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2 px-4 py-3">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? '连接断开中...' : '输入消息... (Enter 发送, Shift+Enter 换行)'}
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none bg-transparent text-[15px] leading-relaxed placeholder-[#AEAEB2]
              focus:outline-none max-h-[160px]"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || disabled}
            title="上传文件"
            className="flex-shrink-0 p-2 rounded-full transition-colors text-[#86868B]
              enabled:hover:text-[#0066CC] disabled:text-[#AEAEB2]"
          >
            {uploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
          </button>
          {streaming ? (
            <button
              onClick={onCancel}
              className="flex-shrink-0 p-2 rounded-full bg-[#FF3B30] text-white
                hover:bg-red-600 transition-colors active:scale-95"
              title="停止生成"
            >
              <Square size={16} fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={(!value.trim() && attachments.length === 0) || uploading || disabled}
              className="flex-shrink-0 p-2 rounded-full transition-all duration-200
                enabled:bg-[#0066CC] enabled:text-white enabled:hover:bg-[#0077ED]
                enabled:active:scale-95
                disabled:bg-[#ECEDF0] disabled:text-[#AEAEB2]"
              title="发送"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </div>
      <input ref={fileInputRef} type="file" multiple hidden onChange={handleFiles} />
    </div>
  );
};
