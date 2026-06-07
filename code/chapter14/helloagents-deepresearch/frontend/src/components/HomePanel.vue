<template>
  <section class="panel panel-form panel-centered">
    <header class="panel-head">
      <div class="logo">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 2.5c-.7 0-1.4.2-2 .6L4.6 7C3.6 7.6 3 8.7 3 9.9v4.2c0 1.2.6 2.3 1.6 2.9l5.4 3.9c1.2.8 2.8.8 4 0l5.4-3.9c1-.7 1.6-1.7 1.6-2.9V9.9c0-1.2-.6-2.3-1.6-2.9L14 3.1a3.6 3.6 0 0 0-2-.6Z"
          />
        </svg>
      </div>
      <div>
        <h1>找实习助手</h1>
        <p>搜索岗位和投递渠道，分析 JD 要求，生成可执行的投递建议。</p>
      </div>
    </header>

    <form class="form" @submit.prevent="emit('submit')">
      <label class="field">
        <span>求职目标</span>
        <textarea
          v-model="form.topic"
          placeholder="例如：我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot、MySQL、Redis，有一个 RAG 项目。"
          rows="4"
          required
        ></textarea>
      </label>

      <section class="example-prompts" aria-label="求职目标示例">
        <button
          v-for="example in internshipExamples"
          :key="example.label"
          type="button"
          class="example-chip"
          :disabled="loading"
          @click="emit('fill-example', example.text)"
        >
          {{ example.label }}
        </button>
      </section>

      <section class="options">
        <label class="field option">
          <span>搜索引擎</span>
          <select v-model="form.searchApi">
            <option value="">沿用后端配置</option>
            <option
              v-for="option in searchOptions"
              :key="option"
              :value="option"
            >
              {{ option }}
            </option>
          </select>
        </label>
      </section>

      <div class="form-actions">
        <button class="submit" type="submit" :disabled="loading">
          <span class="submit-label">
            <svg
              v-if="loading"
              class="spinner"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" stroke-width="3" />
            </svg>
            {{ loading ? "正在找实习..." : "开始找实习" }}
          </span>
        </button>
        <button
          v-if="loading"
          type="button"
          class="secondary-btn"
          @click="emit('cancel')"
        >
          取消找实习
        </button>
      </div>
    </form>

    <section v-if="savedJobItems.length" class="saved-jobs-home">
      <div>
        <h2>已保存岗位</h2>
        <p class="muted">{{ savedApplicationCount }} 个岗位正在跟踪</p>
      </div>
      <button
        type="button"
        class="secondary-btn compact-btn"
        @click="emit('open-saved-applications')"
      >
        查看清单
      </button>
    </section>

    <p v-if="error" class="error-chip">
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path
          d="M10 3.2c-.3 0-.6.2-.8.5L3.4 15c-.4.7.1 1.6.8 1.6h11.6c.7 0 1.2-.9.8-1.6L10.8 3.7c-.2-.3-.5-.5-.8-.5Zm0 4.3c.4 0 .7.3.7.7v4c0 .4-.3.7-.7.7s-.7-.3-.7-.7V8.2c0-.4.3-.7.7-.7Zm0 6.6a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"
        />
      </svg>
      {{ error }}
    </p>
    <p v-else-if="loading" class="hint muted">
      正在收集岗位、JD 和投递渠道线索，实时进展见右侧区域。
    </p>
  </section>
</template>

<script setup lang="ts">
import type {
  InternshipExample,
  JobItemView,
  ResearchFormState
} from "../types/research";

defineProps<{
  error: string;
  form: ResearchFormState;
  internshipExamples: InternshipExample[];
  loading: boolean;
  savedApplicationCount: number;
  savedJobItems: JobItemView[];
  searchOptions: string[];
}>();

const emit = defineEmits<{
  cancel: [];
  "fill-example": [text: string];
  "open-saved-applications": [];
  submit: [];
}>();
</script>

<style scoped>
.panel-form {
  max-width: 420px;
}

.panel-centered {
  width: 100%;
  max-width: 600px;
  padding: 40px;
  box-shadow: 0 32px 64px rgba(15, 23, 42, 0.15);
  transform: scale(1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.panel-centered:hover {
  transform: scale(1.02);
  box-shadow: 0 40px 80px rgba(15, 23, 42, 0.2);
}

.panel-form h1 {
  margin: 0;
  font-size: 26px;
  letter-spacing: 0.01em;
}

.panel-form p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.logo {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.4);
}

.logo svg {
  width: 28px;
  height: 28px;
  fill: #f8fafc;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field span {
  font-weight: 600;
  color: #475569;
}

.example-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-chip {
  border: 1px solid rgba(59, 130, 246, 0.28);
  background: rgba(219, 234, 254, 0.45);
  color: #1e40af;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.example-chip:hover:not(:disabled) {
  background: rgba(191, 219, 254, 0.72);
  border-color: rgba(37, 99, 235, 0.45);
  transform: translateY(-1px);
}

.example-chip:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.options {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.option {
  flex: 1;
  min-width: 140px;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.submit {
  align-self: flex-start;
  padding: 12px 24px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

.submit-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.submit .spinner {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: rgba(255, 255, 255, 0.85);
  stroke-linecap: round;
  animation: spin 1s linear infinite;
}

.submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.submit:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
}

.saved-jobs-home {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.78);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.saved-jobs-home h2 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #1f2937;
}

.error-chip {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 14px;
  color: #b91c1c;
  font-size: 14px;
}

.error-chip svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.hint.muted {
  color: #64748b;
}

@media (max-width: 600px) {
  .options {
    flex-direction: column;
  }

  .panel-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-form h1 {
    font-size: 24px;
  }
}
</style>
