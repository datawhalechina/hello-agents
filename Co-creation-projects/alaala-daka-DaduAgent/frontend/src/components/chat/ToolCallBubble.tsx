import React, { useState } from 'react';
import { Wrench, ChevronDown, ChevronUp } from 'lucide-react';
import type { DisplayMessage } from '../../types/chat';

const TOOL_ICONS: Record<string, string> = {
  search: '🔍',
  calculator: '🧮',
  todo: '📋',
  reflection: '📖',
  rag_summarize: '📚',
  file_manage: '📁',
  ask_for_answer: '❓',
  session: '💬',
};

export const ToolCallBubble: React.FC<{ message: DisplayMessage }> = ({ message }) => {
  const [expanded, setExpanded] = useState(false);
  const tc = message.toolCall;
  if (!tc) return null;

  const isError = tc.status === 'error';
  const icon = TOOL_ICONS[tc.tool] || '🔧';
  const toolName = tc.tool || 'unknown';

  return (
    <div className="flex justify-start">
      <div
        className={`max-w-[85%] rounded-lg text-sm overflow-hidden
          ${isError
            ? 'bg-[#FFF5F5] border-l-2 border-[#FF3B30]'
            : 'bg-[#F5F5F7] border border-[#E5E5EA]'}`}
      >
        {/* 头部 */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-white/50 transition-colors"
        >
          <span className="text-base">{icon}</span>
          <span className="font-medium text-[#6E6E73] font-sidebar text-xs">{toolName}</span>
          {isError ? (
            <span className="text-[11px] text-[#FF3B30] font-sidebar">· 调用失败</span>
          ) : (
            <span className="text-[11px] text-[#30B158] font-sidebar">· 已执行</span>
          )}
          <span className="flex-1" />
          {expanded ? <ChevronUp size={14} className="text-[#AEAEB2]" /> : <ChevronDown size={14} className="text-[#AEAEB2]" />}
        </button>

        {/* 详情 */}
        {expanded && (
          <div className="px-3 pb-3 border-t border-[#E5E5EA]">
            {tc.args && Object.keys(tc.args).length > 0 && (
              <div className="mt-2">
                <div className="text-[11px] text-[#AEAEB2] font-sidebar mb-1">参数</div>
                <pre className="text-xs font-mono bg-white rounded p-2 overflow-x-auto">
                  {JSON.stringify(tc.args, null, 2)}
                </pre>
              </div>
            )}
            {(tc.result || tc.error) && (
              <div className="mt-2">
                <div className="text-[11px] text-[#AEAEB2] font-sidebar mb-1">
                  {isError ? '错误详情' : '返回结果'}
                </div>
                <pre className={`text-xs font-mono rounded p-2 overflow-x-auto max-h-40 overflow-y-auto
                  ${isError ? 'bg-red-50 text-red-700' : 'bg-white text-[#1D1D1F]'}`}>
                  {tc.error || tc.result}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
