import React, { useState, useEffect } from 'react';
import { MessageSquarePlus, Sparkles, Search, FileText } from 'lucide-react';
import { Button } from '../shared/Button';

interface EmptyStateProps {
  hasSession: boolean;
  onCreateSession: () => void;
  onSend?: (content: string) => void;
  /** 连接未就绪时禁用建议按钮，避免消息在 socket 未打开时被丢弃 */
  disabled?: boolean;
}

const suggestions = [
  { icon: Sparkles, text: '介绍一下 Agent_Dev 的功能' },
  { icon: Search, text: '帮我搜索最近 AI 领域的新闻' },
  { icon: FileText, text: '帮我查看 config/AgentConfig.yml 的内容' },
];

export const EmptyState: React.FC<EmptyStateProps> = ({ hasSession, onCreateSession, onSend, disabled }) => {
  const [showCreate, setShowCreate] = useState(!hasSession);

  // 当会话被创建后，自动切换到建议模式
  useEffect(() => {
    if (hasSession) setShowCreate(false);
  }, [hasSession]);

  if (showCreate) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="glass-light border border-[#E5E5EA] rounded-2xl shadow-lg p-8 max-w-sm text-center">
          <MessageSquarePlus size={40} className="mx-auto mb-4 text-[#0066CC]" />
          <h2 className="text-lg font-semibold text-[#1D1D1F] mb-2 font-sidebar">
            是否立即创建对话？
          </h2>
          <p className="text-sm text-[#6E6E73] mb-6 font-body">
            创建会话后即可开始与 Agent 对话，使用 AI 工具完成各种任务
          </p>
          <div className="flex gap-3 justify-center">
            <Button variant="primary" onClick={onCreateSession}>
              创建新会话
            </Button>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              稍后再说
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
      <h2 className="text-lg font-semibold text-[#1D1D1F] font-sidebar">
        尝试以下问题开始对话
      </h2>
      <div className="flex flex-col gap-2 max-w-md w-full">
        {suggestions.map(({ icon: Icon, text }, i) => (
          <button
            key={i}
            onClick={() => !disabled && onSend?.(text)}
            disabled={disabled}
            className="flex items-center gap-3 px-4 py-3 rounded-xl border border-[#E5E5EA] bg-white
              transition-all duration-200 text-left group
              enabled:hover:border-[#0066CC] enabled:hover:shadow-sm
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Icon size={18} className="text-[#AEAEB2] group-enabled:group-hover:text-[#0066CC] transition-colors" />
            <span className="text-sm text-[#1D1D1F] font-body">{text}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
