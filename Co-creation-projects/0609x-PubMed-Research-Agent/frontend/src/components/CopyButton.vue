<template>
  <el-button size="small" text type="primary" @click="copy">
    <el-icon style="margin-right: 4px"><DocumentCopy /></el-icon>
    {{ copied ? '已复制' : '复制' }}
  </el-button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'

const props = defineProps<{ text: string }>()
const copied = ref(false)

async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.text)
    copied.value = true
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}
</script>
