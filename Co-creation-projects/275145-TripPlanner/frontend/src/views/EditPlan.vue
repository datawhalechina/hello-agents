<template>
  <div class="edit-plan-container" v-if="editablePlan">
    <!-- 头部操作栏 -->
    <el-card class="header-card">
      <div class="header-content">
        <h2>✏️ 编辑行程</h2>
        <div class="actions">
          <el-button @click="goBack">取消</el-button>
          <el-button type="primary" @click="saveAndPreview">保存并预览</el-button>
        </div>
      </div>
    </el-card>

    <!-- 编辑内容 -->
    <el-row :gutter="20" class="edit-content">
      <!-- 左侧：行程列表编辑 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="section-header">
              <h3>行程安排</h3>
              <el-button type="primary" size="small" @click="addDay">
                <el-icon><Plus /></el-icon>
                添加一天
              </el-button>
            </div>
          </template>

          <!-- 每日行程编辑 -->
          <el-collapse v-model="activeDay" accordion>
            <el-collapse-item
              v-for="(day, dayIndex) in editablePlan.days"
              :key="dayIndex"
              :name="dayIndex"
            >
              <template #title>
                <div class="day-title">
                  <span>第 {{ day.day }} 天 - {{ day.theme }}</span>
                  <el-button
                    type="danger"
                    size="small"
                    text
                    @click.stop="removeDay(dayIndex)"
                    v-if="editablePlan.days.length > 1"
                  >
                    删除
                  </el-button>
                </div>
              </template>

              <!-- 当日主题 -->
              <el-form-item label="当日主题">
                <el-input v-model="day.theme" placeholder="例如：探索古都文化" />
              </el-form-item>

              <!-- 景点列表 - 显示为卡片，支持拖拽排序 -->
              <div class="activities-section">
                <div class="section-header-small">
                  <h4>景点安排</h4>
                  <div class="section-actions">
                    <el-button size="small" @click="addAttraction(dayIndex)">
                      <el-icon><Plus /></el-icon>
                      添加景点
                    </el-button>
                  </div>
                </div>

                <div class="attraction-list">
                  <div
                    v-for="(attraction, attrIndex) in day.attractions"
                    :key="attrIndex"
                    class="attraction-card"
                    draggable="true"
                    @dragstart="handleDragStart($event, dayIndex, attrIndex)"
                    @dragover="handleDragOver($event)"
                    @drop="handleDrop($event, dayIndex, attrIndex)"
                    @dragend="handleDragEnd"
                  >
                    <el-card class="attraction-item-card">
                      <!-- 拖拽手柄 -->
                      <div class="drag-handle">
                        <el-icon><Rank /></el-icon>
                      </div>

                      <!-- 景点基本信息（只读） -->
                      <div class="attraction-info">
                        <h4>{{ attraction.name }}</h4>
                        <p class="attraction-desc">{{ attraction.description }}</p>
                        <div class="attraction-tags">
                          <el-tag size="small" type="info">
                            {{ attraction.type }}
                          </el-tag>
                          <el-tag size="small" v-if="attraction.suggested_duration_hours">
                            {{ attraction.suggested_duration_hours }}小时
                          </el-tag>
                        </div>
                        <p class="attraction-address">
                          <el-icon><Location /></el-icon>
                          {{ attraction.address }}
                        </p>
                      </div>

                      <!-- 操作按钮 -->
                      <div class="attraction-actions">
                        <el-button
                          type="danger"
                          size="small"
                          @click="removeAttraction(dayIndex, attrIndex)"
                        >
                          <el-icon><Delete /></el-icon>
                          删除
                        </el-button>
                      </div>

                      <!-- 用户备注和实际花费 -->
                      <el-divider>个性化设置</el-divider>
                      <div class="personal-settings">
                        <el-form-item label="我的备注" size="small">
                          <el-input
                            v-model="attraction.notes"
                            type="textarea"
                            :rows="2"
                            placeholder="添加您的个人备注、游玩心得等"
                          />
                        </el-form-item>
                        <el-form-item label="实际花费（元）" size="small">
                          <el-input-number
                            v-model="attraction.actual_cost"
                            :min="0"
                            :precision="2"
                            style="width: 100%"
                            placeholder="记录实际花费"
                          />
                        </el-form-item>
                      </div>
                    </el-card>
                  </div>
                </div>
              </div>

              <!-- 餐饮列表 -->
              <div class="activities-section">
                <div class="section-header-small">
                  <h4>餐饮安排</h4>
                  <div class="section-actions">
                    <el-button size="small" @click="addDining(dayIndex)">
                      <el-icon><Plus /></el-icon>
                      添加餐厅
                    </el-button>
                  </div>
                </div>

                <div
                  v-for="(dining, dineIndex) in day.dinings"
                  :key="dineIndex"
                  class="dining-item"
                >
                  <el-card>
                    <el-form label-width="80px" size="small">
                      <el-row :gutter="16">
                        <el-col :span="12">
                          <el-form-item label="名称">
                            <el-input v-model="dining.name" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="12">
                          <el-form-item label="人均">
                            <el-input-number
                              v-model="(dining.cost_per_person as any)"
                              :min="0"
                              :precision="2"
                              style="width: 100%"
                            />
                          </el-form-item>
                        </el-col>
                      </el-row>

                      <el-form-item label="地址">
                        <el-input v-model="dining.address" />
                      </el-form-item>

                      <el-form-item>
                        <el-button
                          type="danger"
                          size="small"
                          @click="removeDining(dayIndex, dineIndex)"
                        >
                          删除此餐厅
                        </el-button>
                      </el-form-item>
                    </el-form>
                  </el-card>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>

      <!-- 右侧：地图预览和酒店 -->
      <el-col :span="8">
        <!-- 地图预览 -->
        <el-card class="preview-card">
          <template #header>
            <h3>🗺️ 路线预览</h3>
          </template>
          <MapView :points="mapPoints" :center="mapCenter" />
        </el-card>

        <!-- 酒店信息（只读） -->
        <el-card class="hotels-edit-card">
          <template #header>
            <div class="section-header">
              <h3>🏨 酒店信息</h3>
              <el-tag type="info" size="small">只读模式</el-tag>
            </div>
          </template>

          <div v-for="(hotel, index) in editablePlan.hotels" :key="index" class="hotel-display-item">
            <div class="hotel-content">
              <h4>{{ hotel.name }}</h4>
              <p class="hotel-address">
                <el-icon><Location /></el-icon>
                {{ hotel.address }}
              </p>
              <div class="hotel-meta">
                <template v-if="typeof hotel.price === 'number' && hotel.price > 0">
                  <span class="hotel-price">¥{{ hotel.price.toFixed(2) }} / 晚</span>
                </template>
                <template v-else-if="hotel.price">
                  <span class="hotel-price">{{ hotel.price }}</span>
                </template>
              </div>
            </div>
            <el-divider v-if="index < editablePlan.hotels.length - 1" />
          </div>
        </el-card>

      </el-col>
    </el-row>
  </div>

  <el-empty v-else description="暂无可编辑的行程">
    <el-button type="primary" @click="goBack">返回首页</el-button>
  </el-empty>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Location, Rank, Delete, RefreshRight } from '@element-plus/icons-vue'
