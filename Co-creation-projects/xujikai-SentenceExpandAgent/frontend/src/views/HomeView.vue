<!--
主视图组件
整合所有子组件，实现完整的交互流程
-->
<template>
  <div class="home-view">
    <!-- 种子句输入区 -->
    <SeedInput v-if="!sessionStore.session" @start="handleStart" />

    <!-- 手动模式 -->
    <div v-else-if="sessionStore.mode === 'manual'" class="manual-mode">
      <div class="session-header">
        <h2>手动模式</h2>
        <p class="seed-display">原始句子：{{ sessionStore.seedSentence }}</p>
        <button class="reset-btn" @click="handleReset">重新开始</button>
      </div>

      <!-- 消息列表区域 -->
      <div class="message-list-container" ref="messageListContainer">
        <!-- 统一的消息列表 -->
        <MessageItem
          v-for="(msg, index) in manualModeMessages"
          :key="`msg-${index}`"
          :type="msg.type"
          :message="msg.message"
          :stage="msg.stage"
          :expanded-sentence="msg.expandedSentence"
        />

        <!-- 最终结果 -->
        <FinalResult
          v-if="sessionStore.isDone && sessionStore.finalPolished"
          :seed-sentence="sessionStore.seedSentence"
          :polished-sentence="sessionStore.finalPolished"
          @restart="handleReset"
        />
      </div>

      <!-- 用户输入框 -->
      <div v-if="!sessionStore.isDone" class="input-container">
        <UserInput
          @submit="handleSubmit"
        />
      </div>
    </div>

    <!-- 自动模式 -->
    <div v-else-if="sessionStore.mode === 'auto'" class="auto-mode">
      <div class="session-header">
        <h2>自动模式</h2>
        <p class="seed-display">原始句子：{{ sessionStore.seedSentence }}</p>
        <button class="reset-btn" @click="handleReset">重新开始</button>
      </div>

      <!-- 消息列表区域 -->
      <div class="message-list-container" ref="autoMessageListContainer">
        <!-- 统一的消息列表 -->
        <MessageItem
          v-for="(msg, index) in autoModeMessages"
          :key="`auto-msg-${index}`"
          :type="msg.type"
          :message="msg.message"
          :stage="msg.stage"
          :expanded-sentence="msg.expandedSentence"
        />

        <!-- 加载指示器 -->
        <div v-if="autoLoading" class="loading-indicator">
          <div class="spinner"></div>
          <p>{{ loadingText }}</p>
        </div>

        <!-- 最终结果 -->
        <FinalResult
          v-if="sessionStore.isDone && sessionStore.finalPolished"
          :seed-sentence="sessionStore.seedSentence"
          :polished-sentence="sessionStore.finalPolished"
          @restart="handleReset"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, computed, nextTick } from 'vue';
import { useSessionStore } from '../stores/session';
import { subscribeAutoMode } from '../api/expand';
import type { Mode, Stage, RoundRecord, SSEEvent } from '../types/expand';

import SeedInput from '../components/SeedInput.vue';
import UserInput from '../components/UserInput.vue';
import FinalResult from '../components/FinalResult.vue';
import MessageItem from '../components/MessageItem.vue';

const sessionStore = useSessionStore();

// 手动模式状态
const currentUserMessage = ref<string | null>(null);
const isThinking = ref(false);
const messageListContainer = ref<HTMLElement | null>(null);

// 自动模式状态
const autoLoading = ref(false);
const loadingText = ref('正在思考...');
const autoMessageListContainer = ref<HTMLElement | null>(null);
// 用于存储当前正在显示的临时消息（还未保存到 rounds 的）
const autoTempMessages = ref<Array<{
  type: 'question' | 'user' | 'evaluation' | 'system' | 'thinking';
  message: string;
  stage?: Stage;
  expandedSentence?: string;
}>>([]);
const currentRoundData = ref<Partial<RoundRecord>>({});
let cleanupSSE: (() => void) | null = null;

// 计算属性：手动模式统一的消息列表
const manualModeMessages = computed(() => {
  const messages: Array<{
    type: 'question' | 'user' | 'evaluation' | 'system' | 'thinking';
    message: string;
    stage?: Stage;
    expandedSentence?: string;
  }> = [];

  messages.push({
    type: 'user',
    message: sessionStore.seedSentence
  });

  // 添加已完成的轮次消息
  const roundsArray = sessionStore.rounds;
  roundsArray.forEach((round) => {
    // 记者提问
    if (round.question) {
      messages.push({
        type: 'question',
        message: round.question,
        stage: round.stage
      });
    }

    // 用户回答
    messages.push({
      type: 'user',
      message: round.user_answer
    });

    // 语法点评
    messages.push({
      type: 'evaluation',
      message: round.evaluation,
      expandedSentence: round.user_answer !== round.expanded_sentence ? round.expanded_sentence : undefined
    });
  });

  // 添加当前记者提问（如果有）
  if (sessionStore.currentQuestion && !sessionStore.isDone) {
    messages.push({
      type: 'question',
      message: sessionStore.currentQuestion,
      stage: sessionStore.currentStage
    });
  }

  // 添加当前用户消息（如果有）
  if (currentUserMessage.value) {
    messages.push({
      type: 'user',
      message: currentUserMessage.value
    });
  }

  // 添加思考提示（如果有）
  if (isThinking.value) {
    messages.push({
      type: 'thinking',
      message: '正在思考...'
    });
  }

  return messages;
});

