<template>
  <div class="my-trips-container">
    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
      <div class="decoration-circle circle-3"></div>
    </div>

    <!-- 头部 -->
    <div class="header-section">
      <h1>📋 我的行程</h1>
      <p>管理和查看您的历史行程规划</p>
    </div>

    <!-- 行程列表 -->
    <div class="trips-content" v-if="tripsList.length > 0">
      <el-row :gutter="24">
        <el-col 
          :xs="24" 
          :sm="12" 
          :md="8" 
          :lg="6" 
          v-for="(trip, index) in tripsList" 
          :key="trip.id"
        >
          <el-card class="trip-card" shadow="hover" @click="viewTrip(index)">
            <div class="trip-card-header">
              <div class="trip-destination">
                <span class="destination-icon">🌍</span>
                <h3>{{ trip.trip_title }}</h3>
              </div>
              <div class="trip-badge">第 {{ index + 1 }} 次行程</div>
            </div>
            
            <div class="trip-info">
              <div class="info-item">
                <el-icon><Calendar /></el-icon>
                <span>{{ trip.days.length }}天{{ trip.days.length - 1 }}晚</span>
              </div>
              <div class="info-item">
                <el-icon><Wallet /></el-icon>
                <span>预算：¥{{ trip.total_budget.total }}</span>
              </div>
              <div class="info-item">
                <el-icon><Clock /></el-icon>
                <span>{{ formatDate(trip.created_at) }}</span>
              </div>
            </div>

            <div class="trip-preview">
              <div class="preview-tags">
                <el-tag 
                  v-for="day in trip.days.slice(0, 3)" 
                  :key="day.day" 
                  size="small" 
                  type="info"
                >
                  Day {{ day.day }}: {{ day.theme }}
                </el-tag>
                <el-tag v-if="trip.days.length > 3" size="small" type="info">
                  +{{ trip.days.length - 3 }}
                </el-tag>
              </div>
            </div>

            <div class="trip-actions">
              <el-button type="primary" size="small" @click.stop="viewTrip(index)">
                <el-icon><View /></el-icon>
                查看详情
              </el-button>
              <el-button 
                type="success" 
                size="small" 
                @click.stop="editTrip(index)"
              >
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button 
                type="danger" 
                size="small" 
                @click.stop="deleteTrip(index)"
              >
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 -->
    <el-empty 
      v-else 
      description="暂无行程记录"
      class="empty-state"
    >
      <el-button type="primary" @click="createNewTrip">
        <el-icon><Plus /></el-icon>
        开始新的行程规划
      </el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Calendar,
  Wallet,
  Clock,
  View,
  Edit,
  Delete,
  Plus
} from '@element-plus/icons-vue'
import type { TripPlanResponse } from '@/types'
import { tripApi } from '@/services/api'

const router = useRouter()
const tripsList = ref<Array<{ id: string; trip_title: string; created_at: string } & TripPlanResponse>>([])
const loading = ref(false)

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return '未知时间'
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  
  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// 加载行程列表
const loadTrips = async () => {
  loading.value = true
  try {
    // 优先从后端API获取行程列表
    const trips = await tripApi.getTripsList()
    tripsList.value = trips
    
    // 同步到localStorage作为缓存
    localStorage.setItem('myTrips', JSON.stringify(trips))
  } catch (error) {
    console.error('从后端API加载失败，使用本地缓存:', error)
    
    // 降级：使用localStorage缓存的数据
    try {
      const savedTrips = localStorage.getItem('myTrips')
      if (savedTrips) {
        tripsList.value = JSON.parse(savedTrips)
        ElMessage.warning('网络异常，已加载本地缓存数据')
      }
    } catch (err) {
      console.error('加载行程列表失败:', err)
      ElMessage.error('加载行程列表失败')
    }
  } finally {
    loading.value = false
  }
}

// 查看行程
const viewTrip = async (index: number) => {
  const trip = tripsList.value[index]
  
  // 如果有trip.id，尝试从后端获取完整数据
  if (trip.id) {
    try {
      const fullTrip = await tripApi.getTripDetail(trip.id)
      
      // 保存到sessionStorage
      sessionStorage.setItem('currentTripPlan', JSON.stringify(fullTrip))
      
      // 跳转到结果页面
      router.push({
        name: 'Result',
        state: { tripPlan: fullTrip }
      })
      return
    } catch (error) {
      console.error('从后端获取行程详情失败，使用本地数据:', error)
      ElMessage.warning('获取详情失败，使用本地数据')
    }
  }
  
  // 降级：使用本地已有数据
  sessionStorage.setItem('currentTripPlan', JSON.stringify(trip))
  router.push({
    name: 'Result',
    state: { tripPlan: trip }
  })
}

