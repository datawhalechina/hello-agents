<template>
  <!-- 根元素：页面自上而下的组件树。v-loading 是 Element 的指令式加载遮罩 -->
  <div class="page" v-loading="loading" element-loading-text="⏳ 正在测试中，请稍候（含 LLM 生成用例）">
    <!-- 页头 -->
    <div class="page-header">
      <h1>🤖 智能API测试助手</h1>
      <p>粘贴一份 OpenAPI 文档，自动完成「解析 → 生成用例 → 执行测试 → 验证 → 统计」</p>
    </div>

    <!-- ① 表单：loading 传给子组件做按钮转圈；用 @submit 接住子组件 emit 出来的数据 -->
    <ApiTestForm :loading="loading" @submit="handleRun" />

    <!-- ② 错误提示：error 非空才渲染；@close 处理右上角关闭按钮 -->
    <el-alert
      v-if="error"
      class="error-alert"
      :title="error"
      type="error"
      show-icon
      closable
      @close="error = ''"
    />

    <!-- ③ 有结果才渲染结果区 -->
    <template v-if="summary">
      <ResultSummary :summary="summary" />
      <ResultTable :results="results" />
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import ApiTestForm from './components/ApiTestForm.vue'
import ResultSummary from './components/ResultSummary.vue'
import ResultTable from './components/ResultTable.vue'

import { runApiTest } from './api/test'

// ===== 页面级状态：所有"跨组件共享的数据"由父组件统一持有 =====
const loading = ref(false) // 是否正在测试（控制按钮转圈 + 全屏遮罩）
const error = ref('')      // 错误信息字符串（空串=无错误）
const summary = ref(null)  // 统计结果 { total, passed, failed, pass_rate }
const results = ref([])    // 逐条用例结果

/**
 * 表单组件点了"开始测试"并校验通过后，会把 payload emit 到这里。
 * 父组件在此真正发起请求，并负责更新页面状态。
 */
async function handleRun(payload) {
  loading.value = true // 开始：开遮罩
  error.value = ''     // 清掉上次的错误
  summary.value = null // 收起旧的测试结果，避免"旧结果 + 新请求中"的混乱
  results.value = []

  try {
    const data = await runApiTest(payload) // 调 API 层函数（拦截器已剥壳）
    summary.value = data.summary
    results.value = data.results ?? []

    // 成功弹一个轻提示
    ElMessage.success(`测试完成：共 ${summary.value.total} 条，通过率 ${summary.value.pass_rate}%`)
  } catch (e) {
    error.value = e.message || '测试执行失败' // 拦截器已经帮我们把后端 detail 放进 e.message
  } finally {
    loading.value = false // 无论成败，最后都关遮罩（finally 一定会执行）
  }
}
</script>

<style scoped>
.page-header {
  text-align: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 26px;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.error-alert {
  margin-bottom: 20px;
}

/* 结果区的卡片之间留点空隙 */
.page :deep(.el-card) {
  margin-bottom: 20px;
}
</style>
