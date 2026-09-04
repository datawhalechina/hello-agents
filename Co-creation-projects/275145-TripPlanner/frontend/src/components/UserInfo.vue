<template>
  <div class="user-info">
    <!-- 用户已登录状态 -->
    <div v-if="authStore.isAuthenticated" class="logged-in">
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-avatar">
          <el-avatar :size="32" :src="userAvatar">
            <el-icon><UserFilled /></el-icon>
          </el-avatar>
          <span class="username">{{ displayName }}</span>
          <el-icon class="arrow"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人信息
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              设置
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    
    <!-- 用户未登录状态 -->
    <div v-else class="not-logged-in">
      <el-button type="primary" @click="goToLogin">
        <el-icon><UserFilled /></el-icon>
        登录/注册
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { 
  UserFilled, 
  ArrowDown, 
  User, 
  Setting, 
  SwitchButton 
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

// 计算显示名称
const displayName = computed(() => {
  return authStore.username || '用户'
})

// 计算用户头像URL
const userAvatar = computed(() => {
  // 从用户信息中获取头像URL
  return authStore.user?.avatar_url || ''
})

// 处理下拉菜单命令
const handleCommand = (command: string) => {
  switch (command) {
    case 'profile':
      goToProfile()
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
      break
    case 'logout':
      logout()
      break
  }
}

// 跳转到登录页面
const goToLogin = () => {
  router.push('/login')
}

// 跳转到用户资料页面
const goToProfile = () => {
  router.push('/profile')
}

// 退出登录
const logout = async () => {
  try {
    await authStore.logout()
    ElMessage.success('退出登录成功')
    router.push('/')
  } catch (error: any) {
    ElMessage.error(error.message || '退出登录失败')
  }
}
</script>

<style lang="scss" scoped>
.user-info {
  .logged-in {
    .user-avatar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;
      
      &:hover {
        background: #f5f5f5;
      }
      
      .username {
        font-size: 14px;
        color: #333;
        font-weight: 500;
      }
      
      .arrow {
        font-size: 12px;
        color: #666;
        transition: transform 0.3s;
      }
    }
  }
  
  .not-logged-in {
    .el-button {
      border-radius: 20px;
      padding: 8px 16px;
      font-size: 14px;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .user-info {
    .logged-in {
      .user-avatar {
        .username {
          display: none; // 小屏幕隐藏用户名
        }
      }
    }
    
    .not-logged-in {
      .el-button {
        padding: 6px 12px;
        font-size: 13px;
        
        span {
          margin-right: 4px;
        }
      }
    }
  }
}
</style>