// 计算属性：自动模式统一的消息列表
const autoModeMessages = computed(() => {
  const messages: Array<{
    type: 'question' | 'user' | 'evaluation' | 'system' | 'thinking';
    message: string;
    stage?: Stage;
    expandedSentence?: string;
  }> = [];

  // 添加种子句
  messages.push({
    type: 'user',
    message: sessionStore.seedSentence
  });

  // 添加已完成的轮次消息
  const roundsArray = sessionStore.rounds;
  roundsArray.forEach((round) => {
    // 记者提问
    if (round.question) {
      messages.push({
        type: 'question',
        message: round.question,
        stage: round.stage
      });
    }

    // AI回答
    messages.push({
      type: 'user',
      message: round.user_answer
    });

    // 语法点评
    messages.push({
      type: 'evaluation',
      message: round.evaluation,
      expandedSentence: round.user_answer !== round.expanded_sentence ? round.expanded_sentence : undefined
    });
  });

  // 添加临时消息（当前正在进行的阶段）
  messages.push(...autoTempMessages.value);

  return messages;
});

/**
 * 开始新会话
 */
async function handleStart(sentence: string, mode: Mode) {
  try {
    if (mode == 'auto') {
      autoLoading.value = true;
      loadingText.value = '正在启动自动模式...';
    } else {
      isThinking.value = true;
    }

    await sessionStore.startNewSession(sentence, mode);

    // 如果是自动模式，启动自动流程
    if (mode === 'auto') {
      startAutoMode();
    } else {
      isThinking.value = false;
    }
  } catch (error) {
    console.error('Failed to start session:', error);
    if (mode === 'auto') {
      autoLoading.value = false;
      loadingText.value = '连接失败，请重试';
    } else {
      isThinking.value = false;
    }
  }
}

/**
 * 手动模式提交
 */
async function handleSubmit(sentence: string) {
  // 立即显示用户消息
  currentUserMessage.value = sentence;
  isThinking.value = true;

  // 滚动到底部
  await nextTick();
  scrollToBottom();

  try {
    // 提交到后端（submitUserSentence 内部已经会刷新会话状态）
    await sessionStore.submitUserSentence(sentence);

    // 清除当前用户消息（因为它已经在 rounds 中了）
    currentUserMessage.value = null;
    isThinking.value = false;

    // 滚动到底部
    await nextTick();
    scrollToBottom();
  } catch (error) {
    console.error('Failed to submit sentence:', error);
    isThinking.value = false;
  }
}

/**
 * 滚动消息列表到底部
 */
function scrollToBottom(containerRef: HTMLElement | null = messageListContainer.value) {
  if (containerRef) {
    containerRef.scrollTop = containerRef.scrollHeight;
  }
}

/**
 * 重置会话
 */
function handleReset() {
  if (cleanupSSE) {
    cleanupSSE();
    cleanupSSE = null;
  }
  sessionStore.clearSession();
  autoTempMessages.value = [];
  currentRoundData.value = {};
  autoLoading.value = false;
}

/**
 * 启动自动模式
 */
function startAutoMode() {
  loadingText.value = '正在思考...';
  // 订阅 SSE 流
  cleanupSSE = subscribeAutoMode(
    sessionStore.sessionId,
    handleSSEMessage,
    handleSSEError,
    handleSSEComplete
  );
}

/**
 * 处理 SSE 消息
 */
