<template>
  <div class="auth-wrapper">
    <a-card :bordered="false" class="auth-card">
      <div class="auth-header">
        <div class="auth-title">登录</div>
        <div class="auth-subtitle">欢迎回来，请登录您的账户</div>
      </div>
      
      <a-alert
        v-if="authStore.error"
        :message="authStore.error"
        type="error"
        show-icon
        closable
        style="margin-bottom: 24px"
        @close="authStore.error = null"
      />

      <a-form
        layout="vertical"
        :model="formState"
        @finish="onFinish"
        hide-required-mark
        class="auth-form"
      >
        <a-form-item
          name="username"
          :rules="[{ required: true, message: '请输入用户名' }]"
        >
          <a-input
            v-model:value="formState.username"
            size="large"
            placeholder="用户名"
          >
            <template #prefix>
              <user-outlined style="color: rgba(0,0,0,.25)" />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item
          name="password"
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <a-input-password
            v-model:value="formState.password"
            size="large"
            placeholder="密码"
          >
            <template #prefix>
              <lock-outlined style="color: rgba(0,0,0,.25)" />
            </template>
          </a-input-password>
        </a-form-item>

        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            block
            :loading="authStore.loading"
            class="submit-btn"
          >
            登录
          </a-button>
        </a-form-item>

        <div class="auth-footer">
          <span>还没有账号？</span>
          <router-link to="/auth/register" class="link-btn">立即注册</router-link>
        </div>

        <div class="disclaimer">
          <a-divider style="margin: 16px 0; font-size: 12px; color: #999;">风险声明</a-divider>
          <p>
            <warning-outlined /> 本系统生成的 AI 角色发言可能包含错误、误导性信息或虚构内容，不代表真实人物观点。
            本平台内容仅供学术研究与娱乐演示，请勿作为专业建议。用户需自行甄别信息真伪，使用本服务产生的风险与后果由用户自行承担。
          </p>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { UserOutlined, LockOutlined, WarningOutlined } from '@ant-design/icons-vue'

const authStore = useAuthStore()
const formState = reactive({
  username: '',
  password: ''
})

const onFinish = async (values: any) => {
  await authStore.login(values)
}
</script>

<style scoped>
.auth-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  padding: 24px;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-title {
  font-size: 24px;
  color: rgba(0, 0, 0, 0.85);
  font-weight: 600;
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.45);
}

.auth-form {
  margin-bottom: 0;
}

.submit-btn {
  height: 40px;
  font-size: 16px;
  margin-top: 8px;
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  margin-top: 16px;
  color: rgba(0, 0, 0, 0.45);
}

.link-btn {
  color: #1890ff;
  font-weight: 500;
  margin-left: 4px;
}

.link-btn:hover {
  text-decoration: underline;
}

.disclaimer {
  margin-top: 24px;
  font-size: 12px;
  color: #999;
  text-align: center;
  line-height: 1.5;
}

.disclaimer p {
  margin: 0;
}

@media (max-width: 576px) {
  .auth-card {
    box-shadow: none;
    padding: 0;
    background: transparent;
  }
}
</style>
