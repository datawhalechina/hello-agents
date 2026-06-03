<template>
  <div class="login-container">
    <a-card class="login-card" :title="isRegister ? '注册' : '登录'">
      <template #extra>
        <a-button type="link" @click="isRegister = !isRegister">
          {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
        </a-button>
      </template>

      <a-form :model="form" :rules="rules" layout="vertical" @finish="handleSubmit">
        <a-form-item label="用户名" name="username">
          <a-input v-model:value="form.username" placeholder="请输入用户名" size="large" />
        </a-form-item>

        <a-form-item label="密码" name="password">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" size="large" />
        </a-form-item>

        <a-form-item v-if="isRegister" label="确认密码" name="confirmPassword">
          <a-input-password v-model:value="form.confirmPassword" placeholder="请再次输入密码" size="large" />
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block size="large">
            {{ isRegister ? '注册' : '登录' }}
          </a-button>
        </a-form-item>
      </a-form>

      <div v-if="error" class="error-msg">{{ error }}</div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

const router = useRouter()
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_: any, value: string) => {
        if (isRegister.value && value !== form.password) {
          return Promise.reject('两次密码不一致')
        }
        return Promise.resolve()
      },
      trigger: 'blur'
    }
  ],
}

async function handleSubmit() {
  if (isRegister.value && form.password !== form.confirmPassword) {
    error.value = '两次密码不一致'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const endpoint = isRegister.value ? 'register' : 'login'
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'https://localhost:8000'
    const res = await fetch(`${baseUrl}/api/auth/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // 让 cookie 可被设置
      body: JSON.stringify({ username: form.username, password: form.password }),
    })
    const data = await res.json()

    if (!res.ok) {
      error.value = data.detail || '操作失败'
      return
    }

    // 保存登录用户名（前端显示用，不影响认证）
    localStorage.setItem('auth_username', data.username)

    message.success(isRegister.value ? '注册成功' : '登录成功')

    // 跳转到首页（带上登录标记）
    router.push('/')
  } catch (e: any) {
    error.value = '网络错误，请检查后端是否启动'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
.login-card {
  width: 420px;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
}
.error-msg {
  color: #ff4d4f;
  text-align: center;
  margin-top: 8px;
}
</style>
