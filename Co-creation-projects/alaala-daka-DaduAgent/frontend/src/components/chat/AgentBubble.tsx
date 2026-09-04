import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { DisplayMessage } from '../../types/chat';
import { CodeBlock } from './CodeBlock';
import { StreamingText } from './StreamingText';
import { TodoPanel } from './TodoPanel';

export const AgentBubble: React.FC<{ message: DisplayMessage }> = ({ message }) => (
  <div className="flex justify-start">
    <div className="max-w-[85%] bg-white border border-[#E5E5EA] rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
      {message.todoState && message.todoState.length > 0 && (
        <TodoPanel todos={message.todoState} />
      )}
      {message.isStreaming ? (
        <div className="markdown-body text-[15px] leading-relaxed">
          <StreamingText content={message.content} />
          <span className="inline-block w-2 h-4 bg-[#0066CC] animate-pulse ml-0.5 align-middle" />
        </div>
      ) : (
        <div className="markdown-body text-[15px] leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const codeStr = String(children).replace(/\n$/, '');
                if (match) {
                  return <CodeBlock language={match[1]} code={codeStr} />;
                }
                return (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      )}

      {/* 中断标识 */}
      {message.interrupted && (
        <div className="mt-2 text-[11px] text-[#AEAEB2] select-none">
          聊天中断
        </div>
      )}
    </div>
  </div>
);
