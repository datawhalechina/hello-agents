/**
 * 英语句子扩写智能体 - API 封装
 * 包含 REST API 和 SSE 流式接口
 */

import type {
  StartRequest,
  SubmitRequest,
  AgentResponse,
  SessionState,
  SSEEvent
} from '../types/expand';

// API 基础 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 开始新的扩写会话
 */
export async function startSession(request: StartRequest): Promise<AgentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/session/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to start session: ${response.statusText}`);
  }

  return response.json();
}

/**
 * 提交用户扩写句子（手动模式）
 */
export async function submitSentence(request: SubmitRequest): Promise<AgentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/session/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to submit sentence: ${response.statusText}`);
  }

  return response.json();
}

/**
 * 获取会话完整状态
 */
export async function getSession(sessionId: string): Promise<SessionState> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to get session: ${response.statusText}`);
  }

  return response.json();
}

/**
 * SSE 流式自动模式
 * @param sessionId 会话 ID
 * @param onMessage 接收到消息消息时的回调
 * @param onError 发生错误时的回调
 * @param onComplete 完成时的回调
 * @returns 清理函数，用于关闭 EventSource
 */
export function subscribeAutoMode(
  sessionId: string,
  onMessage: (event: SSEEvent) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): () => void {
  const eventSource = new EventSource(
    `${API_BASE_URL}/api/session/${sessionId}/auto`
  );

  // 处理普通消息
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage({
        type: data.type || 'question',
        data: data.data,
      });
    } catch (error) {
      console.error('Failed to parse SSE message:', error);
    }
  };

  // 处理完成事件
  eventSource.addEventListener('done', () => {
    onComplete?.();
    eventSource.close();
  });

  // 处理错误事件
  eventSource.addEventListener('error', (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage({
        type: 'error',
        error: data.error,
      });
    } catch (error) {
      console.error('Failed to parse error event:', error);
    }
    onError?.(new Error('Auto mode error'));
  });

  // 处理连接错误
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    onError?.(new Error('SSE connection failed'));
    eventSource.close();
  };

  // 返回清理函数
  return () => {
    eventSource.close();
  };
}
