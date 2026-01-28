<template>
  <div class="budget-summary">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>💰 预算明细</h3>
          <div class="total-budget">
            <span>实际预算：</span>
            <span class="amount">¥{{ totalBudget.toFixed(2) }}</span>
          </div>
        </div>
      </template>

      <!-- 预算概览 -->
      <div class="budget-overview">
        <el-row :gutter="16">
          <el-col :span="6" v-for="category in budgetCategories" :key="category.name">
            <div class="category-card">
              <div class="category-icon">{{ category.icon }}</div>
              <div class="category-name">{{ category.name }}</div>
              <div class="category-amount">¥{{ category.amount.toFixed(2) }}</div>
              <div class="category-percent">{{ category.percent }}%</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 详细列表 -->
      <el-divider />
      
      <div class="budget-details">
        <el-collapse v-model="activeCollapse">
          <el-collapse-item
            v-for="detail in budgetDetails"
            :key="detail.category"
            :name="detail.category"
          >
            <template #title>
              <div class="collapse-title">
                <span class="title-text">{{ detail.category }}</span>
                <span class="title-amount">¥{{ detail.amount.toFixed(2) }}</span>
              </div>
            </template>
            
            <el-table :data="detail.items" :show-header="true" size="small">
              <el-table-column prop="name" label="项目" />
              <el-table-column prop="cost" label="费用" align="right">
                <template #default="scope">
                  ¥{{ scope.row.cost.toFixed(2) }}
                </template>
              </el-table-column>
            </el-table>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 预算建议 -->
      <el-alert
        v-if="budgetTip"
        :title="budgetTip"
        type="info"
        :closable="false"
        class="budget-tip"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { TripPlanResponse, BudgetDetail } from '@/types'

interface Props {
  tripPlan: TripPlanResponse
}

const props = defineProps<Props>()
const activeCollapse = ref<string[]>([])

// 辅助函数：从门票价格中提取数值
const extractPrice = (price: number | string): number => {
  if (typeof price === 'number') {
    return price
  }
  if (typeof price === 'string') {
    if (price === '免费' || price === '0元' || price === '无') {
      return 0
    }
    // 提取字符串中的数字（例如："60元" -> 60, "60 元/人" -> 60）
    const match = price.match(/(\d+(\.\d+)?)/)
    if (match) {
      return parseFloat(match[1])
    }
  }
  return 0
}

// 计算每日景点门票费用（基于实际景点的ticket_price）
const calculateDailyAttractionCost = (day: TripPlanResponse['days'][0]): BudgetDetail['items'] => {
  const items: BudgetDetail['items'] = []
  
  day.attractions.forEach((attraction, index) => {
    const price = extractPrice(attraction.ticket_price)
    if (price > 0) {
      items.push({
        name: attraction.name,
        cost: price
      })
    }
  })
  
  return items
}

// 计算每日餐饮费用（基于实际餐饮的cost_per_person）
const calculateDailyDiningCost = (day: TripPlanResponse['days'][0]): BudgetDetail['items'] => {
  const items: BudgetDetail['items'] = []
  
  day.dinings.forEach(dining => {
    const cost = extractPrice(dining.cost_per_person)
    if (cost > 0) {
      items.push({
        name: dining.name,
        cost: cost
      })
    }
  })
  
  return items
}

// 计算每日酒店费用（基于推荐酒店的价格）
const calculateDailyHotelCost = (day: TripPlanResponse['days'][0]): BudgetDetail['items'] => {
  const items: BudgetDetail['items'] = []
  
  if (day.recommended_hotel) {
    const price = extractPrice(day.recommended_hotel.price)
    if (price > 0) {
      items.push({
        name: day.recommended_hotel.name,
        cost: price
      })
    }
  }
  
  return items
}

// 计算每日交通费用（基于每天预算的transport_cost，因为没有更详细的数据）
const calculateDailyTransportCost = (day: TripPlanResponse['days'][0]): BudgetDetail['items'] => {
  // 交通费用没有详细的子项，只能使用天级预算
  if (day.budget.transport_cost > 0) {
    return [{
      name: `第 ${day.day} 天交通`,
      cost: day.budget.transport_cost
    }]
  }
  return []
}

// 计算真实的总预算（基于实际数据计算，不依赖后端的budget字段）
const totalBudget = computed(() => {
  const details = calculateBudgetDetails()
  return details.reduce((sum, detail) => sum + detail.amount, 0)
})

// 计算各类别预算（基于实际数据）
const budgetDetails = computed((): BudgetDetail[] => {
  return calculateBudgetDetails()
})

