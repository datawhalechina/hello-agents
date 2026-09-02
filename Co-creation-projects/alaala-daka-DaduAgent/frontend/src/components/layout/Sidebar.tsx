import React, { useState, useEffect } from 'react';
import { Plus, Search, Settings, MessageSquare, Trash2, Check, X } from 'lucide-react';
import { useSessions } from '../../hooks/useSessions';
import type { Session } from '../../types/session';

interface SidebarProps {
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onToggleConfig: () => void;
  onDeleteSession: (id: string) => void;
  refreshKey?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentSessionId,
  onSelectSession,
  onNewSession,
  onToggleConfig,
  onDeleteSession,
  refreshKey,
}) => {
  const { sessions, loading, refresh, deleteSession } = useSessions();
  const [search, setSearch] = useState('');
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 当 sessionId 更改、创建新会话或一轮对话结束时刷新列表
  useEffect(() => {
    refresh();
  }, [currentSessionId, refresh, refreshKey]);

  const filtered = sessions.filter((s: Session) => {
    const q = search.toLowerCase();
    return (
      s.session_id.toLowerCase().includes(q) ||
      (s.title || '').toLowerCase().includes(q)
    );
  });

  const handleDelete = async (id: string) => {
    if (deleting) return;
    setDeleting(true);
    try {
      await deleteSession(id);
      onDeleteSession(id);
    } catch (err) {
      console.error('Failed to delete session:', err);
    } finally {
      setDeleting(false);
      setConfirmingId(null);
    }
  };

  return (
    <aside className="w-[280px] flex-shrink-0 glass border-r border-[#E5E5EA] flex flex-col">
      {/* 顶部 — 标题 + 搜索 */}
      <div className="p-4 border-b border-[#E5E5EA]">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-base font-semibold text-[#1D1D1F] font-sidebar tracking-tight">
            Dadu Agent
          </h1>
          <button
            onClick={onNewSession}
            className="p-1.5 rounded-lg hover:bg-[#E5E5EA] transition-colors text-[#6E6E73] hover:text-[#1D1D1F]"
            title="新建会话"
          >
            <Plus size={18} />
          </button>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#AEAEB2]" />
          <input
            type="text"
            placeholder="搜索会话..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-[#F5F5F7] border border-[#E5E5EA]
              focus:outline-none focus:border-[#0066CC] focus:ring-1 focus:ring-[#0066CC]/20
              placeholder-[#AEAEB2] font-sidebar"
          />
        </div>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-[#AEAEB2] text-sm">加载中...</div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-[#AEAEB2] text-sm gap-2">
            <MessageSquare size={24} />
            <span>{search ? '无匹配会话' : '暂无会话 — 点击 + 创建'}</span>
          </div>
        ) : (
          filtered.map((s: Session) => (
            <div
              key={s.session_id}
              onClick={() => onSelectSession(s.session_id)}
              className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer mb-0.5
                transition-all duration-150
                ${s.session_id === currentSessionId
                  ? 'bg-white border-l-2 border-[#0066CC] shadow-sm'
                  : 'border-l-2 border-transparent hover:bg-white/60'}`}
            >
              <MessageSquare size={14} className={
                s.session_id === currentSessionId ? 'text-[#0066CC]' : 'text-[#AEAEB2]'
              } />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[#1D1D1F] truncate font-sidebar">
                  {s.title || '新会话'}
                </div>
                <div className="text-[11px] text-[#AEAEB2] font-sidebar">
                  {(s.user_message_count ?? s.message_count) * 2} 条消息
                  {s.created_at ? ` · ${s.created_at.slice(5, 16)}` : ''}
                  {s.session_id ? ` · ${s.session_id}` : ''}
                </div>
              </div>
              {confirmingId === s.session_id ? (
                <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => handleDelete(s.session_id)}
                    disabled={deleting}
                    className="p-1 rounded-md bg-[#FF3B30] text-white hover:bg-red-600
                      transition-colors disabled:opacity-50"
                    title="确认删除"
                  >
                    <Check size={12} />
                  </button>
                  <button
                    onClick={() => setConfirmingId(null)}
                    className="p-1 rounded-md bg-[#E5E5EA] text-[#6E6E73] hover:bg-[#D2D2D7]
                      transition-colors"
                    title="取消"
                  >
                    <X size={12} />
                  </button>
                </span>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmingId(s.session_id);
                  }}
                  className="p-1 rounded-md text-[#AEAEB2] hover:text-[#FF3B30] hover:bg-[#FFF5F5]
                    transition-colors opacity-0 group-hover:opacity-100"
                  title="删除会话"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* 底部 — 设置 */}
      <div className="p-3 border-t border-[#E5E5EA]">
        <button
          onClick={onToggleConfig}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-[#6E6E73]
            hover:bg-[#E5E5EA] hover:text-[#1D1D1F] transition-colors font-sidebar"
        >
          <Settings size={16} />
          <span>设置与工具</span>
        </button>
      </div>
    </aside>
  );
};
