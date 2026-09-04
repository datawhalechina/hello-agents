<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>③ 用例明细</span>
        <!-- 筛选器：全部 / 只看通过 / 只看失败，v-model 绑到本地响应式变量 filter -->
        <el-radio-group v-model="filter" size="small">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="passed">通过</el-radio-button>
          <el-radio-button value="failed">失败</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <!-- :data 是表格数据源；:row-class-name 给每行动态加类（按通过/失败上底色） -->
    <el-table
      :data="filteredRows"
      border
      :row-class-name="rowClassName"
      empty-text="暂无用例数据"
    >
      <!-- type="expand" 列：点击行首的 + 号展开，default 插槽里收到当前行 row -->
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail">
            <div class="detail-item">
              <span class="detail-label">请求</span>
              <code class="detail-code">{{ row.method }} {{ row.path }}</code>
            </div>

            <el-row :gutter="12">
              <el-col :span="12">
                <div class="detail-item">
                  <span class="detail-label">查询参数 (params)</span>
                  <pre class="detail-pre">{{ row.paramsText }}</pre>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="detail-item">
                  <span class="detail-label">请求体 (body)</span>
                  <pre class="detail-pre">{{ row.bodyText }}</pre>
                </div>
              </el-col>
            </el-row>

            <div v-if="row.errors.length" class="detail-item">
              <span class="detail-label">错误信息</span>
              <ul class="error-list">
                <li v-for="(msg, i) in row.errors" :key="i">{{ msg }}</li>
              </ul>
            </div>

            <div class="detail-item">
              <span class="detail-label">响应体 (response)</span>
              <pre class="detail-pre">{{ row.responseBodyText }}</pre>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="method" label="方法" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="methodTag(row.method)" size="small" effect="plain">
            {{ row.method }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="用例名称" min-width="180" show-overflow-tooltip />

      <el-table-column prop="caseType" label="类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="caseTypeTag(row.caseType)" size="small">
            {{ caseTypeText(row.caseType) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="期望状态" width="100" align="center">
        <template #default="{ row }">{{ row.expectedStatus }}</template>
      </el-table-column>

      <el-table-column label="实际状态" width="100" align="center">
        <template #default="{ row }">{{ row.statusCode }}</template>
      </el-table-column>

      <el-table-column prop="elapsed" label="耗时(秒)" width="110" align="center" />

      <el-table-column label="结果" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
            {{ row.passed ? '✅ 通过' : '❌ 失败' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { computed, ref } from 'vue'
import { CASE_TYPE_LABELS, CASE_TYPE_TAGS, METHOD_TAGS } from '@/constants/exampleDoc'
import { display, prettyJson } from '@/utils/format'

// props：父组件把后端返回的 results 数组传进来
const props = defineProps({
  results: {
    type: Array,
    required: true,
  },
})

// 本地状态：表格筛选（全部/通过/失败），只影响本组件展示
const filter = ref('all')

/**
 * rows：把后端"嵌套且可能缺失"的原始数据，改造成模板好用的扁平行对象。
 * 好处：① 模板干净；② 空值兜底只写一次；③ 文案/展示字段集中在这里算好
 */
const rows = computed(() => {
  const results = props.results ?? []
  return results.map((item, index) => {
    const caseObj = item.case ?? {}      // 防御：万一 case 缺失
    const result = item.result ?? {}     // 防御：请求失败时 result 可能字段缺失
    const errors = item.errors ?? []
    return {
      id: index,
      passed: !!item.passed,
      name: caseObj.name || '-',
      method: caseObj.method || '-',
      path: caseObj.path || '-',
      caseType: caseObj.case_type || '-',
      expectedStatus: display(caseObj.expected_status),
      statusCode: display(result.status_code),
      elapsed: display(result.elapsed),
      errors,
      paramsText: prettyJson(caseObj.params),
      bodyText: prettyJson(caseObj.body),
      responseBodyText: prettyJson(result.body),
    }
  })
})

// 按 filter 筛选后的行：computed 依赖 rows 与 filter，任一变化自动重算
const filteredRows = computed(() => {
  if (filter.value === 'all') return rows.value
  const wantPass = filter.value === 'passed'
  return rows.value.filter((row) => row.passed === wantPass)
})

// 行底色类名：失败的整行淡红，方便扫一眼定位问题
function rowClassName({ row }) {
  return row.passed ? '' : 'row-fail'
}

// 查表翻译：类型英文 → 中文；METHOD_TAGS / CASE_TYPE_TAGS 查不到就灰色兜底
function methodTag(method) {
  return METHOD_TAGS[method] || 'info'
}
function caseTypeText(type) {
  return CASE_TYPE_LABELS[type] || type
}
function caseTypeTag(type) {
  return CASE_TYPE_TAGS[type] || 'info'
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 16px;
}

.detail {
  padding: 4px 16px;
  line-height: 1.6;
}

.detail-item {
  margin-bottom: 10px;
}

.detail-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.detail-code {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 13px;
}

.detail-pre {
  margin: 0;
  background: #282c34;
  color: #abb2bf;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.error-list {
  margin: 0;
  padding-left: 18px;
  color: #f56c6c;
}

/* rowClassName 加在 el-table 内部的 <tr> 上，属于 Element 内部组件作用域，
   本组件 scoped 样式够不着，必须用 :deep() 穿透 */
:deep(.row-fail td) {
  background-color: #fdf0f0;
}
</style>
