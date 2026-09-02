import React, { useState, useCallback, useRef } from 'react';
import { AppShell } from './components/layout/AppShell';
import { ChatArea } from './components/chat/ChatArea';
import { useWebSocket } from './hooks/useWebSocket';
import { apiClient } from './api/client';
import type { DisplayMessage } from './types/chat';

/** 用户消息里上传文件注释块的匹配（与后端 Agent.build_file_note 的标记一致） */
const FILE_NOTE_RE = /\[已上传文件\][\s\S]*?\[[/]?已上传文件\]/g;

/** 剥离用户消息中的上传文件注释块，返回剩余文本与文件路径列表 */
function parseFileNote(text: string): { stripped: string; paths: string[] } {
  const paths: string[] = [];
  const stripped = text
    .replace(FILE_NOTE_RE, (block) => {
      for (const line of block.split('\n')) {
        const m = line.match(/^-\s+(.+)$/);
        if (m) paths.push(m[1].trim());
      }
      return '';
    })
    .replace(/\n{2,}/g, '\n')
    .trim();
  return { stripped, paths };
}

/** 将后端消息格式转换为前端 DisplayMessage；无可渲染内容的记录返回 null */
function convertBackendMessage(msg: Record<string, unknown>, index: number): DisplayMessage | null {
  const type = (msg.type as string) || 'human';
  const roleMap: Record<string, DisplayMessage['role']> = {
    human: 'user',
    ai: 'agent',
    tool: 'tool',
    system: 'system',
  };
  const role = roleMap[type] || 'agent';
  // 对 tool message，检查是否包含错误
  let content = typeof msg.content === 'string' ? msg.content : '';
  const isTool = type === 'tool';
  const error = msg.error as string | undefined;

  // 用户消息：剥离上传文件注释块，改为附件 chip
  let attachments: DisplayMessage['attachments'];
  if (type === 'human') {
    const { stripped, paths } = parseFileNote(content);
    content = stripped;
    if (paths.length) {
      attachments = paths.map(p => ({
        name: p.split('/').pop() || p,
        path: p,
        size: 0, // 历史不持久化大小；UI 对 size===0 省略大小段
      }));
    }
  }

  // 跳过无文本且无附件的 AI/用户历史消息（纯 tool_calls 中间步骤 / 历史遗留空记录），避免空气泡
  if (!isTool && !content.trim() && (!attachments || attachments.length === 0)) return null;
  return {
    id: `history-${index}`,
    role: isTool ? 'tool' : role,
    content: isTool ? (error || content) : content,
    timestamp: Date.now() - (1000 - index),
    ...(attachments ? { attachments } : {}),
    ...(isTool ? { toolCall: {
      call_id: `hist-${index}`,
      tool: (msg.tool as string) || (msg.name as string) || 'unknown',
      args: (msg.args as Record<string, unknown>) || {},
      result: error ? undefined : content,
      error,
      status: error ? 'error' as const : 'success' as const,
    }} : {}),
  };
}

export default function App() {
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sessionListKey, setSessionListKey] = useState(0);
  const nextSessionIdRef = useRef<string>('');

  const handleMessage = useCallback((msg: DisplayMessage) => {
    setMessages(prev => {
      const existing = prev.findIndex(m => m.id === msg.id);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = msg;
        return updated;
      }
      return [...prev, msg];
    });
  }, []);

  const handleStreamingChange = useCallback((s: boolean) => {
    setStreaming(s);
  }, []);

  // 一轮对话结束后通知侧栏刷新（标题/消息数已更新）
  const handleTurnEnd = useCallback(() => setSessionListKey(k => k + 1), []);

  const {
    send, cancel, answerUser, connected,
    askUser, dismissAskUser,
  } = useWebSocket({
    sessionId,
    onMessage: handleMessage,
    onStreamingChange: handleStreamingChange,
    onTurnEnd: handleTurnEnd,
  });

  const handleCreateSession = useCallback(async () => {
    try {
      const data = await apiClient.createSession('新会话');
      setSessionId(data.session_id);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  }, []);

  const handleSelectSession = useCallback(async (id: string) => {
    if (id === sessionId) return;
    setSessionId(id);
    setMessages([]);
    setLoadingHistory(true);
    nextSessionIdRef.current = id;
    try {
      const data = await apiClient.getMessages(id, 0, 200);
      if (nextSessionIdRef.current !== id) return; // 竞态保护
      const history: DisplayMessage[] = (data.messages || [])
        .map((m, i) => convertBackendMessage(m as Record<string, unknown>, i))
        .filter((m): m is DisplayMessage => m !== null);
      // 历史回显：把会话持久化的 todo 状态附加到最后一条 agent 消息上，渲染待办面板
      if (data.todos && data.todos.length > 0) {
        for (let i = history.length - 1; i >= 0; i--) {
          if (history[i].role === 'agent') {
            history[i] = { ...history[i], todoState: data.todos as import('./types/chat').TodoItem[] };
            break;
          }
        }
      }
      setMessages(history);
    } catch (err) {
      console.error('Failed to load history:', err);
      if (nextSessionIdRef.current === id) setMessages([]);
    } finally {
      if (nextSessionIdRef.current === id) setLoadingHistory(false);
    }
  }, [sessionId]);

  const handleDeleteSession = useCallback((id: string) => {
    // 删除当前会话时，清空聊天区并回到无会话状态（WebSocket 会自动重连到临时会话）
    if (id === sessionId) {
      setSessionId('');
      setMessages([]);
    }
  }, [sessionId]);

  return (
    <AppShell
      currentSessionId={sessionId}
      onSelectSession={handleSelectSession}
      onNewSession={handleCreateSession}
      onDeleteSession={handleDeleteSession}
      configPanelOpen={configOpen}
      onToggleConfig={() => setConfigOpen(!configOpen)}
      onConfigPanelClose={() => setConfigOpen(false)}
      refreshKey={sessionListKey}
    >
      <ChatArea
        messages={messages}
        streaming={streaming}
        connected={connected}
        askUser={askUser}
        hasSession={!!sessionId}
        loadingHistory={loadingHistory}
        onSend={send}
        onCancel={cancel}
        onAnswerUser={answerUser}
        onDismissAskUser={dismissAskUser}
        onCreateSession={handleCreateSession}
      />
    </AppShell>
  );
}