// 统一预算计算逻辑
const calculateBudgetDetails = (): BudgetDetail[] => {
  const details: BudgetDetail[] = []
  
  // 1. 景点门票费用
  const allAttractionItems: BudgetDetail['items'] = []
  let totalAttractionCost = 0
  
  props.tripPlan.days.forEach(day => {
    const dailyItems = calculateDailyAttractionCost(day)
    allAttractionItems.push(...dailyItems)
    totalAttractionCost += dailyItems.reduce((sum, item) => sum + item.cost, 0)
  })
  
  if (allAttractionItems.length > 0) {
    details.push({
      category: '景点门票',
      amount: totalAttractionCost,
      items: allAttractionItems
    })
  }
  
  // 2. 餐饮费用
  const allDiningItems: BudgetDetail['items'] = []
  let totalDiningCost = 0
  
  props.tripPlan.days.forEach(day => {
    const dailyItems = calculateDailyDiningCost(day)
    allDiningItems.push(...dailyItems)
    totalDiningCost += dailyItems.reduce((sum, item) => sum + item.cost, 0)
  })
  
  if (allDiningItems.length > 0) {
    details.push({
      category: '餐饮美食',
      amount: totalDiningCost,
      items: allDiningItems
    })
  }
  
  // 3. 酒店住宿费用
  const allHotelItems: BudgetDetail['items'] = []
  let totalHotelCost = 0
  
  props.tripPlan.days.forEach(day => {
    const dailyItems = calculateDailyHotelCost(day)
    allHotelItems.push(...dailyItems)
    totalHotelCost += dailyItems.reduce((sum, item) => sum + item.cost, 0)
  })
  
  if (allHotelItems.length > 0) {
    details.push({
      category: '酒店住宿',
      amount: totalHotelCost,
      items: allHotelItems
    })
  }
  
  // 4. 交通费用
  const allTransportItems: BudgetDetail['items'] = []
  let totalTransportCost = 0
  
  props.tripPlan.days.forEach(day => {
    const dailyItems = calculateDailyTransportCost(day)
    allTransportItems.push(...dailyItems)
    totalTransportCost += dailyItems.reduce((sum, item) => sum + item.cost, 0)
  })
  
  if (allTransportItems.length > 0) {
    details.push({
      category: '交通费用',
      amount: totalTransportCost,
      items: allTransportItems
    })
  }
  
  return details
}

// 计算预算分类概览
const budgetCategories = computed(() => {
  const categories = [
    { name: '景点', icon: '🎫', key: '景点门票' },
    { name: '餐饮', icon: '🍽️', key: '餐饮美食' },
    { name: '住宿', icon: '🏨', key: '酒店住宿' },
    { name: '交通', icon: '🚗', key: '交通费用' }
  ]
  
  return categories.map(cat => {
    const detail = budgetDetails.value.find(d => d.category === cat.key)
    const amount = detail?.amount || 0
    const percent = totalBudget.value > 0 
      ? Math.round((amount / totalBudget.value) * 100) 
      : 0
    
    return {
      name: cat.name,
      icon: cat.icon,
      amount,
      percent
    }
  })
})

// 预算建议
const budgetTip = computed(() => {
  if (totalBudget.value < 500) {
    return '💡 经济出行，建议选择公共交通和经济型酒店'
  } else if (totalBudget.value < 2000) {
    return '💡 中等预算，可以体验当地特色美食和舒适住宿'
  } else if (totalBudget.value < 5000) {
    return '💡 宽裕预算，可以享受更好的服务和体验'
  } else {
    return '💡 豪华出行，尽情享受高品质的旅行体验'
  }
})
</script>

<style scoped lang="scss">
.budget-summary {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    h3 {
      margin: 0;
      font-size: 20px;
      color: #303133;
    }

    .total-budget {
      font-size: 14px;
      color: #606266;

      .amount {
        font-size: 24px;
        font-weight: bold;
        color: #f56c6c;
        margin-left: 8px;
      }
    }
  }

  .budget-overview {
    margin: 20px 0;

    .category-card {
      text-align: center;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;
      transition: all 0.3s;

      &:hover {
        background: #ecf5ff;
        transform: translateY(-2px);
      }

      .category-icon {
        font-size: 32px;
        margin-bottom: 8px;
      }

      .category-name {
        font-size: 14px;
        color: #606266;
        margin-bottom: 8px;
      }

      .category-amount {
        font-size: 18px;
        font-weight: bold;
        color: #303133;
        margin-bottom: 4px;
      }

      .category-percent {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  .budget-details {
    .collapse-title {
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-right: 20px;

      .title-text {
        font-weight: 500;
      }

      .title-amount {
        font-weight: bold;
        color: #f56c6c;
      }
    }
  }

  .budget-tip {
    margin-top: 20px;
  }
}
</style>
