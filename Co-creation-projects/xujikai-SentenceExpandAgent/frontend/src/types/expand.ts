/**
 * 英语句子扩写智能体 - 类型定义
 * 与后端 models/entities.py 对齐
 */

// 扩写阶段枚举
export type Stage = 'stage1' | 'stage2' | 'stage3' | 'done';

// 交互模式
export type Mode = 'manual' | 'auto';

// 单次扩写轮次记录
export interface RoundRecord {
  stage: Stage;
  question: string;           // 记者提问
  user_answer: string;        // 用户输入的句子
  evaluation: string;         // 语法点评
  expanded_sentence: string;  // 本轮扩写结果
}

// 整个会话状态
export interface SessionState {
  session_id: string;
  mode: Mode;
  seed_sentence: string;
  current_stage: Stage | null;
  rounds: RoundRecord[];
  final_polished: string | null;
}

// 开始会话请求
export interface StartRequest {
  seed_sentence: string;
  mode: Mode;
}

// 提交用户句子请求（手动模式）
export interface SubmitRequest {
  session_id: string;
  user_sentence: string;
}

// 智能体单次响应
export interface AgentResponse {
  session_id: string;
  stage: Stage;
  question?: string;
  evaluation?: string;
  expanded_sentence?: string;
  final_polished?: string;
  is_done: boolean;
}

// SSE 事件类型
export interface SSEEvent {
  type: 'stage1' | 'stage2' | 'stage3' | 'polished' | 'analysis' | 'progress' | 'done' | 'error';
  data?: any;  // data 的结构取决于 type
  error?: {
    detail: string;
    type: string;
  };
}
