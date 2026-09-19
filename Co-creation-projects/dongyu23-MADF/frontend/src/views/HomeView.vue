<template>
  <div class="dashboard-page">
    <div class="welcome-section">
      <h2 class="welcome-title">欢迎回来，{{ authStore.user?.username }}</h2>
      <p class="welcome-subtitle">这里是您的多智能体协作中心，您可以管理智能体、发起讨论或查看实时进展。</p>
    </div>

    <a-row :gutter="[24, 24]">
      <a-col :xs="24" :lg="16">
        <a-card title="最近活跃论坛" :bordered="false" class="dashboard-card main-card">
            <template #extra><router-link to="/forums">查看全部</router-link></template>
            <div v-if="forumStore.loading" style="text-align: center; padding: 24px;">
              <a-spin />
            </div>
            <div v-else-if="forumStore.forums.length === 0" style="text-align: center; padding: 24px;">
              <a-empty description="暂无活跃论坛" />
            </div>
            <a-list
              v-else
              item-layout="horizontal"
              :data-source="forumStore.forums.slice(0, 5)"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <template #actions>
                    <a @click="$router.push(`/forums/${item.id}`)">进入</a>
                  </template>
                  <a-list-item-meta :description="item.start_time ? `开始于 ${new Date(item.start_time).toLocaleDateString()}` : '尚未开始'">
                    <template #title>
                      <a @click="$router.push(`/forums/${item.id}`)" class="list-item-title">{{ item.topic }}</a>
                    </template>
                    <template #avatar>
                      <a-avatar style="background-color: #1890ff">{{ item.topic[0] }}</a-avatar>
                    </template>
                  </a-list-item-meta>
                  <div class="status-tag">
                     <a-tag :color="item.status === 'active' ? 'processing' : 'default'">
                       {{ item.status === 'active' ? '进行中' : '已结束' }}
                     </a-tag>
                  </div>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
      </a-col>
      
      <a-col :xs="24" :lg="8">
        <div class="side-column">
          <a-card title="快捷操作" :bordered="false" class="dashboard-card">
            <div class="quick-actions">
              <a-button type="primary" block @click="$router.push('/personas')" class="action-btn">
                <team-outlined /> 创建新智能体
              </a-button>
              <a-button block @click="$router.push('/forums')" class="action-btn">
                <comment-outlined /> 发起新讨论
              </a-button>
              <a-button block danger @click="authStore.logout()" class="action-btn">
                <logout-outlined /> 退出登录
              </a-button>
            </div>
          </a-card>

          <a-card title="我的智能体" :bordered="false" class="dashboard-card">
            <template #extra><router-link to="/personas">管理</router-link></template>
            <div class="persona-mini-list">
              <div v-if="personaStore.loading" style="text-align: center; padding: 12px;">
                <a-spin size="small" />
              </div>
              <div v-else-if="personaStore.personas.length === 0" style="text-align: center; color: #999; padding: 12px 0;">
                暂无智能体
              </div>
              <template v-else>
                <div v-for="p in personaStore.personas.slice(0, 4)" :key="p.id" class="persona-item">
                  <a-avatar size="small" style="background-color: #7265e6">{{ p.name[0] }}</a-avatar>
                  <span class="persona-name">{{ p.name }}</span>
                </div>
              </template>
            </div>
          </a-card>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { TeamOutlined, CommentOutlined, LogoutOutlined } from '@ant-design/icons-vue'

const authStore = useAuthStore()
const forumStore = useForumStore()
const personaStore = usePersonaStore()

onMounted(() => {
  forumStore.fetchForums()
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.welcome-section {
  margin-bottom: 32px;
}

.welcome-title {
  font-size: 28px;
  font-weight: 500;
  color: rgba(0,0,0,0.85);
  margin-bottom: 8px;
}

.welcome-subtitle {
  font-size: 16px;
  color: rgba(0,0,0,0.45);
}

.dashboard-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  height: 100%;
}

.main-card {
  min-height: 400px;
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-btn {
  height: 40px;
  font-size: 15px;
}

.persona-mini-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.persona-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  background: #f9f9f9;
  transition: all 0.3s;
}

.persona-item:hover {
  background: #f0f0f0;
}

.persona-name {
  font-size: 14px;
  color: rgba(0,0,0,0.85);
  font-weight: 500;
}

.list-item-title {
  font-size: 15px;
  font-weight: 500;
  color: rgba(0,0,0,0.85);
}

@media (max-width: 576px) {
  .welcome-title {
    font-size: 24px;
  }
  
  .welcome-subtitle {
    font-size: 14px;
  }
  
  .status-tag {
    display: none;
  }
}
</style>
