<template>
  <el-drawer
    v-model="drawerVisible"
    class="news-detail-drawer"
    direction="rtl"
    size="min(560px, 94vw)"
    destroy-on-close
    append-to-body
  >
    <template #header>
      <div class="drawer-header-text">{{ item?.title || '资讯详情' }}</div>
    </template>

    <div v-if="item" class="detail-inner">
      <div class="meta-bar">
        <el-tag
          size="small"
          :type="item.info_type_cn === '研报' ? 'warning' : item.info_type_cn === '公告' ? '' : 'success'"
          effect="plain"
        >
          {{ item.info_type_cn || item.info_type || '资讯' }}
        </el-tag>
        <span v-if="item.date" class="meta-piece">{{ item.date }}</span>
        <span v-if="item.institution" class="meta-piece">{{ item.institution }}</span>
        <span v-if="item.entity_name" class="meta-piece">{{ item.entity_name }}</span>
        <el-tag v-if="item.rating" size="small" type="warning">{{ item.rating }}</el-tag>
      </div>

      <el-alert
        v-if="!hasBody && !item.url"
        title="暂无正文摘要"
        type="info"
        :closable="false"
        show-icon
        class="mb-3"
      />
      <el-alert
        v-else-if="!hasBody && item.url"
        title="暂无摘要，可点击下方按钮查看原文"
        type="warning"
        :closable="false"
        show-icon
        class="mb-3"
      />

      <el-scrollbar v-if="hasBody" max-height="calc(100vh - 220px)">
        <!-- 纯文本展示，避免 v-html 注入风险 -->
        <div class="body-text">{{ item.content }}</div>
      </el-scrollbar>

      <div v-if="item.url" class="link-row">
        <!-- 优先 window.open；若被拦截则由后端 webbrowser.open 唤起系统浏览器（见 openOriginalUrl） -->
        <el-button type="primary" class="open-original-btn" @click="openOriginalUrl">
          在浏览器中打开原文
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script>
export default { name: 'NewsDetailDrawer' }
</script>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** 与后端 /news 返回的 item 结构一致 */
  item: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])

/** 与 HistoryDrawer 一致：正确转发 update:modelValue，避免关闭后父级未同步 */
const drawerVisible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const hasBody = computed(() => {
  const c = props.item?.content
  return typeof c === 'string' && c.trim().length > 0
})

async function openOriginalUrl() {
  const u = props.item?.url
  if (typeof u !== 'string' || !u.trim()) return
  const url = u.trim()
  try {
    const w = window.open(url, '_blank', 'noopener,noreferrer')
    if (w) return
  } catch {
    /* 继续走后端唤起浏览器 */
  }
  try {
    const res = await api.post('/system/open-external-url', { url }, { skipRetry: true })
    if (res.code === 0 && res.data?.opened) {
      ElMessage.success('已在系统默认浏览器中打开原文')
      return
    }
    if (res.code === 0 && !res.data?.opened) {
      ElMessage.warning('系统未能唤起浏览器，正在复制链接…')
    } else {
      ElMessage.warning(res.message || '打开原文失败')
    }
  } catch {
    ElMessage.warning('请求打开浏览器失败，正在复制链接…')
  }
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.info('链接已复制到剪贴板，请粘贴到浏览器地址栏打开')
  } catch {
    ElMessage.error('打开原文失败，请手动复制链接')
  }
}
</script>

<style scoped>
.drawer-header-text {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  line-height: 1.45;
  padding-right: 8px;
}
.detail-inner {
  padding: 0 4px 16px;
}
.meta-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.meta-piece {
  font-size: 12px;
  color: #909399;
}
.mb-3 {
  margin-bottom: 12px;
}
.body-text {
  font-size: 14px;
  line-height: 1.75;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
  padding-right: 8px;
}
.link-row {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
.open-original-btn {
  width: 100%;
}
</style>

<style>
/* 抽屉标题区与内容区略微收紧 */
.news-detail-drawer .el-drawer__body {
  padding-top: 8px;
}
</style>