import MapView from '@/components/MapView.vue'
import type { TripPlanResponse, DailyPlan, Attraction, Dining, Hotel, MapPoint } from '@/types'

const router = useRouter()
const editablePlan = ref<TripPlanResponse | null>(null)
const activeDay = ref(0)

// 拖拽相关状态
const draggedPos = ref<{ dayIndex: number; attrIndex: number } | null>(null)

// 加载行程数据
onMounted(() => {
  const state = history.state as { tripPlan?: TripPlanResponse }
  if (state?.tripPlan) {
    // 深拷贝避免直接修改原数据
    editablePlan.value = JSON.parse(JSON.stringify(state.tripPlan))

    // 初始化备注和实际花费字段（如果不存在）
    editablePlan.value.days.forEach(day => {
      day.attractions.forEach(attraction => {
        attraction.notes = attraction.notes || ''
        attraction.actual_cost = attraction.actual_cost || undefined
      })
    })
  } else {
    const savedPlan = sessionStorage.getItem('currentTripPlan')
    if (savedPlan) {
      editablePlan.value = JSON.parse(savedPlan)

      // 初始化备注和实际花费字段
      editablePlan.value.days.forEach(day => {
        day.attractions.forEach(attraction => {
          attraction.notes = attraction.notes || ''
          attraction.actual_cost = attraction.actual_cost || undefined
        })
      })
    }
  }
})

// 地图点位（用于预览）
const mapPoints = computed<MapPoint[]>(() => {
  if (!editablePlan.value) return []

  const points: MapPoint[] = []

  editablePlan.value.days.forEach(day => {
    day.attractions.forEach(attraction => {
      if (attraction.location) {
        points.push({
          name: attraction.name,
          type: 'attraction',
          description: attraction.description,
          cost: typeof attraction.ticket_price === 'number' ? attraction.ticket_price : undefined,
          location: attraction.location
        })
      }
    })

    day.dinings.forEach(dining => {
      if (dining.location) {
        points.push({
          name: dining.name,
          type: 'dining',
          description: dining.address,
          cost: typeof dining.cost_per_person === 'number' ? dining.cost_per_person : undefined,
          location: dining.location
        })
      }
    })
  })

  editablePlan.value.hotels.forEach(hotel => {
    if (hotel.location) {
      points.push({
        name: hotel.name,
        type: 'hotel',
        description: hotel.address,
        cost: typeof hotel.price === 'number' ? hotel.price : undefined,
        location: hotel.location
      })
    }
  })

  return points
})

