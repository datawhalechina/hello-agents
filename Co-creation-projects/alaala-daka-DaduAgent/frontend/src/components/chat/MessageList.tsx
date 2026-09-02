import React, { useRef, useEffect } from 'react';
import type { DisplayMessage } from '../../types/chat';
import { AgentBubble } from './AgentBubble';
import { UserBubble } from './UserBubble';
import { ToolCallBubble } from './ToolCallBubble';
import { AgentWorkingIndicator } from './AgentWorkingIndicator';

interface MessageListProps {
  messages: DisplayMessage[];
  /** 是否处于"Agent 工作中"状态（等待输出 → 输出结束） */
  working?: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, working }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 去重：相同 ID 的消息只保留最后一个（流式更新）
  const deduped = messages.reduce<DisplayMessage[]>((acc, msg) => {
    const existing = acc.findIndex(m => m.id === msg.id);
    if (existing >= 0) {
      acc[existing] = msg;
    } else {
      acc.push(msg);
    }
    return acc;
  }, []);

  // 正在流式输出的 agent 气泡（通常是最后一条）——指示器显示在其"左上侧"
  const hasStreamingAgent = !!working && deduped.some(m => m.role === 'agent' && m.isStreaming);

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
      {deduped.map((msg) => {
        const isStreamingAgent = msg.role === 'agent' && msg.isStreaming;
        const bubble = (() => {
          switch (msg.role) {
            case 'user':
              return <UserBubble key={msg.id} message={msg} />;
            case 'agent':
              return <AgentBubble key={msg.id} message={msg} />;
            case 'tool':
              return <ToolCallBubble key={msg.id} message={msg} />;
            default:
              return null;
          }
        })();
        return (
          <React.Fragment key={msg.id}>
            {hasStreamingAgent && isStreamingAgent && <AgentWorkingIndicator />}
            {bubble}
          </React.Fragment>
        );
      })}
      {/* 思考期（尚无流式气泡）时，指示器显示在列表末尾等待位置 */}
      {working && !hasStreamingAgent && <AgentWorkingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
};
