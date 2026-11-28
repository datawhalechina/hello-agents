<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from './api'

const route = useRoute()
const serviceStatus = ref('检查中')
const today = new Date().toLocaleDateString('zh-CN')

const activeMenu = computed(() => route.path)

onMounted(async () => {
  try {
    const health = await api.health()
    serviceStatus.value = `${health.llm_provider} / ${health.llm_model}`
  } catch (error) {
    serviceStatus.value = '后端未连接'
    ElMessage.warning(`无法连接后端服务：${error.message}`)
  }
})
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <strong>Wellness Assistant</strong>
        <span>个人健康管理智能体</span>
      </div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/chat">健康对话</el-menu-item>
        <el-menu-item index="/dashboard">指标趋势</el-menu-item>
        <el-menu-item index="/plan">运动计划</el-menu-item>
        <el-menu-item index="/trace">Agent 链路</el-menu-item>
      </el-menu>
      <div class="service">
        <span class="muted">服务状态</span>
        <div>{{ serviceStatus }}</div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span>{{ route.meta.title || '健康对话' }}</span>
        <span class="muted">{{ today }}</span>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer class="footer">
        本项目仅作健康辅助用途，不具备医疗诊断能力，输出内容不能替代专业医师诊疗。
      </el-footer>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}

.aside {
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.brand {
  padding: 22px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.brand span {
  font-size: 12px;
  color: #6b7280;
}

.service {
  margin-top: auto;
  padding: 16px;
  font-size: 13px;
  border-top: 1px solid #e5e7eb;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 600;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9a3412;
  font-size: 12px;
  background: #fff7ed;
}
</style>
