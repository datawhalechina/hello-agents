<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">🚀</div>
        <h1>Way_to_Engineer</h1>
        <p>{{ langStore.t('login.subtitle') }}</p>
      </div>
      <div class="login-form">
        <label class="input-label">{{ langStore.t('login.label') }}</label>
        <input
          v-model="username"
          type="text"
          class="username-input"
          :class="{ 'input-error': errorMsg }"
          :placeholder="langStore.t('login.placeholder')"
          @keydown.enter="handleLogin"
          @input="errorMsg = ''"
          autofocus
        />
        <p v-if="errorMsg" class="error-text">{{ errorMsg }}</p>
        <button
          class="login-btn"
          @click="handleLogin"
          :disabled="!username.trim() || checking"
        >
          <span v-if="!checking">{{ langStore.t('login.btn') }}</span>
          <span v-else class="spinner"></span>
        </button>
      </div>
      <div class="login-footer">
        <p>{{ langStore.t('login.footer') }}</p>
      </div>
    </div>

    <!-- 重名确认对话框 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showConfirm" class="confirm-overlay" @click.self="cancelConfirm">
          <div class="confirm-dialog">
            <div class="confirm-icon">⚠️</div>
            <h3>用户名已被使用</h3>
            <p>用户 <strong>{{ confirmUsername }}</strong> 已有学习记录。</p>
            <p class="confirm-desc">继续使用将加载该用户的学习进度，确定吗？</p>
            <div class="confirm-actions">
              <button class="btn btn-cancel" @click="cancelConfirm">换一个用户名</button>
              <button class="btn btn-confirm" @click="confirmLogin">继续使用</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { useLangStore } from '../stores/langStore'

const router = useRouter()
const authStore = useAuthStore()
const langStore = useLangStore()
const username = ref('')
const errorMsg = ref('')
const checking = ref(false)
const showConfirm = ref(false)
const confirmUsername = ref('')

const handleLogin = async () => {
  const trimmed = username.value.trim()
  if (!trimmed) return

  checking.value = true
  errorMsg.value = ''

  try {
    // 检查用户名是否已存在
    const checkRes = await axios.post('/api/auth/check', { username: trimmed })
    const { exists, has_data } = checkRes.data

    if (exists && has_data) {
      // 用户名已存在且有学习数据 → 需要用户确认
      confirmUsername.value = trimmed
      showConfirm.value = true
      checking.value = false
      return
    }

    // 新用户 或 存在但无数据 → 直接登录
    await doLogin(trimmed)
  } catch (error: any) {
    errorMsg.value = error.response?.data?.detail || '登录失败，请重试'
    checking.value = false
  }
}

const doLogin = async (name: string) => {
  try {
    const res = await axios.post('/api/auth/login', { username: name })
    authStore.login(name)
    router.push('/')
  } catch (error: any) {
    errorMsg.value = error.response?.data?.detail || '登录失败，请重试'
  } finally {
    checking.value = false
  }
}

const confirmLogin = () => {
  showConfirm.value = false
  doLogin(confirmUsername.value)
}

const cancelConfirm = () => {
  showConfirm.value = false
  confirmUsername.value = ''
  checking.value = false
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: white;
  border-radius: 20px;
  padding: 48px 40px;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.logo-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.login-header h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
}

.login-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.username-input {
  padding: 14px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  font-size: 16px;
  transition: all 0.2s;
  outline: none;
}

.username-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.input-error {
  border-color: #ff4d4f;
}

.input-error:focus {
  border-color: #ff4d4f;
  box-shadow: 0 0 0 4px rgba(255, 77, 79, 0.1);
}

.error-text {
  margin: 0;
  font-size: 13px;
  color: #ff4d4f;
}

.login-btn {
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  margin-top: 24px;
  text-align: center;
}

.login-footer p {
  margin: 0;
  font-size: 12px;
  color: #999;
}

/* 确认对话框 */
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.confirm-dialog {
  background: white;
  border-radius: 20px;
  padding: 36px 32px;
  width: 380px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.confirm-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.confirm-dialog h3 {
  margin: 0 0 12px 0;
  font-size: 20px;
  color: #1a1a1a;
}

.confirm-dialog p {
  margin: 0 0 6px 0;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

.confirm-desc {
  margin-bottom: 24px !important;
  color: #999 !important;
  font-size: 13px !important;
}

.confirm-actions {
  display: flex;
  gap: 12px;
}

.btn {
  flex: 1;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-cancel {
  background: #f0f2f5;
  color: #666;
}

.btn-cancel:hover {
  background: #e8e8e8;
}

.btn-confirm {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
