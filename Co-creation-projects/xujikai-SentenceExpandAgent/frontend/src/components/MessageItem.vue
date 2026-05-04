<!--
消息项组件
统一显示所有类型的消息（记者提问、用户回答、语法点评、系统提示等）
-->
<template>
  <div class="message-item" :class="messageTypeClass">
    <div class="message-header">
      <span class="message-avatar">{{ avatar }}</span>
      <span class="message-sender">{{ senderName }}</span>
      <span v-if="showStageBadge" class="stage-badge">{{ stageTitle }}</span>
    </div>
    <div class="message-content" :class="contentClass">
      <p class="message-text">{{ message }}</p>
      <div v-if="expandedSentence" class="expanded-section">
        <span class="expanded-label">✨ 扩写结果</span>
        <p class="expanded-text">{{ expandedSentence }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Stage } from '../types/expand';

const props = defineProps<{
  type: 'question' | 'user' | 'evaluation' | 'system' | 'thinking';
  message: string;
  stage?: Stage;
  expandedSentence?: string;
}>();

const avatar = computed(() => {
  const avatars = {
    question: '🎤',
    user: '👤',
    evaluation: '📝',
    system: '🔔',
    thinking: '💭'
  };
  return avatars[props.type];
});

const senderName = computed(() => {
  const names = {
    question: '记者',
    user: '你',
    evaluation: '语法点评',
    system: '系统',
    thinking: '正在思考'
  };
  return names[props.type];
});

const messageTypeClass = computed(() => `message-${props.type}`);

const contentClass = computed(() => `content-${props.type}`);

const showStageBadge = computed(() => props.type === 'question' && props.stage);

const stageTitle = computed(() => {
  if (!props.stage) return '';
  const titles: Record<Stage, string> = {
    stage1: '阶段 1',
    stage2: '阶段 2',
    stage3: '阶段 3',
    done: '完成'
  };
  return titles[props.stage];
});
</script>

<style scoped>
.message-item {
  margin-bottom: 1rem;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.message-avatar {
  font-size: 1.25rem;
}

.message-sender {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.stage-badge {
  margin-left: auto;
  padding: 0.25rem 0.75rem;
  background: #e8f4ff;
  color: #4a90e2;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.message-content {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.message-text {
  margin: 0;
  color: #333;
  line-height: 1.6;
  font-size: 0.95rem;
}

/* 记者提问样式 */
.message-question .message-content {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-bottom-left-radius: 4px;
}

/* 用户消息样式 */
.message-user .message-content {
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border-bottom-right-radius: 4px;
}

/* 语法点评样式 */
.message-evaluation .message-content {
  background: linear-gradient(135deg, #fff9e6,  #fff3cd);
  border-left: 4px solid #ffc107;
}

/* 系统消息样式 */
.message-system .message-content {
  background: #f8f9fa;
  color: #666;
  font-size: 0.85rem;
}

/* 思考提示样式 */
.message-thinking .message-content {
  background: #f0f4f8;
  color: #666;
  font-style: italic;
}

/* 扩写结果样式 */
.expanded-section {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed rgba(0, 0, 0, 0.1);
}

.expanded-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: #4a90e2;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.expanded-text {
  margin: 0;
  color: #2c3e50;
  line-height: 1.6;
  font-size: 0.95rem;
  font-weight: 500;
}
</style>
