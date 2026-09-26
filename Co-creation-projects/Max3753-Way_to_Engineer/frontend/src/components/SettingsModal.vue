<template>
  <div class="modal-overlay" v-if="visible" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>LLM 配置</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group" :class="{ 'has-error': fieldErrors.base_url }">
          <label>API Base URL</label>
          <input
            v-model="form.base_url"
            type="text"
            placeholder="https://api.deepseek.com/v1"
            class="form-input"
          />
          <span class="field-error" v-if="fieldErrors.base_url">{{ fieldErrors.base_url }}</span>
          <span class="field-hint" v-else>例如 https://api.deepseek.com/v1</span>
        </div>
        <div class="form-group" :class="{ 'has-error': fieldErrors.model_id }">
          <label>Model ID</label>
          <input
            v-model="form.model_id"
            type="text"
            placeholder="deepseek-chat"
            class="form-input"
          />
          <span class="field-error" v-if="fieldErrors.model_id">{{ fieldErrors.model_id }}</span>
        </div>
        <div class="form-group" :class="{ 'has-error': fieldErrors.api_key }">
          <label>API Key</label>
          <input
            v-model="form.api_key"
            type="password"
            placeholder="sk-xxxxxxxxxxxxxxxx"
            class="form-input"
          />
          <span class="field-error" v-if="fieldErrors.api_key">{{ fieldErrors.api_key }}</span>
          <span class="field-hint" v-else>必填，修改后将替换现有密钥</span>
        </div>
        <div v-if="message" :class="['message', messageType]">{{ message }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn-reset" @click="resetToDefaults">恢复默认</button>
        <div class="footer-right">
          <button class="btn-cancel" @click="$emit('close')">取消</button>
          <button class="btn-save" @click="save" :disabled="saving">
            {{ saving ? '保存中...' : '保存并应用' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import axios from 'axios'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const form = reactive({
  base_url: '',
  model_id: '',
  api_key: '',
})
const fieldErrors = reactive({
  base_url: '',
  model_id: '',
  api_key: '',
})
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

function clearFieldErrors() {
  fieldErrors.base_url = ''
  fieldErrors.model_id = ''
  fieldErrors.api_key = ''
}

function validateForm(): boolean {
  clearFieldErrors()
  let valid = true

  if (!form.base_url.trim()) {
    fieldErrors.base_url = 'Base URL 不能为空'
    valid = false
  } else if (!/^https?:\/\/.+/.test(form.base_url.trim())) {
    fieldErrors.base_url = '请输入有效的 URL（以 http:// 或 https:// 开头）'
    valid = false
  }

  if (!form.model_id.trim()) {
    fieldErrors.model_id = 'Model ID 不能为空'
    valid = false
  }

  if (!form.api_key.trim()) {
    fieldErrors.api_key = 'API Key 不能为空'
    valid = false
  }

  return valid
}

// 打开时加载当前配置
watch(() => props.visible, async (show) => {
  if (!show) return
  message.value = ''
  clearFieldErrors()
  try {
    const res = await axios.get('/api/settings/llm')
    form.base_url = res.data.base_url
    form.model_id = res.data.model_id
    form.api_key = ''  // 不回显密钥，让用户重新输入
  } catch {
    message.value = '获取当前配置失败'
    messageType.value = 'error'
  }
})

const save = async () => {
  if (!validateForm()) {
    message.value = '请修正标红的字段后重试'
    messageType.value = 'error'
    return
  }

  saving.value = true
  message.value = ''

  try {
    const res = await axios.post('/api/settings/llm', {
      base_url: form.base_url.trim(),
      model_id: form.model_id.trim(),
      api_key: form.api_key.trim(),
    })
    if (res.data.success) {
      message.value = '✅ 配置已更新并生效'
      messageType.value = 'success'
    } else {
      message.value = '❌ ' + res.data.message
      messageType.value = 'error'
    }
  } catch (err: any) {
    message.value = '❌ 保存失败: ' + (err.response?.data?.detail || err.message)
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

const resetToDefaults = async () => {
  saving.value = true
  message.value = ''
  clearFieldErrors()

  try {
    const res = await axios.post('/api/settings/llm/reset')
    if (res.data.success) {
      // 刷新表单显示默认值
      form.base_url = res.data.config.base_url
      form.model_id = res.data.config.model_id
      form.api_key = ''
      message.value = '✅ 已恢复为 .env 默认配置'
      messageType.value = 'success'
    } else {
      message.value = '❌ ' + res.data.message
      messageType.value = 'error'
    }
  } catch (err: any) {
    message.value = '❌ 重置失败: ' + (err.response?.data?.detail || err.message)
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 480px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

[data-theme="dark"] .modal-content {
  background: #2d2d2d;
  color: #e0e0e0;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0 4px;
  line-height: 1;
}

.close-btn:hover {
  color: #333;
}

[data-theme="dark"] .close-btn:hover {
  color: #fff;
}

.modal-body {
  padding: 20px 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group.has-error label {
  color: #cf1322;
}

[data-theme="dark"] .form-group.has-error label {
  color: #f48771;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #555;
}

[data-theme="dark"] .form-group label {
  color: #aaa;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.15);
}

.has-error .form-input {
  border-color: #ff4d4f;
}

.has-error .form-input:focus {
  border-color: #ff4d4f;
  box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.15);
}

[data-theme="dark"] .has-error .form-input {
  border-color: #f48771;
}

[data-theme="dark"] .form-input {
  background: #3c3c3c;
  border-color: #555;
  color: #e0e0e0;
}

[data-theme="dark"] .form-input:focus {
  border-color: #667eea;
}

.field-error {
  display: block;
  font-size: 12px;
  color: #ff4d4f;
  margin-top: 4px;
}

.field-hint {
  display: block;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.message {
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 14px;
  margin-top: 8px;
}

.message.success {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #389e0d;
}

.message.error {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #cf1322;
}

[data-theme="dark"] .message.success {
  background: #1a3a1a;
  border-color: #2d7d2d;
  color: #8dd0a8;
}

[data-theme="dark"] .message.error {
  background: #3a1a1a;
  border-color: #7d2d2d;
  color: #f48771;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px 20px;
}

.footer-right {
  display: flex;
  gap: 8px;
}

.btn-reset {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  background: transparent;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #999;
  transition: all 0.2s;
}

.btn-reset:hover {
  border-color: #ff4d4f;
  color: #ff4d4f;
}

[data-theme="dark"] .btn-reset {
  border-color: #555;
  color: #888;
}

[data-theme="dark"] .btn-reset:hover {
  border-color: #f48771;
  color: #f48771;
}

.btn-cancel {
  padding: 8px 20px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

[data-theme="dark"] .btn-cancel {
  background: #3c3c3c;
  border-color: #555;
  color: #e0e0e0;
}

.btn-save {
  padding: 8px 20px;
  border: none;
  background: #667eea;
  color: #fff;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-save:hover:not(:disabled) {
  background: #5a6fd6;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
