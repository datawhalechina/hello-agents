<template>
  <div class="forum-list-page">
    <div class="page-header">
      <div class="header-title">
        <span class="title">圆桌论坛</span>
        <span class="subtitle">创建多智能体讨论组，观察思维碰撞</span>
      </div>
      <a-button type="primary" size="large" class="create-forum-btn" @click="showModal()">
        <plus-outlined /> 发起新讨论
      </a-button>
    </div>

    <a-spin :spinning="forumStore.loading && forumStore.forums.length === 0">
      <div v-if="forumStore.loading && forumStore.forums.length === 0" class="forum-grid">
        <a-card v-for="i in 6" :key="i" class="forum-card">
          <a-skeleton active :paragraph="{ rows: 2 }" />
        </a-card>
      </div>
      <div v-else class="forum-grid">
        <a-card
          v-for="item in paginatedForums"
          :key="item.id"
          hoverable
          class="forum-card"
          @click="$router.push(`/forums/${item.id}`)"
        >
          <a-card-meta>
            <template #title>
              <div class="card-title">
                <span class="topic">{{ item.topic }}</span>
                <a-tag :color="getStatusColor(item.status)">{{ getStatusText(item.status) }}</a-tag>
              </div>
            </template>
            <template #description>
              <div class="card-desc">
                创建时间: {{ item.start_time ? new Date(item.start_time).toLocaleString() : '尚未开始' }}
              </div>
            </template>
            <template #avatar>
              <a-avatar
                shape="square"
                size="large"
                :style="{ backgroundColor: getAvatarColor(item.topic) }"
              >
                {{ item.topic[0] }}
              </a-avatar>
            </template>
          </a-card-meta>
          
          <div class="card-footer" @click.stop>
            <div class="card-footer-actions">
              <a-popconfirm 
                title="确定删除该论坛吗？" 
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(item.id)"
                @click.stop
              >
                <a-button type="text" danger size="small" @click.stop>
                  <delete-outlined /> 删除
                </a-button>
              </a-popconfirm>
              <span class="action-text" @click="$router.push(`/forums/${item.id}`)">点击进入讨论 <arrow-right-outlined /></span>
            </div>
          </div>
        </a-card>
        
        <div v-if="forumStore.forums.length === 0 && !forumStore.loading" class="empty-state">
          <a-empty description="暂无正在进行的论坛，发起一个新的话题吧" />
        </div>
      </div>
      <div class="pagination-wrapper" v-if="forumStore.forums.length > forumPageSize">
        <a-pagination
          v-model:current="forumPage"
          :page-size="forumPageSize"
          :total="forumStore.forums.length"
          :show-size-changer="false"
        />
      </div>
    </a-spin>

    <a-modal
      v-model:open="visible"
      title="发起新讨论"
      @ok="handleOk"
      :confirmLoading="submitting"
      width="520px"
    >
      <a-form layout="vertical" ref="formRef" :model="formState">
        <a-form-item
          label="讨论主题"
          name="topic"
          :rules="[{ required: true, message: '请输入讨论主题' }]"
        >
          <a-input
            v-model:value="formState.topic"
            placeholder="例如：人工智能对未来就业的影响"
            size="large"
          />
        </a-form-item>
        
        <a-form-item
          label="邀请参与者"
          name="participant_ids"
          :rules="[{ required: true, message: '请至少选择一位智能体' }]"
        >
          <a-select
            v-model:value="formState.participant_ids"
            mode="multiple"
            show-search
            option-filter-prop="label"
            placeholder="选择参与讨论的智能体"
            :options="personaOptions"
            :loading="personaStore.loading"
            size="large"
            style="width: 100%"
          >
            <template #option="{ label }">
               <div style="display: flex; justify-content: space-between">
                 <span>{{ label }}</span>
               </div>
            </template>
          </a-select>
          <div style="margin-top: 8px; color: #8c8c8c; font-size: 12px;">
            提示：您可以选择自己创建的智能体，也可以邀请公开的智能体加入。
          </div>
        </a-form-item>

        <a-form-item label="主持人" name="moderator_id">
          <a-select
            v-model:value="formState.moderator_id"
            allow-clear
            show-search
            option-filter-prop="label"
            placeholder="使用系统默认主持人"
            :options="moderatorOptions"
            :loading="forumStore.loading"
            size="large"
          />
        </a-form-item>

        <a-form-item label="论坛时长 (分钟)" name="duration">
            <input
              v-model.number="formState.duration"
              class="duration-input"
              type="number"
              min="1"
              max="120"
              step="1"
              inputmode="numeric"
              aria-label="论坛时长 (分钟)"
            />
            <div class="field-help">支持 1 到 120 分钟，长时讨论建议 30 分钟以上。</div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { message } from 'ant-design-vue'
