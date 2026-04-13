<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Card, List, Input, Button, message, Empty, Tag, Modal, Checkbox } from 'ant-design-vue'
import { configApi, type ConfigFile } from '@/api/config'
import { SaveOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons-vue'

const router = useRouter()

const configs = ref<string[]>([])
const selectedConfig = ref<ConfigFile | null>(null)
const editingContent = ref('')
const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const showResetModal = ref(false)
const resetOptions = ref({
  reset_sessions: true,
  reset_memory: true,
  reset_global_config: false,
})

const configDescriptions: Record<string, string> = {
  CONFIG: '全局配置',
  IDENTITY: '身份定义',
  USER: '用户信息',
  SOUL: '人格模板',
  MEMORY: '长期记忆',
  AGENTS: '工作空间规则',
  HEARTBEAT: '心跳任务',
  BOOTSTRAP: '初始化引导',
}

// 获取配置文件的后缀
const getConfigExtension = (name: string): string => {
  return name === 'CONFIG' ? '.json' : '.md'
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await configApi.list()
    configs.value = res.configs
  } catch (error) {
    message.error('加载配置列表失败')
  } finally {
    loading.value = false
  }
}

const selectConfig = async (name: string) => {
  try {
    const res = await configApi.get(name)
    selectedConfig.value = res
    editingContent.value = res.content
  } catch (error) {
    message.error('加载配置失败')
  }
}

const saveConfig = async () => {
  if (!selectedConfig.value) return

  saving.value = true
  try {
    await configApi.update(selectedConfig.value.name, editingContent.value)
    message.success('保存成功')
  } catch (error: any) {
    // 透传后端错误信息
    const errorMsg = error?.response?.data?.detail || error?.message || '保存失败'
    message.error(errorMsg)
  } finally {
    saving.value = false
  }
}

const confirmReset = () => {
  // 重置选项为默认值
  resetOptions.value = {
    reset_sessions: true,
    reset_memory: true,
    reset_global_config: false,
  }
  showResetModal.value = true
}

const handleReset = async () => {
  resetting.value = true
  try {
    const res = await configApi.reset(resetOptions.value)
    message.success(res.message)
    showResetModal.value = false
    selectedConfig.value = null
    editingContent.value = ''

    // 如果清除了会话历史，也要清除 localStorage 中的上次会话 ID
    if (resetOptions.value.reset_sessions) {
      localStorage.removeItem('helloclaw.lastSessionId')
    }

    await loadConfigs()

    // 导航到聊天页面并传递刷新参数，让 ChatView 重新获取 agent 信息
    router.push({ name: 'chat', query: { refresh: Date.now().toString() } })
  } catch (error) {
    message.error('重置失败')
  } finally {
    resetting.value = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<template>
  <div class="config-view">
    <div class="config-header">
      <h1>配置管理</h1>
      <p>管理 Agent 的配置文件和身份信息</p>
    </div>

    <div class="config-content">
      <!-- 配置列表 -->
      <div class="config-list">
        <Card :loading="loading" class="list-card">
          <template #title>
            <FileTextOutlined /> 配置文件
          </template>
          <template #extra>
            <button
              class="reset-btn"
              @click="confirmReset"
              title="重置为初始模板"
            >
              <ReloadOutlined /> 初始化
            </button>
          </template>
          <List :data-source="configs" :locale="{ emptyText: '暂无配置文件' }">
            <template #renderItem="{ item }">
              <List.Item
                @click="selectConfig(item)"
                :class="['config-item', { active: selectedConfig?.name === item }]"
              >
                <div class="config-item-content">
                  <span class="config-name">{{ item }}</span>
                  <Tag color="error" v-if="configDescriptions[item]">
                    {{ configDescriptions[item] }}
                  </Tag>
                </div>
              </List.Item>
            </template>
          </List>
        </Card>
      </div>

      <!-- 编辑区域 -->
      <div class="config-editor">
        <Card v-if="selectedConfig" class="editor-card">
          <template #title>
            <span>{{ selectedConfig.name }}</span>
            <Tag color="green" style="margin-left: 8px">{{ getConfigExtension(selectedConfig.name) }}</Tag>
          </template>
          <template #extra>
            <Button
              type="primary"
              :loading="saving"
              @click="saveConfig"
            >
              <SaveOutlined /> 保存
            </Button>
          </template>
          <Input.TextArea
            v-model:value="editingContent"
            :auto-size="{ minRows: 18, maxRows: 30 }"
            class="editor-textarea"
          />
        </Card>

        <Card v-else class="empty-card">
          <Empty
            description="请从左侧选择一个配置文件"
            :image-style="{ height: '80px' }"
          />
        </Card>
      </div>
    </div>

    <!-- 重置确认弹窗 -->
    <Modal
      v-model:open="showResetModal"
      title="确认初始化"
      :confirm-loading="resetting"
      @ok="handleReset"
      okText="确认初始化"
      cancelText="取消"
      okType="danger"
    >
      <div class="reset-warning">
        <p style="color: #ff4d4f; font-weight: 500;">⚠️ 警告：此操作不可撤销！</p>
        <p>初始化将把所有配置文件恢复为默认模板，包括：</p>
        <ul>
          <li>AGENTS.md - 工作空间规则</li>
          <li>IDENTITY.md - 身份信息</li>
          <li>USER.md - 用户信息</li>
          <li>SOUL.md - 人格模板</li>
          <li>MEMORY.md - 长期记忆</li>
          <li>HEARTBEAT.md - 心跳任务</li>
          <li>BOOTSTRAP.md - 初始化引导</li>
        </ul>

        <div class="reset-options">
          <p style="font-weight: 500; margin-bottom: 8px;">额外清除选项：</p>
          <Checkbox v-model:checked="resetOptions.reset_sessions">
            清除所有会话历史
          </Checkbox>
          <Checkbox v-model:checked="resetOptions.reset_memory">
            清除每日记忆文件
          </Checkbox>
          <Checkbox v-model:checked="resetOptions.reset_global_config">
            重置全局配置（LLM、Agent 设置等）
          </Checkbox>
        </div>

        <p style="margin-top: 16px;">您确定要继续吗？</p>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
.config-view {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-sizing: border-box;
}

.config-header {
  flex-shrink: 0;
  margin-bottom: 24px;
}

.config-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 500;
}

.config-header p {
  margin: 0;
  color: #999;
}

.config-content {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.config-list {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-card :deep(.ant-card-body) {
  flex: 1;
  padding: 0;
  overflow-y: auto;
}

.config-item {
  cursor: pointer;
  padding: 12px 16px;
  transition: all 0.2s;
  border-bottom: 1px solid #f0f0f0;
}

.config-item:hover {
  background-color: #f5f5f5;
}

.config-item.active {
  background-color: #fff1f0;
  border-left: 3px solid #ff4d4f;
}

.config-item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-name {
  font-weight: 500;
}

.config-editor {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.editor-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-card :deep(.ant-card-head) {
  flex-shrink: 0;
}

.editor-card :deep(.ant-card-body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
}

.empty-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 初始化按钮 - 纯红色背景 + 白色字体（可操作） */
.reset-btn {
  padding: 4px 12px;
  font-size: 13px;
  border: none;
  border-radius: 6px;
  background: #ff4d4f;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.reset-btn:hover {
  background: #ff7875;
}

.reset-warning {
  padding: 8px 0;
}

.reset-warning ul {
  margin: 12px 0;
  padding-left: 24px;
}

.reset-warning li {
  margin: 4px 0;
  color: #666;
}

.reset-options {
  margin-top: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
