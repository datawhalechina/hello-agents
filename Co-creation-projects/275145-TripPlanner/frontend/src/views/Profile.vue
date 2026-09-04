<template>
  <div class="profile-container">
    <!-- 背景装饰 -->
    <div class="background-decoration">
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
      <div class="decoration-circle circle-3"></div>
    </div>

    <!-- 主要内容 -->
    <div class="profile-content">
      <!-- 头部 -->
      <div class="profile-header">
        <el-button @click="goBack" class="back-button" link>
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <h1>个人资料</h1>
      </div>

      <!-- 个人信息卡片 -->
      <el-card class="profile-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <h3>基本信息</h3>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-width="100px"
          label-position="top"
          class="profile-form"
        >
          <!-- 头像上传 -->
          <div class="avatar-section">
            <div class="avatar-upload">
              <el-upload
                class="avatar-uploader"
                :show-file-list="false"
                :before-upload="beforeAvatarUpload"
                :on-change="handleAvatarChange"
                :auto-upload="false"
                action="#"
              >
                <el-avatar :size="100" :src="avatarUrl">
                  <el-icon v-if="!avatarUploading"><UserFilled /></el-icon>
                  <el-icon v-else class="is-loading"><Loading /></el-icon>
                </el-avatar>
                <div class="avatar-mask" :class="{ uploading: avatarUploading }">
                  <el-icon v-if="!avatarUploading"><Camera /></el-icon>
                  <el-icon v-else class="is-loading"><Loading /></el-icon>
                  <span>{{ avatarUploading ? '上传中...' : '更换头像' }}</span>
                </div>
              </el-upload>
            </div>
            <p class="avatar-tip">支持 JPG、PNG 格式，文件大小不超过 2MB</p>
          </div>

          <!-- 用户名 -->
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="formData.username"
              placeholder="请输入用户名"
              maxlength="20"
              show-word-limit
            />
          </el-form-item>

          <!-- 手机号 -->
          <el-form-item label="手机号" prop="phone">
            <el-input
              v-model="formData.phone"
              placeholder="请输入手机号码（选填）"
              maxlength="11"
            >
              <template #prefix>
                <el-icon><Phone /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <!-- 性别 -->
          <el-form-item label="性别" prop="gender">
            <el-radio-group v-model="formData.gender">
              <el-radio label="male">男</el-radio>
              <el-radio label="female">女</el-radio>
              <el-radio label="other">保密</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 生日 -->
          <el-form-item label="生日" prop="birthday">
            <el-date-picker
              v-model="formData.birthday"
              type="date"
              placeholder="请选择生日"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>

          <!-- 个人简介 -->
          <el-form-item label="个人简介" prop="bio">
            <el-input
              v-model="formData.bio"
              type="textarea"
              :rows="3"
              placeholder="介绍一下你自己吧"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>

          <!-- 旅行偏好 -->
          <el-form-item label="旅行偏好">
            <el-select
              v-model="formData.travel_preferences"
              multiple
              placeholder="选择您的旅行偏好"
              style="width: 100%"
              collapse-tags
              collapse-tags-tooltip
            >
              <el-option label="🏯 历史文化" value="历史" />
              <el-option label="🌄 自然风光" value="自然" />
              <el-option label="🍜 美食体验" value="美食" />
              <el-option label="🛍️ 购物娱乐" value="购物" />
              <el-option label="👶 亲子游玩" value="亲子" />
              <el-option label="📸 摄影打卡" value="摄影" />
              <el-option label="☘️ 休闲放松" value="休闲" />
              <el-option label="🏔️ 户外探险" value="探险" />
            </el-select>
          </el-form-item>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleSubmit"
              class="submit-button"
            >
              保存修改
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 账号安全 -->
      <el-card class="security-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <h3>账号安全</h3>
          </div>
        </template>

        <div class="security-list">
          <div class="security-item">
            <div class="item-left">
              <el-icon class="item-icon"><Lock /></el-icon>
              <div class="item-info">
                <h4>修改密码</h4>
                <p>定期修改密码，保障账号安全</p>
              </div>
            </div>
            <el-button @click="showPasswordDialog = true">修改</el-button>
          </div>

        </div>
      </el-card>
    </div>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="showPasswordDialog"
      title="修改密码"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="80px"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            placeholder="请输入原密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="passwordLoading"
          @click="handleChangePassword"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules, type UploadProps } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/services/api'