import { PlusOutlined, ArrowRightOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const forumStore = useForumStore()
const personaStore = usePersonaStore()
const visible = ref(false)
const submitting = ref(false)
const forumPage = ref(1)
const forumPageSize = 9

const formState = reactive({
  topic: '',
  participant_ids: [] as number[],
  moderator_id: undefined as number | undefined,
  duration: 5
})

onMounted(() => {
  forumStore.fetchForums()
  forumStore.fetchModerators()
  personaStore.fetchPersonas()
})

const moderatorOptions = computed(() => {
  return forumStore.moderators.map(m => ({
    label: m.name,
    value: m.id
  }))
})

const personaOptions = computed(() => {
  return personaStore.personas.map(p => ({
    label: p.name,
    value: p.id
  }))
})

const paginatedForums = computed(() => {
  const start = (forumPage.value - 1) * forumPageSize
  return forumStore.forums.slice(start, start + forumPageSize)
})

const getStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'processing'
    case 'pending': return 'warning'
    case 'closed':
    case 'finished': return 'default'
    case 'active': return 'processing'
    default: return 'default'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'running': return '进行中'
    case 'pending': return '未开始'
    case 'closed':
    case 'finished': return '已结束'
    case 'active': return '进行中'
    default: return '未知'
  }
}

const getAvatarColor = (topic: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < topic.length; i++) {
    hash = topic.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const showModal = async () => {
  visible.value = true // Open modal immediately for better UX
  // Load data in background
  forumStore.fetchModerators()
  personaStore.fetchPersonas() // Ensure personas are also loaded
  
  formState.topic = ''
  formState.participant_ids = []
  formState.moderator_id = undefined
  formState.duration = 5
}

const handleOk = async () => {
  formState.topic = formState.topic.trim()
  if (!formState.topic || formState.participant_ids.length === 0) {
    message.warning('请填写完整信息')
    return
  }
  if (formState.participant_ids.length > 5) {
    message.warning('每个论坛最多选择 5 位智能体')
    return
  }
  if (formState.duration < 1 || formState.duration > 120) {
    message.warning('论坛时长必须在 1 到 120 分钟之间')
    return
  }
  
  submitting.value = true
  try {
    await forumStore.fetchModerators()
    if (formState.moderator_id && !forumStore.moderators.some(m => m.id === formState.moderator_id)) {
      formState.moderator_id = undefined
      message.warning('所选主持人已失效，请重新选择')
      return
    }
    await forumStore.createForum(formState.topic, formState.participant_ids, formState.duration, formState.moderator_id)
    visible.value = false
  } catch (e: unknown) {
    if (e instanceof Error) {
        message.error(e.message || '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
    // No loading spinner for optimistic delete to keep UI snappy
    // forumStore.loading = true 
    try {
        await forumStore.deleteForum(id)
        message.success('删除成功')
    } catch (e: any) {
        console.error(e)
        message.error(e.message || '删除失败')
    }
}
</script>

<style scoped>
.forum-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 24px;
  font-weight: 500;
  color: rgba(0,0,0,0.85);
}

.subtitle {
  font-size: 14px;
  color: rgba(0,0,0,0.45);
  margin-top: 4px;
}

.forum-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.forum-card {
  border-radius: 8px;
  transition: all 0.3s;
  cursor: pointer;
}

.forum-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 0;
}

.card-title .topic {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 8px;
}

.card-desc {
  margin-top: 8px;
  font-size: 12px;
}

.card-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  color: #1890ff;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 48px 0;
  text-align: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.field-help {
  margin-top: 6px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}

.card-footer-actions {
  align-items: center;
  display: flex;
  justify-content: space-between;
  min-width: 0;
  width: 100%;
}

@media (max-width: 768px) {
  .forum-list-page {
    padding: 20px 12px;
  }

  .page-header {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
  }

  .create-forum-btn {
    width: 100%;
  }

  .forum-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }

  .forum-card {
    min-width: 0;
  }

  .card-footer-actions {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