// 编辑行程
const editTrip = (index: number) => {
  const trip = tripsList.value[index]
  router.push({
    name: 'EditPlan',
    state: { tripPlan: trip }
  })
}

// 删除行程
const deleteTrip = async (index: number) => {
  try {
    const trip = tripsList.value[index]
    
    await ElMessageBox.confirm(
      '确定要删除这个行程吗？此操作不可恢复。',
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 如果有trip.id，从后端删除
    if (trip.id) {
      try {
        await tripApi.deleteTrip(trip.id)
        ElMessage.success('行程已删除')
      } catch (error) {
        console.error('从后端删除行程失败:', error)
        ElMessage.error('删除失败，请重试')
        return
      }
    } else {
      // 没有id的情况，只删除本地缓存
      ElMessage.success('行程已删除（仅本地）')
    }
    
    // 从本地列表中移除
    tripsList.value.splice(index, 1)
    
    // 更新localStorage缓存
    saveTrips()
  } catch {
    // 用户取消
  }
}

// 保存行程列表
const saveTrips = () => {
  try {
    localStorage.setItem('myTrips', JSON.stringify(tripsList.value))
  } catch (error) {
    console.error('保存行程列表失败:', error)
  }
}

// 创建新行程
const createNewTrip = () => {
  router.push({ name: 'Home' })
}

onMounted(() => {
  loadTrips()
})
</script>

<style scoped lang="scss">
.my-trips-container {
  position: relative;
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;

  // 背景装饰
  .background-decoration {
    position: absolute;
    width: 100%;
    height: 100%;
    overflow: hidden;
    pointer-events: none;

    .decoration-circle {
      position: absolute;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      animation: float 20s infinite;

      &.circle-1 {
        width: 300px;
        height: 300px;
        top: -150px;
        left: -150px;
        animation-delay: 0s;
      }

      &.circle-2 {
        width: 200px;
        height: 200px;
        top: 50%;
        right: -100px;
        animation-delay: 5s;
      }

      &.circle-3 {
        width: 400px;
        height: 400px;
        bottom: -200px;
        left: 30%;
        animation-delay: 10s;
      }
    }
  }

  // 头部
  .header-section {
    position: relative;
    text-align: center;
    color: white;
    margin-bottom: 40px;
    z-index: 1;
    animation: fadeInDown 0.8s ease;

    h1 {
      margin: 0 0 10px 0;
      font-size: 36px;
      font-weight: 700;
      text-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    p {
      margin: 0;
      font-size: 16px;
      opacity: 0.95;
    }
  }

  // 行程列表
  .trips-content {
    position: relative;
    max-width: 1400px;
    margin: 0 auto;
    z-index: 1;

    .trip-card {
      margin-bottom: 24px;
      border-radius: 16px;
      cursor: pointer;
      transition: all 0.3s ease;
      height: 100%;
      display: flex;
      flex-direction: column;

      &:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
      }

      .trip-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 16px;

        .trip-destination {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;

          .destination-icon {
            font-size: 24px;
          }

          h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #303133;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 200px;
          }
        }

        .trip-badge {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }
      }

      .trip-info {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 16px;

        .info-item {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #606266;
          font-size: 14px;

          .el-icon {
            color: #909399;
          }
        }
      }

      .trip-preview {
        margin-bottom: 16px;
        flex: 1;

        .preview-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
      }

      .trip-actions {
        display: flex;
        gap: 8px;
        margin-top: auto;

        .el-button {
          flex: 1;
        }
      }
    }
  }

  // 空状态
  .empty-state {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 24px;
    padding: 60px 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  }
}

// 动画
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

// 响应式
@media (max-width: 768px) {
  .my-trips-container {
    padding: 15px;

    .header-section h1 {
      font-size: 28px;
    }

    .trips-content {
      .trip-card {
        .trip-card-header .trip-destination h3 {
          max-width: 150px;
          font-size: 16px;
        }

        .trip-actions {
          flex-direction: column;
        }
      }
    }
  }
}
</style>