import type { UpdateProfileRequest, ChangePasswordRequest } from '@/types'
import {
  ArrowLeft,
  UserFilled,
  Camera,
  Phone,
  InfoFilled,
  Lock,
  Loading
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

// 表单引用
const formRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)
const passwordLoading = ref(false)
const showPasswordDialog = ref(false)
const avatarUploading = ref(false)  // 头像上传状态

// 头像URL（用于显示/预览）
const avatarUrl = ref('')
// 原始头像URL（用于提交到后端）
const originalAvatarUrl = ref('')
// 临时保存待上传的文件
const pendingAvatarFile = ref<File | null>(null)

// 表单数据
const formData = reactive({
  username: '',
  phone: '',
  gender: 'other',
  birthday: '',
  bio: '',
  travel_preferences: []
})

// 密码表单
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 表单验证规则
const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在 2 到 20 个字符', trigger: ['blur', 'change'] }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: ['blur', 'change'] }
  ],
  bio: [
    { max: 200, message: '个人简介不能超过 200 个字符', trigger: ['blur', 'change'] }
  ]
}

// 密码验证规则
const passwordRules: FormRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: ['blur', 'change'] }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 头像上传前的验证
const beforeAvatarUpload: UploadProps['beforeUpload'] = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('上传头像只能是图片格式!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('上传头像大小不能超过 2MB!')
    return false
  }
  return true
}

// 头像选择变化时立即上传并预览
const handleAvatarChange: UploadProps['onChange'] = async (uploadFile) => {
  if (uploadFile.raw) {
    avatarUploading.value = true
    
    try {
      // 上传头像到服务器
      const uploadResult = await authApi.uploadAvatar(uploadFile.raw)
      
      // 使用服务器返回的URL
      avatarUrl.value = uploadResult.url
      pendingAvatarFile.value = uploadFile.raw
      
      ElMessage.success('头像上传成功')
    } catch (error: any) {
      console.error('头像上传失败:', error)
      ElMessage.error(error.message || '头像上传失败，请重试')
      
      // 恢复原头像
      avatarUrl.value = originalAvatarUrl.value
    } finally {
      avatarUploading.value = false
    }
  }
}

// 加载用户信息
onMounted(() => {
  if (authStore.user) {
    formData.username = authStore.user.username || ''
    formData.phone = authStore.user.phone || ''
    formData.gender = authStore.user.gender || 'other'
    formData.birthday = authStore.user.birthday || ''
    formData.bio = authStore.user.bio || ''
    formData.travel_preferences = authStore.user.travel_preferences || []
    avatarUrl.value = authStore.user.avatar_url || ''
    originalAvatarUrl.value = authStore.user.avatar_url || ''
  }
})

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true

    try {
      // 构建更新请求
      // 如果正在进行图片上传，使用当前的头像URL（已经是服务器返回的URL）
      const finalAvatarUrl = avatarUrl.value

      const updateData: UpdateProfileRequest = {
        username: formData.username,
        phone: formData.phone || undefined,
        gender: formData.gender,
        birthday: formData.birthday || undefined,
        bio: formData.bio || undefined,
        travel_preferences: formData.travel_preferences,
        avatar_url: finalAvatarUrl || undefined
      }

      console.log('提交用户资料更新:', updateData)

      // 调用更新用户信息API
      const updatedUser = await authApi.updateProfile(updateData)

      // 更新本地状态
      authStore.updateUser(updatedUser)
      originalAvatarUrl.value = updatedUser.avatar_url || ''
      pendingAvatarFile.value = null

      ElMessage.success('保存成功！')
    } catch (error: any) {
      console.error('保存用户资料失败:', error)
      ElMessage.error(error.message || '保存失败，请重试')
    } finally {
      loading.value = false
    }
  })
}

