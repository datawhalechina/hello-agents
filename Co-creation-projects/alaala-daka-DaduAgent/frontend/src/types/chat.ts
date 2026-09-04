// WebSocket 消息类型定义

export interface WsMessageBase {
  type: string;
}

// 附件（对话内上传的文件）
export interface ChatAttachment {
  name: string;   // 显示名（原始文件名）
  path: string;   // 项目根相对路径，如 'uploads/foo.txt'
  size: number;   // 字节
}

// ── Client → Server ──
export interface ChatMessage extends WsMessageBase {
  type: 'chat';
  content: string;
  files?: string[];   // 本次上传文件路径（项目根相对），隐式交给 Agent
}

export interface CancelMessage extends WsMessageBase {
  type: 'cancel';
}

export interface UserAnswerMessage extends WsMessageBase {
  type: 'user_answer';
  request_id: string;
  answer: 'approved' | 'rejected';
  detail?: string;
}

export type ClientMessage = ChatMessage | CancelMessage | UserAnswerMessage | { type: 'ping' };

// ── Server → Client ──
export interface ChunkMessage extends WsMessageBase {
  type: 'chunk';
  content: string;
}

export interface ToolCallMessage extends WsMessageBase {
  type: 'tool_call';
  call_id: string;
  tool: string;
  args: Record<string, unknown>;
}

export interface ToolResultMessage extends WsMessageBase {
  type: 'tool_result';
  call_id: string;
  tool: string;
  result: string;
}

export interface ToolErrorMessage extends WsMessageBase {
  type: 'tool_error';
  call_id: string;
  tool: string;
  error: string;
}

export interface AskUserMessage extends WsMessageBase {
  type: 'ask_user';
  request_id: string;
  question: string;
}

export interface DoneMessage extends WsMessageBase {
  type: 'done';
}

export interface InterruptedMessage extends WsMessageBase {
  type: 'interrupted';
}

export interface ErrorMessage extends WsMessageBase {
  type: 'error';
  message: string;
}

export interface SessionInfoMessage extends WsMessageBase {
  type: 'session_info';
  session_id: string;
  message_count: number;
}

export interface TodoItem {
  id: number;
  title: string;
  desc: string;
  status: 'pending' | 'in_progress' | 'done';
  created_at?: string;
  done_at?: string | null;
}

export interface TodoSnapshotMessage extends WsMessageBase {
  type: 'todo';
  todos: TodoItem[];
}

export type ServerMessage =
  | ChunkMessage
  | ToolCallMessage
  | ToolResultMessage
  | ToolErrorMessage
  | AskUserMessage
  | DoneMessage
  | InterruptedMessage
  | ErrorMessage
  | SessionInfoMessage
  | TodoSnapshotMessage
  | { type: 'pong' };

// ── 消息显示模型（UI 层使用）──
export type DisplayMessageRole = 'user' | 'agent' | 'tool' | 'system';

export interface DisplayMessage {
  id: string;
  role: DisplayMessageRole;
  content: string;
  timestamp: number;
  toolCall?: {
    call_id: string;
    tool: string;
    args: Record<string, unknown>;
    result?: string;
    error?: string;
    status: 'running' | 'success' | 'error';
  };
  interrupted?: boolean;
  isStreaming?: boolean;
  attachments?: ChatAttachment[];
  todoState?: TodoItem[];
}