function handleSSEMessage(event: SSEEvent) {
  if (!event.type || !event.data) {
    console.warn('Invalid SSE event format:', event);
    return;
  }

  const eventType = event.type;
  const eventData = event.data as any;

  switch (eventType) {
    case 'stage1':
    case 'stage2':
    case 'stage3':
      // 处理阶段事件
      const stage = eventType as Stage;

      if (eventData.question) {
        // 显示提问 - 添加到临时消息
        autoTempMessages.value = [
          {
            type: 'question',
            message: eventData.question,
            stage: stage
          }
        ];
        // 保存到当前轮次数据
        currentRoundData.value.question = eventData.question;
        loadingText.value = `阶段 ${eventType.slice(-1)}：记者正在提问...`;
        
        // 滚动到底部
        nextTick(() => {
          scrollToBottom(autoMessageListContainer.value);
        });
      }

      if (eventData.expanded) {
        // 扩写完成，先添加临时消息显示AI回答和点评
        autoTempMessages.value = [
          {
            type: 'question',
            message: currentRoundData.value.question || `请为这个句子增加细节`,
            stage: stage
          },
          {
            type: 'user',
            message: eventData.expanded
          },
          {
            type: 'evaluation',
            message: '自动模式生成，语法正确',
            expandedSentence: eventData.expanded
          }
        ];

        // 保存轮次数据
        if (!currentRoundData.value.question) {
          const defaultQuestions = {
            stage1: '请为这个句子增加一些细节',
            stage2: '请为这个句子增加时间或地点信息',
            stage3: '请为这个句子增加定语从句或状语从句',
            done: '',
          };
          currentRoundData.value.question = defaultQuestions[stage];
        }

        currentRoundData.value.stage = stage;
        currentRoundData.value.user_answer = eventData.expanded;
        currentRoundData.value.evaluation = '自动模式生成，语法正确';
        currentRoundData.value.expanded_sentence = eventData.expanded;

        // 保存轮次到 sessionStore
        const round: RoundRecord = {
          stage,
          question: currentRoundData.value.question,
          user_answer: currentRoundData.value.user_answer ?? '',
          evaluation: currentRoundData.value.evaluation,
          expanded_sentence: currentRoundData.value.expanded_sentence ?? '',
        };
        sessionStore.addRound(round);

        // 清空临时消息和当前轮次数据，准备下一阶段
        autoTempMessages.value = [];
        currentRoundData.value = {};
        
        loadingText.value = `阶段 ${eventType.slice(-1)}：扩写完成`;
        
        // 滚动到底部
        nextTick(() => {
          scrollToBottom(autoMessageListContainer.value);
        });
      }
      break;

    case 'polished':
      // 处理润色版本
      if (eventData.sentence) {
        sessionStore.setFinalPolished(eventData.sentence);
        loadingText.value = '正在生成最终润色版本...';
        // 更新阶段为完成
        sessionStore.updateStage('done');
      }
      break;

    case 'analysis':
      // 处理结构分析
      console.log('Structure analysis:', eventData.items);
      loadingText.value = '正在分析句子结构...';
      break;

    case 'progress':
      // 处理进度更新
      if (eventData.message) {
        loadingText.value = eventData.message;
      }
      break;

    case 'done':
      // 完成事件
      console.log('Auto mode completed with data:', eventData);
      loadingText.value = '完成！';

      // 如果 done 事件包含完整数据，可以更新 sessionStore
      if (eventData.stage1 || eventData.stage2 || eventData.stage3) {
        // 确保所有轮次都已保存
        ['stage1', 'stage2', 'stage3'].forEach((stageName, index) => {
          const stageData = eventData[stageName as keyof typeof eventData];
          if (stageData && sessionStore.rounds.length <= index) {
            const round: RoundRecord = {
              stage: stageName as Stage,
              question: stageData.question || '请扩写这个句子',
              'user_answer': stageData.expanded || sessionStore.seedSentence,
              evaluation: '自动模式生成，语法正确',
              'expanded_sentence': stageData.expanded || sessionStore.seedSentence
            };
            sessionStore.addRound(round);
          }
        });

        // 设置最终润色版本
        if (eventData.polished) {
          sessionStore.setFinalPolished(eventData.polished);
        }
      }

      // 标记会话完成
      sessionStore.updateStage('done');
      // 清空临时消息
      autoTempMessages.value = [];
      break;

    default:
      console.warn('Unknown SSE event type:', eventType);
  }
}

/**
 * 处理 SSE 错误
 */
function handleSSEError(error: Error) {
  console.error('SSE Error:', error);
  autoLoading.value = false;
  loadingText.value = '连接失败，请重试';
}

/**
 * 处理 SSE 完成
 */
async function handleSSEComplete() {
  console.log('SSE Stream completed');
  autoLoading.value = false;
  loadingText.value = '完成！';

  // 注意：不调用 refreshSession()，避免覆盖前端维护的状态
  // 自动模式的数据已经通过 SSE 事件在前端维护好了
  // currentStreamQuestion 和 currentStreamEvaluation 保持原样
  // sessionStore.rounds 中的所有轮次数据都会保留
}

// 清理
onUnmounted(() => {
  if (cleanupSSE) {
    cleanupSSE();
  }
});
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 2rem;
}

.session-header {
  max-width: 800px;
  margin: 0 auto 2rem;
  padding: 1.5rem;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.session-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: #333;
}

.seed-display {
  margin: 0;
  color: #666;
  font-size: 0.95rem;
}

.reset-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.reset-btn:hover {
  background: #5a6268;
}

.manual-mode,
.auto-mode {
  max-width: 800px;
  margin: 0 auto;
}

.message-list-container {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
  max-height: 60vh;
  overflow-y: auto;
  margin-bottom: 1rem;
}

.input-container {
  background: white;
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  bottom: 0;
}

.loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4a90e2;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-indicator p {
  margin: 0;
  color: #666;
  font-size: 0.95rem;
}
</style>
