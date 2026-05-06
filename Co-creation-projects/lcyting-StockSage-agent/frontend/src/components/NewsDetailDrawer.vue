<template>
  <el-drawer
    :model-value="modelValue"
    class="news-detail-drawer"
    direction="rtl"
    size="min(560px, 94vw)"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
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
        <!-- 使用 window.open：部分 exe/宿主环境对 target=_blank 的 <a> 拦截，导致「无法查看原文」 -->
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

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** 与后端 /news 返回的 item 结构一致 */
  item: { type: Object, default: null },
})

defineEmits(['update:modelValue'])

const hasBody = computed(() => {
  const c = props.item?.content
  return typeof c === 'string' && c.trim().length > 0
})

function openOriginalUrl() {
  const u = props.item?.url
  if (typeof u !== 'string' || !u.trim()) return
  const url = u.trim()
  try {
    const w = window.open(url, '_blank', 'noopener,noreferrer')
    if (!w) {
      ElMessage.warning('无法打开新窗口：请检查浏览器是否拦截弹出窗口，或复制链接到地址栏打开')
    }
  } catch {
    ElMessage.error('打开原文链接失败')
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
