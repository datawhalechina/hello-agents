<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>① 输入 API 信息</span>
      </div>
    </template>

    <!-- ref="formRef"：拿到 el-form 的实例，后面才能调用 validate() 做整体校验 -->
    <!-- :model 绑定表单数据对象；:rules 绑定校验规则；label-position="top" 让标签显示在输入框上方 -->
    <!-- @submit.prevent：阻止浏览器原生表单提交（否则在单行输入框按回车会刷新页面） -->
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
      <el-form-item label="OpenAPI 文档来源">
        <el-radio-group v-model="mode" :disabled="loading">
          <el-radio-button value="text">粘贴文档</el-radio-button>
          <el-radio-button value="url">URL 抓取</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="mode === 'text'" label="OpenAPI 文档（粘贴 yaml/json）" prop="openapiText">
        <el-input
          v-model="form.openapiText"
          type="textarea"
          :rows="10"
          placeholder="在此粘贴 OpenAPI 文档内容..."
        />
      </el-form-item>

      <el-form-item v-else label="OpenAPI 文档 URL" prop="openapiUrl">
        <el-input
          v-model="form.openapiUrl"
          type="url"
          placeholder="例如：https://httpbin.org/spec.json"
          clearable
          @keyup.enter="handleSubmit"
        />
        <div class="field-tip">后端将直接抓取 URL 内容，无需先下载文档</div>
      </el-form-item>

      <el-form-item label="目标 API 基础地址（base_url）" prop="baseUrl">
        <el-input
          v-model="form.baseUrl"
          placeholder="例如：https://jsonplaceholder.typicode.com"
          clearable
          @keyup.enter="handleSubmit"
        />
      </el-form-item>

      <el-form-item label="请求头（选填，JSON 格式）" prop="headers">
        <el-input
          v-model="form.headers"
          type="textarea"
          :rows="3"
          placeholder='例如：{"Authorization": "Bearer 你的token"}'
        />
        <div class="field-tip">受保护接口需要认证头，按 JSON 对象填写（留空则不发送）</div>
      </el-form-item>

      <div class="btn-row">
        <!-- :loading="loading"：父组件传进来的状态，请求期间按钮转圈并禁用 -->
        <el-button type="primary" size="large" :loading="loading" @click="handleSubmit">
          🚀 开始测试
        </el-button>
        <el-button size="large" :disabled="loading" @click="fillExample">📝 填入示例</el-button>
        <el-button size="large" :disabled="loading" @click="clearForm">🗑️ 清空</el-button>
      </div>
    </el-form>
  </el-card>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { EXAMPLE_DOC, EXAMPLE_BASE_URL } from '@/constants/exampleDoc'

// ===== 父组件传进来的 props（只读）=====
const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
})

// ===== 声明本组件能向外触发的事件 =====
// 组件里只能 emit 在 defineEmits 里声明过的事件，这层声明让代码自文档化
const emit = defineEmits(['submit'])

// formRef 绑定到模板里的 el-form；模板中用 ref="formRef"，这里用同名 ref 变量接收
const formRef = ref(null)
const mode = ref('text')

// reactive 创建响应式对象：输入框用 v-model 双向绑定到它
// （一个对象里有多个值、会被整体操作时，用 reactive 比多个 ref 更顺）
const form = reactive({
  openapiText: '',
  openapiUrl: '',
  baseUrl: '',
  headers: '',
})

// 请求头可选：留空跳过；非空必须是合法 JSON 对象
function validateHeaders(rule, value, callback) {
  if (!value || !value.trim()) return callback()
  try {
    const parsed = JSON.parse(value)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return callback(new Error('请求头必须是 JSON 对象，例如 {"Authorization": "Bearer xxx"}'))
    }
    return callback()
  } catch {
    return callback(new Error('请求头格式错误：不是合法的 JSON 对象'))
  }
}

// 校验规则：required 必填。trigger 表示何时触发校验
const rules = computed(() => ({
  openapiText: mode.value === 'text'
    ? [{ required: true, message: '请粘贴 OpenAPI 文档内容', trigger: 'blur' }]
    : [],
  openapiUrl: mode.value === 'url'
    ? [{ required: true, message: '请输入 OpenAPI 文档 URL', trigger: 'blur' }]
    : [],
  baseUrl: [{ required: true, message: '请填写目标 API 基础地址', trigger: 'blur' }],
  headers: [{ validator: validateHeaders, trigger: 'blur' }],
}))

// 填入示例：把示例文档和地址写进表单，并清掉红色校验提示
function fillExample() {
  mode.value = 'text'
  form.openapiText = EXAMPLE_DOC
  form.openapiUrl = ''
  form.baseUrl = EXAMPLE_BASE_URL
  form.headers = ''
  formRef.value?.clearValidate() // ?. 空值保护：ref 还没绑定时不会报错
}

function clearForm() {
  form.openapiText = ''
  form.openapiUrl = ''
  form.baseUrl = ''
  form.headers = ''
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  // validate() 校验整张表单；不通过会 reject（并自动标红），直接 return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  // 通过：把数据整理成后端要的字段名（下划线风格），emit 给父组件
  const payload = {
    base_url: form.baseUrl.trim(),
  }
  if (mode.value === 'url') {
    payload.openapi_url = form.openapiUrl.trim()
  } else {
    payload.openapi_text = form.openapiText.trim()
  }
  // 请求头是选填的 JSON 对象，非空才解析并带上
  if (form.headers.trim()) {
    payload.headers = JSON.parse(form.headers)
  }
  emit('submit', payload)
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
}

.btn-row {
  margin-top: 6px;
}

.field-tip {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}
</style>
