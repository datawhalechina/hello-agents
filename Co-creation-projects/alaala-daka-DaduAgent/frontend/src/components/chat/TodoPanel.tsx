import React from 'react';
import type { TodoItem } from '../../types/chat';

const STATUS_ICON: Record<TodoItem['status'], string> = {
  pending: '⬜',
  in_progress: '🔄',
  done: '✅',
};

/**
 * 待办清单面板：把 Agent 的 todo 快照渲染为带进度条的任务列表。
 * 由后端 {"type":"todo","todos":[...]} 事件驱动，流式过程中实时更新。
 */
export const TodoPanel: React.FC<{ todos: TodoItem[] }> = ({ todos }) => {
  const total = todos.length;
  const doneCount = todos.filter(t => t.status === 'done').length;
  const pct = total ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div className="my-2 rounded-lg border border-[#E5E5EA] bg-[#F5F5F7] overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-white/60 border-b border-[#E5E5EA]">
        <span className="text-sm">📋</span>
        <span className="font-medium text-[13px] text-[#1D1D1F]">待办清单</span>
        <span className="text-[11px] text-[#6E6E73]">{doneCount}/{total} 已完成</span>
        <div className="flex-1 ml-2 h-1.5 rounded-full bg-[#E5E5EA] overflow-hidden">
          <div
            className="h-full bg-[#0066CC] rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <ul className="px-3 py-2 space-y-1">
        {todos.map(t => (
          <li key={t.id} className="flex items-start gap-2 text-[13px]">
            <span className="leading-5">{STATUS_ICON[t.status] || '❓'}</span>
            <span className={t.status === 'done' ? 'line-through text-[#AEAEB2]' : 'text-[#1D1D1F]'}>
              {t.title}
            </span>
            {t.desc ? <span className="text-[#6E6E73]">— {t.desc}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
};