const mapCenter = computed(() => {
  const pts = mapPoints.value.filter(p => p.location)
  if (pts.length === 0) return undefined
  return pts[0].location
})

// 计算总预算
const totalBudget = computed(() => {
  if (!editablePlan.value) return 0

  if (
    editablePlan.value.total_budget &&
    typeof editablePlan.value.total_budget === 'object' &&
    typeof (editablePlan.value.total_budget as any).total === 'number'
  ) {
    return (editablePlan.value.total_budget as any).total
  }

  const daysTotal = editablePlan.value.days?.reduce((sum, day) => {
    const dayTotal = (day as any).budget?.total
    return sum + (typeof dayTotal === 'number' ? dayTotal : 0)
  }, 0) ?? 0

  return daysTotal
})

// 计算实际花费
const actualTotal = computed(() => {
  if (!editablePlan.value) return 0

  return editablePlan.value.days.reduce((sum, day) => {
    const attractionsCost = day.attractions.reduce((attrSum, attraction) => {
      return attrSum + (attraction.actual_cost || 0)
    }, 0)

    const diningsCost = day.dinings.reduce((diningSum, dining) => {
      return diningSum + (typeof dining.cost_per_person === 'number' ? dining.cost_per_person : 0)
    }, 0)

    return sum + attractionsCost + diningsCost
  }, 0)
})

// 添加一天
const addDay = () => {
  if (!editablePlan.value) return

  const newDay: DailyPlan = {
    day: editablePlan.value.days.length + 1,
    theme: '新的一天',
    attractions: [],
    dinings: [],
    budget: {
      transport_cost: 0,
      dining_cost: 0,
      hotel_cost: 0,
      attraction_ticket_cost: 0,
      total: 0
    }
  }

  editablePlan.value.days.push(newDay)
  ElMessage.success('已添加新的一天')
}

// 删除一天
const removeDay = (index: number) => {
  if (!editablePlan.value || editablePlan.value.days.length <= 1) return

  editablePlan.value.days.splice(index, 1)
  editablePlan.value.days.forEach((day, i) => {
    day.day = i + 1
  })

  ElMessage.success('已删除该天行程')
}

// 添加景点
const addAttraction = (dayIndex: number) => {
  if (!editablePlan.value) return

  const newAttraction: Attraction = {
    name: '新景点',
    type: 'attraction',
    rating: 'N/A',
    description: '',
    address: '',
    image_urls: [],
    ticket_price: 0,
    notes: '',
    actual_cost: undefined
  }

  editablePlan.value.days[dayIndex].attractions.push(newAttraction)
  ElMessage.success('已添加新景点')
}

// 删除景点
const removeAttraction = (dayIndex: number, attrIndex: number) => {
  if (!editablePlan.value) return

  editablePlan.value.days[dayIndex].attractions.splice(attrIndex, 1)
  ElMessage.success('已删除该景点')
}

// 替换景点（打开对话框）
const replaceAttraction = (dayIndex: number, attrIndex: number) => {
  ElMessage.info('替换功能开发中，请先删除再添加')
}

// 拖拽开始
const handleDragStart = (event: DragEvent, dayIndex: number, attrIndex: number) => {
  draggedPos.value = { dayIndex, attrIndex }
  event.dataTransfer!.effectAllowed = 'move'
  event.dataTransfer!.dropEffect = 'move'
}

// 拖拽经过
const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  event.dataTransfer!.dropEffect = 'move'
}

// 拖拽放下
const handleDrop = (event: DragEvent, targetDayIndex: number, targetAttrIndex: number) => {
  event.preventDefault()

  if (!draggedPos.value || !editablePlan.value) return

  const { dayIndex: sourceDayIndex, attrIndex: sourceAttrIndex } = draggedPos.value

  // 同一天内的景点排序
  if (sourceDayIndex === targetDayIndex && sourceAttrIndex !== targetAttrIndex) {
    const attractions = editablePlan.value.days[sourceDayIndex].attractions
    const [movedAttr] = attractions.splice(sourceAttrIndex, 1)
    attractions.splice(targetAttrIndex, 0, movedAttr)
    ElMessage.success('景点顺序已调整')
  } else if (sourceDayIndex !== targetDayIndex) {
    // 跨天移动景点
    const sourceAttractions = editablePlan.value.days[sourceDayIndex].attractions
    const targetAttractions = editablePlan.value.days[targetDayIndex].attractions
    const [movedAttr] = sourceAttractions.splice(sourceAttrIndex, 1)
    targetAttractions.splice(targetAttrIndex, 0, movedAttr)
    ElMessage.success('景点已移动到其他天')
  }

  draggedPos.value = null
}

