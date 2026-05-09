<template>
  <div class="simulation-page">
    <!-- 页面标题 + 模拟交易提示 -->
    <div class="page-header">
      <h2>模拟交易</h2>
      <el-alert
        title="模拟交易环境 — 所有交易均为虚拟操作，不涉及真实资金"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top:8px;"
      />
    </div>

    <!-- 账户概览卡片 -->
    <el-row :gutter="16" class="account-row">
      <el-col :span="6">
        <el-card shadow="hover" class="account-card">
          <div class="acct-label">总资产</div>
          <div class="acct-value">{{ formatMoney(balance.total_assets) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="account-card">
          <div class="acct-label">可用资金</div>
          <div class="acct-value blue">{{ formatMoney(balance.available_balance) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="account-card">
          <div class="acct-label">持仓市值</div>
          <div class="acct-value">{{ formatMoney(balance.market_value) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="account-card">
          <div class="acct-label">累计盈亏</div>
          <div :class="['acct-value', balance.total_profit_loss >= 0 ? 'up' : 'down']">
            {{ balance.total_profit_loss >= 0 ? '+' : '' }}{{ formatMoney(balance.total_profit_loss) }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作标签页 -->
    <el-card shadow="hover" class="main-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- Tab 1: 持仓管理 -->
        <el-tab-pane label="持仓管理" name="positions">
          <div v-loading="posLoading">
            <el-table
              v-if="positions.length > 0"
              :data="positions"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="stock_code" label="代码" width="100" />
              <el-table-column prop="stock_name" label="名称" width="120" />
              <el-table-column prop="quantity" label="持仓数量" width="100" />
              <el-table-column label="成本价" width="100">
                <template #default="{ row }">{{ formatMoney(row.cost_price) }}</template>
              </el-table-column>
              <el-table-column label="现价" width="100">
                <template #default="{ row }">{{ formatMoney(row.current_price) }}</template>
              </el-table-column>
              <el-table-column label="市值" width="120">
                <template #default="{ row }">{{ formatMoney(row.market_value) }}</template>
              </el-table-column>
              <el-table-column label="盈亏" width="130">
                <template #default="{ row }">
                  <span :class="row.profit_loss >= 0 ? 'text-up' : 'text-down'">
                    {{ row.profit_loss >= 0 ? '+' : '' }}{{ formatMoney(row.profit_loss) }}
                    ({{ row.profit_loss_rate >= 0 ? '+' : '' }}{{ row.profit_loss_rate }}%)
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    plain
                    @click="openSellDialog(row)"
                  >
                    卖出
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-empty
              v-else-if="!posLoading"
              description="暂无持仓"
              :image-size="80"
            >
              <el-button type="primary" @click="activeTab = 'order'">
                去下单
              </el-button>
            </el-empty>
          </div>

          <!-- 持仓收益图表 -->
          <div v-if="positions.length > 0" class="chart-section">
            <el-divider>持仓收益分布</el-divider>
            <v-chart :option="profitChartOption" autoresize style="height: 280px;" />
          </div>
        </el-tab-pane>

        <!-- Tab 2: 买卖下单 -->
        <el-tab-pane label="买卖下单" name="order">
          <el-row :gutter="24">
            <el-col :span="12">
              <el-card shadow="never" class="order-form-card">
                <template #header>
                  <span class="form-title">
                    <el-tag :type="orderForm.trade_type === 'buy' ? 'danger' : 'success'" size="large">
                      {{ orderForm.trade_type === 'buy' ? '买入' : '卖出' }}
                    </el-tag>
                  </span>
                </template>

                <el-form
                  :model="orderForm"
                  label-width="80px"
                  class="order-form"
                >
                  <el-form-item label="交易方向">
                    <el-radio-group v-model="orderForm.trade_type">
                      <el-radio-button value="buy">买入</el-radio-button>
                      <el-radio-button value="sell">卖出</el-radio-button>
                    </el-radio-group>
                  </el-form-item>

                  <el-form-item label="股票代码">
                    <el-input
                      v-model="orderForm.stock_code"
                      placeholder="6位代码，如 600519"
                      maxlength="6"
                    />
                  </el-form-item>

                  <el-form-item label="委托数量">
                    <el-input-number
                      v-model="orderForm.quantity"
                      :min="100"
                      :step="100"
                      :max="1000000"
                      placeholder="100的整数倍"
                      style="width:100%;"
                    />
                  </el-form-item>

                  <el-form-item label="委托价格">
                    <el-input-number
                      v-model="orderForm.price"
                      :min="0.01"
                      :step="0.01"
                      :precision="2"
                      placeholder="留空为市价委托"
                      style="width:100%;"
                    />
                    <el-text type="info" size="small" style="display:block;margin-top:4px;">
                      留空则按市价委托
                    </el-text>
                  </el-form-item>

                  <el-form-item>
                    <el-button
                      :type="orderForm.trade_type === 'buy' ? 'danger' : 'success'"
                      size="large"
                      @click="handlePlaceOrder"
                      :loading="orderSubmitting"
                      style="width:100%;"
                    >
                      {{ orderForm.trade_type === 'buy' ? '确认买入' : '确认卖出' }}
                    </el-button>
                  </el-form-item>
                </el-form>

                <!-- 下单预估 -->
                <el-alert
                  v-if="estimatedAmount > 0"
                  :title="orderForm.trade_type === 'buy' ? '预估买入金额' : '预估卖出收入'"
                  :description="`${formatMoney(estimatedAmount)} 元`"
                  type="info"
                  :closable="false"
                  show-icon
                />
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span class="form-title">下单说明</span>
                </template>
                <div class="order-help">
                  <el-text tag="p">买入：输入股票代码、数量和价格（可选），确认后提交委托。</el-text>
                  <el-text tag="p">卖出：选择持仓中的股票，输入卖出数量。</el-text>
                  <el-divider />
                  <el-text tag="p" type="info" size="small">
                    A股交易规则：买入最小单位100股（1手），数量需为100的整数倍。
                  </el-text>
                  <el-text tag="p" type="info" size="small">
                    市价委托：不指定价格，以当前市场最优价成交。
                  </el-text>
                  <el-text tag="p" type="info" size="small">
                    限价委托：指定价格，只有当市场价格达到指定价时才成交。
                  </el-text>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- Tab 3: 委托记录 -->
        <el-tab-pane label="委托记录" name="orders">
          <div v-loading="orderLoading">
            <div class="orders-header">
              <span v-if="orders.length > 0">
                共 {{ orders.length }} 条委托
              </span>
              <el-button
                v-if="orders.some(o => o.status === 'pending')"
                type="danger"
                size="small"
                @click="handleCancelAll"
                :loading="cancelAllLoading"
              >
                一键撤单
              </el-button>
            </div>

            <el-table
              v-if="orders.length > 0"
              :data="orders"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="order_id" label="委托编号" width="180" />
              <el-table-column prop="stock_code" label="代码" width="100" />
              <el-table-column prop="stock_name" label="名称" width="120" />
              <el-table-column label="方向" width="70">
                <template #default="{ row }">
                  <el-tag
                    :type="row.trade_type === 'buy' ? 'danger' : row.trade_type === 'sell' ? 'success' : 'info'"
                    size="small"
                  >
                    {{ row.trade_type === 'buy' ? '买入' : row.trade_type === 'sell' ? '卖出' : '—' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="价格" width="100">
                <template #default="{ row }">{{ formatMoney(row.price) }}</template>
              </el-table-column>
              <el-table-column prop="quantity" label="数量" width="80" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'done' ? 'success' : row.status === 'pending' ? 'warning' : 'info'"
                    size="small"
                  >
                    {{ row.status_text || statusMap[row.status] || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="create_time" label="时间" width="160" />
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.status === 'pending'"
                    type="danger"
                    link
                    size="small"
                    @click="handleCancelOrder(row)"
                  >
                    撤单
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-empty
              v-else-if="!orderLoading"
              description="暂无委托记录"
              :image-size="80"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 卖出弹窗 -->
    <el-dialog v-model="sellDialogVisible" title="卖出股票" width="400px">
      <div v-if="sellTarget">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="股票">{{ sellTarget.stock_name }}（{{ sellTarget.stock_code }}）</el-descriptions-item>
          <el-descriptions-item label="持仓">{{ sellTarget.quantity }} 股</el-descriptions-item>
          <el-descriptions-item label="现价">{{ formatMoney(sellTarget.current_price) }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-form label-width="80px">
          <el-form-item label="卖出数量">
            <el-input-number
              v-model="sellQuantity"
              :min="100"
              :step="100"
              :max="sellTarget.quantity"
              style="width:100%;"
            />
          </el-form-item>
          <el-form-item label="委托价格">
            <el-input-number
              v-model="sellPrice"
              :min="0.01"
              :step="0.01"
              :precision="2"
              placeholder="留空为市价"
              style="width:100%;"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="sellDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmSell" :loading="orderSubmitting">
          确认卖出
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default { name: 'Simulation' }
</script>

<script setup>
/**
 * 模拟交易页面
 *
 * 提供模拟组合持仓管理、买卖下单、委托记录查询、一键撤单功能。
 * 数据来源：后端 /api/v1/simulation
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// =========================================================================
// ECharts
// =========================================================================
import VChart from 'vue-echarts'

// =========================================================================
// 状态
// =========================================================================
const activeTab = ref('positions')
const posLoading = ref(false)
const orderLoading = ref(false)
const orderSubmitting = ref(false)
const cancelAllLoading = ref(false)

// 账户资金
const balance = reactive({
  total_assets: 0,
  available_balance: 0,
  frozen_balance: 0,
  market_value: 0,
  total_profit_loss: 0,
})

// 持仓
const positions = ref([])

// 委托记录
const orders = ref([])

// 下单表单
const orderForm = reactive({
  trade_type: 'buy',
  stock_code: '',
  quantity: 100,
  price: null,
})

// 卖出弹窗
const sellDialogVisible = ref(false)
const sellTarget = ref(null)
const sellQuantity = ref(100)
const sellPrice = ref(null)

// =========================================================================
// 常量
// =========================================================================
const statusMap = {
  'done': '已成交',
  'pending': '未成交',
  'canceled': '已撤销',
  'part_deal': '部分成交',
}

// =========================================================================
// 计算属性
// =========================================================================

/** 预估金额（下单时显示） */
const estimatedAmount = computed(() => {
  if (!orderForm.stock_code || orderForm.quantity <= 0) return 0
  if (orderForm.price) return orderForm.price * orderForm.quantity
  // 市价预估：简单提示
  return 0
})

/** 持仓收益图表 */
const profitChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
  },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: positions.value.map(p => p.stock_name || p.stock_code),
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: '盈亏',
      type: 'bar',
      data: positions.value.map(p => ({
        value: p.profit_loss,
        itemStyle: {
          color: p.profit_loss >= 0 ? '#f56c6c' : '#1ecd94',
        },
      })),
      label: {
        show: true,
        position: 'top',
        formatter: (p) => {
          const val = p.value
          return val >= 0 ? `+${val.toFixed(0)}` : val.toFixed(0)
        },
      },
    },
  ],
}))

// =========================================================================
// 工具函数
// =========================================================================
function formatMoney(val) {
  if (val === null || val === undefined) return '--'
  const num = Number(val)
  if (isNaN(num)) return '--'
  // 大数用万为单位
  if (Math.abs(num) >= 10000) {
    return (num / 10000).toFixed(2) + '万'
  }
  return num.toFixed(2)
}

// =========================================================================
// 数据加载
// =========================================================================

/** 加载账户资金 */
async function loadBalance() {
  try {
    const res = await api.get('/simulation/funds')
    if (res.code === 0 && res.data) {
      Object.assign(balance, res.data)
    }
  } catch (e) {
    console.error('加载账户资金失败:', e)
  }
}

/** 加载持仓 */
async function loadPositions() {
  posLoading.value = true
  try {
    const res = await api.get('/simulation/portfolio')
    if (res.code === 0 && res.data) {
      positions.value = res.data.positions || []
    }
  } catch (e) {
    console.error('加载持仓失败:', e)
  } finally {
    posLoading.value = false
  }
}

/** 加载委托记录 */
async function loadOrders() {
  orderLoading.value = true
  try {
    const res = await api.get('/simulation/orders')
    if (res.code === 0 && res.data) {
      orders.value = res.data.orders || []
    }
  } catch (e) {
    console.error('加载委托记录失败:', e)
  } finally {
    orderLoading.value = false
  }
}

/** 刷新全部数据 */
async function refreshAll() {
  await Promise.all([loadBalance(), loadPositions(), loadOrders()])
}

// =========================================================================
// 下单操作
// =========================================================================

/** 提交买卖委托 */
async function handlePlaceOrder() {
  if (!orderForm.stock_code || orderForm.stock_code.length < 6) {
    ElMessage.warning('请输入有效的6位股票代码')
    return
  }
  if (orderForm.quantity < 100 || orderForm.quantity % 100 !== 0) {
    ElMessage.warning('委托数量必须为100的整数倍')
    return
  }

  const tradeLabel = orderForm.trade_type === 'buy' ? '买入' : '卖出'
  const priceText = orderForm.price ? `${orderForm.price} 元` : '市价委托'
  try {
    await ElMessageBox.confirm(
      `确认以${priceText}${tradeLabel} ${orderForm.stock_code}，数量 ${orderForm.quantity} 股？`,
      `确认${tradeLabel}`,
      { confirmButtonText: `确认${tradeLabel}`, cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  orderSubmitting.value = true
  try {
    const res = await api.post('/simulation/order', {
      trade_type: orderForm.trade_type,
      stock_code: orderForm.stock_code,
      quantity: orderForm.quantity,
      price: orderForm.price || undefined,
    })
    if (res.code === 0) {
      ElMessage.success(res.message || '委托提交成功')
      // 重置表单
      orderForm.stock_code = ''
      orderForm.quantity = 100
      orderForm.price = null
      // 刷新数据
      refreshAll()
    } else {
      ElMessage.error(res.message || '下单失败')
    }
  } catch (e) {
    ElMessage.error('下单请求失败: ' + (e.message || '未知错误'))
  } finally {
    orderSubmitting.value = false
  }
}

/** 打开卖出弹窗 */
function openSellDialog(row) {
  sellTarget.value = row
  sellQuantity.value = row.quantity
  sellPrice.value = null
  sellDialogVisible.value = true
}

/** 确认卖出 */
async function confirmSell() {
  if (sellQuantity.value < 100 || sellQuantity.value % 100 !== 0) {
    ElMessage.warning('卖出数量必须为100的整数倍')
    return
  }

  const priceText = sellPrice.value ? `${sellPrice.value} 元` : '市价委托'
  try {
    await ElMessageBox.confirm(
      `确认以${priceText}卖出 ${sellTarget.value.stock_name}(${sellTarget.value.stock_code})，数量 ${sellQuantity.value} 股？`,
      '确认卖出',
      { confirmButtonText: '确认卖出', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  orderSubmitting.value = true
  try {
    const res = await api.post('/simulation/order', {
      trade_type: 'sell',
      stock_code: sellTarget.value.stock_code,
      quantity: sellQuantity.value,
      price: sellPrice.value || undefined,
    })
    if (res.code === 0) {
      ElMessage.success(res.message || '卖出委托提交成功')
      sellDialogVisible.value = false
      refreshAll()
    } else {
      ElMessage.error(res.message || '卖出失败')
    }
  } catch (e) {
    ElMessage.error('卖出请求失败')
  } finally {
    orderSubmitting.value = false
  }
}

/** 撤单 */
async function handleCancelOrder(row) {
  try {
    await ElMessageBox.confirm(
      `确定撤销委托 ${row.order_id}？`,
      '撤单确认',
      { type: 'warning' }
    )
    const res = await api.delete(`/simulation/order/${row.order_id}`, {
      params: { stock_code: row.stock_code || '' },
    })
    if (res.code === 0) {
      ElMessage.success(res.message || '撤单成功')
      refreshAll()
    } else {
      ElMessage.error(res.message || '撤单失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('撤单失败')
    }
  }
}

/** 一键撤单 */
async function handleCancelAll() {
  try {
    await ElMessageBox.confirm(
      '确定撤销所有未成交的委托订单？',
      '一键撤单',
      { type: 'warning' }
    )
    cancelAllLoading.value = true
    const res = await api.post('/simulation/cancel-all')
    if (res.code === 0) {
      ElMessage.success(res.message || '一键撤单完成')
      refreshAll()
    } else {
      ElMessage.error(res.message || '一键撤单失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('撤单失败')
    }
  } finally {
    cancelAllLoading.value = false
  }
}

// =========================================================================
// 标签切换
// =========================================================================
function handleTabChange(tab) {
  if (tab === 'positions') {
    loadPositions()
  } else if (tab === 'orders') {
    loadOrders()
  }
}

// =========================================================================
// 生命周期
// =========================================================================
onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.simulation-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
}

/* 账户卡片 */
.account-row {
  margin-bottom: 16px;
}
.account-card {
  text-align: center;
}
.account-card :deep(.el-card__body) {
  padding: 16px 12px;
}
.acct-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.acct-value {
  font-size: 22px;
  font-weight: 700;
  font-family: 'DIN', 'Helvetica Neue', monospace;
  color: #303133;
}
.acct-value.blue {
  color: #409EFF;
}
.acct-value.up {
  color: #f56c6c;
}
.acct-value.down {
  color: #1ecd94;
}

/* 颜色 */
.text-up { color: #f56c6c; font-weight: 600; }
.text-down { color: #1ecd94; font-weight: 600; }

/* 主卡片 */
.main-card {
  min-height: 400px;
}

/* 图表区 */
.chart-section {
  margin-top: 8px;
}

/* 下单表单 */
.order-form-card {
  background: #fafafa;
}
.form-title {
  font-size: 15px;
  font-weight: 600;
}
.order-form {
  margin-top: 8px;
}
.order-help p {
  margin: 6px 0;
  font-size: 13px;
  line-height: 1.6;
}

/* 委托记录 */
.orders-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
}
</style>
