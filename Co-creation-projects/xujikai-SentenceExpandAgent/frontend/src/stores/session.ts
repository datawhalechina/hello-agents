/**
 * 英语句子扩写智能体 - 会话状态管理
 * 使用 Pinia 管理会话状态
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type {
  SessionState,
  AgentResponse,
  Mode,
  Stage,
  RoundRecord
} from '../types/expand';
import { startSession, submitSentence, getSession } from '../api/expand';

export const useSessionStore = defineStore('session', () => {
  // 状态
  const session = ref<SessionState | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const currentQuestion = ref<string | null>(null);

  // 计算属性
  const currentStage = computed<Stage>(() => session.value?.current_stage || 'stage1');
  const mode = computed<Mode>(() => session.value?.mode || 'manual');
  const seedSentence = computed(() => session.value?.seed_sentence || '');
  const rounds = computed<RoundRecord[]>(() => session.value?.rounds || []);
  const finalPolished = computed(() => session.value?.final_polished || null);
  const isDone = computed(() => session.value?.current_stage === 'done');
  const sessionId = computed(() => session.value?.session_id || '');

  /**
   * 开始新的会话
   */
  async function startNewSession(seedSentence: string, mode: Mode) {
    loading.value = true;
    error.value = null;

    try {
      session.value = {
        session_id: "",
        mode,
        seed_sentence: seedSentence,
        current_stage: null,
        rounds: [],
        final_polished: null,
      };

      const response = await startSession({
        seed_sentence: seedSentence,
        mode,
      });

      // 更新状态
      session.value = {
        session_id: response.session_id,
        mode,
        seed_sentence: seedSentence,
        current_stage: response.stage,
        rounds: [],
        final_polished: response.final_polished || null,
      };

      // 保存当前提问
      currentQuestion.value = response.question || null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start session';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 提交用户句子（手动模式）
   */
  async function submitUserSentence(userSentence: string) {
    if (!session.value) {
      throw new Error('No active session');
    }

    loading.value = true;
    error.value = null;

    try {
      const response = await submitSentence({
        session_id: session.value.session_id,
        user_sentence: userSentence,
      });

      // 直接从响应中获取信息，不调用 refreshSession
      // 首先，需要手动更新会话状态
      if (session.value && response.evaluation && response.expanded_sentence) {
        // 创建新的 round 记录
        const newRound = {
          stage: session.value.current_stage,
          question: currentQuestion.value || '',
          user_answer: userSentence,
          evaluation: response.evaluation,
          expanded_sentence: response.expanded_sentence
        };
        
        // 添加到 rounds 数组
        session.value.rounds.push(newRound);
        
        // 更新当前阶段
        if (response.stage) {
          session.value.current_stage = response.stage;
        }
        
        // 更新最终润色结果
        if (response.final_polished) {
          session.value.final_polished = response.final_polished;
        }
      }

      // 保存当前提问
      currentQuestion.value = response.question || null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to submit sentence';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 刷新会话状态
   */
  async function refreshSession() {
    if (!session.value) {
      throw new Error('No active session');
    }

    try {
      const updatedSession = await getSession(session.value.session_id);
      session.value = updatedSession;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to refresh session';
      throw e;
    }
  }

  /**
   * 添加轮次记录（用于自动模式）
   */
  function addRound(round: RoundRecord) {
    if (!session.value) {
      throw new Error('No active session');
    }
    session.value.rounds.push(round);
  }

  /**
   * 更新当前阶段
   */
  function updateStage(stage: Stage) {
    if (!session.value) {
      throw new Error('No active session');
    }
    session.value.current_stage = stage;
  }

  /**
   * 设置最终润色版本
   */
  function setFinalPolished(polished: string) {
    if (!session.value) {
      throw new Error('No active session');
    }
    session.value.final_polished = polished;
  }

  /**
   * 设置当前提问
   */
  function setCurrentQuestion(question: string | null) {
    currentQuestion.value = question;
  }

  /**
   * 清除会话
   */
  function clearSession() {
    session.value = null;
    currentQuestion.value = null;
    error.value = null;
    loading.value = false;
  }

  /**
   * 获取当前阶段的标题
   */
  function getStageTitle(stage: Stage): string {
    const titles: Record<Stage, string> = {
      stage1: '第一阶段：添加时间与地点',
      stage2: '第二阶段：添加人物与原因',
      stage3: '第三阶段：添加方式与细节',
      done: '完成',
    };
    return titles[stage];
  }

  return {
    // 状态
    session,
    loading,
    error,
    currentQuestion,

    // 计算属性
    currentStage,
    mode,
    seedSentence,
    rounds,
    finalPolished,
    isDone,
    sessionId,

    // 方法
    startNewSession,
    submitUserSentence,
    refreshSession,
    addRound,
    updateStage,
    setFinalPolished,
    setCurrentQuestion,
    clearSession,
    getStageTitle,
  };
});