// 拖拽结束
const handleDragEnd = () => {
  draggedPos.value = null
}

// 添加餐厅
const addDining = (dayIndex: number) => {
  if (!editablePlan.value) return

  const newDining: Dining = {
    name: '新餐厅',
    address: '',
    cost_per_person: 0,
    rating: 'N/A'
  }

  editablePlan.value.days[dayIndex].dinings.push(newDining)
  ElMessage.success('已添加新餐厅')
}

// 删除餐厅
const removeDining = (dayIndex: number, dineIndex: number) => {
  if (!editablePlan.value) return

  editablePlan.value.days[dayIndex].dinings.splice(dineIndex, 1)
  ElMessage.success('已删除该餐厅')
}

// 添加酒店
const addHotel = () => {
  if (!editablePlan.value) return

  const newHotel: Hotel = {
    name: '新酒店',
    address: '',
    price: 0,
    rating: 'N/A'
  }

  editablePlan.value.hotels.push(newHotel)
  ElMessage.success('已添加新酒店')
}

// 删除酒店
const removeHotel = (index: number) => {
  if (!editablePlan.value) return

  editablePlan.value.hotels.splice(index, 1)
  ElMessage.success('已删除该酒店')
}

// 返回
const goBack = () => {
  router.back()
}

// 保存并预览
const saveAndPreview = () => {
  if (!editablePlan.value) return

  if (
    editablePlan.value.total_budget &&
    typeof editablePlan.value.total_budget === 'object'
  ) {
    ;(editablePlan.value.total_budget as any).total = totalBudget.value
  }

  sessionStorage.setItem('currentTripPlan', JSON.stringify(editablePlan.value))

  ElMessage.success('保存成功！')

  router.push({
    name: 'Result',
    state: { tripPlan: editablePlan.value }
  })
}
</script>

<style scoped lang="scss">
.edit-plan-container {
  position: relative;
  min-height: 100vh;
  padding: 32px 20px 40px;
  /* 旅行主题渐变：蓝天到夕阳橙 */
  background: linear-gradient(135deg, #667eea 0%, #764ba2 35%, #f093fb 70%, #f5576c 100%);
  overflow: hidden;

  .header-card {
    margin-bottom: 28px;
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      h2 {
        margin: 0;
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 1px;
      }

      .actions {
        display: flex;
        gap: 16px;
      }
    }
  }

  .edit-content {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      h3 {
        margin: 0;
        font-size: 18px;
      }
    }

    .section-header-small {
      display: flex;
      justify-content: space-between;
      align-items: center;

      h4 {
        margin: 0;
        font-size: 16px;
      }
    }

    .day-title {
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-right: 20px;
    }

    .activities-section {
      margin-top: 20px;

      .section-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;

        h4 {
          margin: 0;
          font-size: 16px;
        }
      }

      .dining-item {
        margin-bottom: 16px;
      }
    }

    // 景点列表样式
    .attraction-list {
      .attraction-card {
        margin-bottom: 16px;
        cursor: move;

        &:hover {
          .attraction-item-card {
            border-color: #409eff;
            box-shadow: 0 2px 12px 0 rgba(64, 158, 255, 0.12);
          }
        }

        .attraction-item-card {
          .drag-handle {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: #f5f7fa;
            border-radius: 4px;
            margin-bottom: 12px;
            cursor: grab;

            &:hover {
              background: #e6e8eb;
            }

            .el-icon {
              font-size: 20px;
              color: #606266;
            }
          }

          .attraction-info {
            margin-bottom: 16px;

            h4 {
              margin: 0 0 8px 0;
              font-size: 16px;
              font-weight: 600;
              color: #303133;
            }

            .attraction-desc {
              margin: 0 0 8px 0;
              font-size: 14px;
              color: #606266;
              line-height: 1.5;
            }

            .attraction-tags {
              display: flex;
              gap: 8px;
              margin-bottom: 8px;
            }

            .attraction-address {
              margin: 0;
              font-size: 13px;
              color: #909399;
              display: flex;
              align-items: center;
              gap: 4px;
            }
          }

          .el-divider {
            margin: 16px 0;
          }

          .attraction-actions {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
          }

          .personal-settings {
            background: #f9fafc;
            padding: 12px;
            border-radius: 4px;

            :deep(.el-form-item) {
              margin-bottom: 12px;

              &:last-child {
                margin-bottom: 0;
              }
            }
          }
        }
      }
    }

    .preview-card,
    .hotels-edit-card {
      margin-bottom: 20px;
    }

    .hotel-edit-item {
      margin-bottom: 16px;
    }
  }
}
</style>