// 修改密码
const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    passwordLoading.value = true

    try {
      // 构建密码修改请求
      const passwordData: ChangePasswordRequest = {
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password
      }

      // 调用修改密码API
      await authApi.changePassword(passwordData)

      ElMessage.success('密码修改成功！')
      showPasswordDialog.value = false

      // 重置表单
      passwordForm.old_password = ''
      passwordForm.new_password = ''
      passwordForm.confirm_password = ''
      passwordFormRef.value?.clearValidate()
    } catch (error: any) {
      ElMessage.error(error.message || '密码修改失败，请重试')
    } finally {
      passwordLoading.value = false
    }
  })
}

// 返回首页
const goBack = () => {
  router.push('/')
}
</script>

<style scoped lang="scss">
.profile-container {
  position: relative;
  min-height: 100vh;
  padding: 0;
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

  .profile-content {
    position: relative;
    max-width: 900px;
    margin: 0 auto;
    padding: 80px 20px 40px;
    z-index: 1;
  }
}

.profile-header {
  text-align: center;
  margin-bottom: 40px;

  .back-button {
    position: absolute;
    left: 20px;
    top: 20px;
    color: white;
    font-size: 16px;
  }

  h1 {
    margin: 0;
    font-size: 36px;
    font-weight: 700;
    color: white;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }
}

.profile-card {
  border-radius: 16px;
  margin-bottom: 24px;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }
  }

  .profile-form {
    padding: 20px 0;

    .avatar-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 30px;

      .avatar-upload {
        position: relative;
        cursor: pointer;

        .el-avatar {
          border: 4px solid white;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .avatar-mask {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: rgba(0, 0, 0, 0.5);
          border-radius: 50%;
          opacity: 0;
          transition: opacity 0.3s;
          color: white;

          .el-icon {
            font-size: 24px;
            margin-bottom: 8px;
          }

          span {
            font-size: 14px;
          }
        }

        &:hover .avatar-mask {
          opacity: 1;
        }
      }

      .avatar-tip {
        margin: 12px 0 0;
        font-size: 12px;
        color: #909399;
      }
    }

    .form-tip {
      margin-top: 4px;
      font-size: 12px;
      color: #e6a23c;
    }

    .submit-button {
      width: 100%;
      height: 44px;
      font-size: 16px;
      font-weight: 600;
      border-radius: 8px;
    }
  }
}

.guest-tip-card {
  border-radius: 16px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #fff7e6 0%, #ffffff 100%);

  .guest-tip-content {
    display: flex;
    gap: 20px;

    .tip-icon {
      font-size: 48px;
      color: #e6a23c;
      flex-shrink: 0;
    }

    .tip-text {
      flex: 1;

      h4 {
        margin: 0 0 12px;
        font-size: 18px;
        font-weight: 600;
        color: #333;
      }

      p {
        margin: 0 0 12px;
        color: #666;
        line-height: 1.6;
      }

      ul {
        margin: 16px 0;
        padding-left: 20px;
        color: #666;
        line-height: 2;
      }

      .el-button {
        margin-top: 16px;
      }
    }
  }
}

.security-card {
  border-radius: 16px;

  .security-list {
    .security-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 0;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
        padding-bottom: 0;
      }

      .item-left {
        display: flex;
        align-items: center;
        gap: 16px;

        .item-icon {
          font-size: 28px;
          color: #409eff;
        }

        .item-info {
          h4 {
            margin: 0 0 4px;
            font-size: 16px;
            font-weight: 600;
            color: #333;
          }

          p {
            margin: 0;
            font-size: 14px;
            color: #909399;
          }
        }
      }
    }
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .profile-header {
    h1 {
      font-size: 28px;
    }
  }

  .guest-tip-content {
    flex-direction: column;

    .tip-icon {
      align-self: center;
    }
  }
}
</style>
