import React from 'react';
import { File } from 'lucide-react';
import type { DisplayMessage } from '../../types/chat';
import { formatSize, extOf } from '../../utils/format';

export const UserBubble: React.FC<{ message: DisplayMessage }> = ({ message }) => {
  const hasText = message.content.trim().length > 0;
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] bg-[#007AFF] text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm">
        {message.attachments?.length ? (
          <div className="flex flex-wrap gap-1.5 mb-1.5">
            {message.attachments.map(a => (
              <span
                key={a.path}
                className="inline-flex items-center gap-1 bg-white/25 text-white text-[12px] rounded-full px-2 py-0.5"
                title={a.path}
              >
                <File size={12} />
                <span className="max-w-[160px] truncate">{a.name}</span>
                {extOf(a.name) && <span>.{extOf(a.name)}</span>}
                {/* 历史回显 size=0：省略大小段 */}
                {a.size > 0 && <span>· {formatSize(a.size)}</span>}
              </span>
            ))}
          </div>
        ) : null}
        {hasText ? (
          <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </p>
        ) : null}
      </div>
    </div>
  );
};
