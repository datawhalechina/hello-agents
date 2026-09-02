import React, { useCallback, useRef, useEffect } from 'react';
import type { DisplayMessage, AskUserMessage, ChatAttachment } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { EmptyState } from './EmptyState';
import { AskUserDialog } from './AskUserDialog';
import { ConnectionBanner } from './ConnectionBanner';

interface ChatAreaProps {
  messages: DisplayMessage[];
  streaming: boolean;
  connected: boolean;
  askUser: AskUserMessage | null;
  hasSession: boolean;
  loadingHistory: boolean;
  onSend: (content: string, attachments?: ChatAttachment[]) => void;
  onCancel: () => void;
  onAnswerUser: (requestId: string, answer: 'approved' | 'rejected', detail?: string) => void;
  onDismissAskUser: () => void;
  onCreateSession: () => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  streaming,
  connected,
  askUser,
  hasSession,
  loadingHistory,
  onSend,
  onCancel,
  onAnswerUser,
  onDismissAskUser,
  onCreateSession,
}) => {
  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* 连接状态横幅 */}
      {!connected && <ConnectionBanner />}

      {/* 消息区 */}
      <div className="flex-1 overflow-y-auto">
        {loadingHistory ? (
          <div className="flex items-center justify-center h-full text-[#AEAEB2] text-sm font-sidebar">
            加载历史消息...
          </div>
        ) : messages.length === 0 ? (
          <EmptyState
            hasSession={hasSession}
            onCreateSession={onCreateSession}
            onSend={onSend}
            disabled={!connected}
          />
        ) : (
          <MessageList messages={messages} working={streaming} />
        )}
      </div>

      {/* 输入区 */}
      <div className="border-t border-[#E5E5EA] bg-[#F5F5F7] p-4">
        <ChatInput
          onSend={onSend}
          onCancel={onCancel}
          streaming={streaming}
          disabled={!connected}
        />
      </div>

      {/* ask_for_answer 确认弹窗 */}
      {askUser && (
        <AskUserDialog
          question={askUser.question}
          requestId={askUser.request_id}
          onAnswer={onAnswerUser}
          onDismiss={onDismissAskUser}
        />
      )}
    </div>
  );
};
