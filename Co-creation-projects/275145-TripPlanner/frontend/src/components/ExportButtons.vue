<template>
  <div class="export-buttons">
    <el-button-group>
      <el-button
        type="primary"
        :loading="exporting"
        @click="handleExport('pdf')"
      >
        <el-icon><Document /></el-icon>
        导出 PDF
      </el-button>
      <el-button
        type="success"
        :loading="exporting"
        @click="handleExport('image')"
      >
        <el-icon><Picture /></el-icon>
        导出图片
      </el-button>
    </el-button-group>

    <!-- 导出配置对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="导出设置"
      width="400px"
    >
      <el-form label-width="100px">
        <el-form-item label="包含内容">
          <el-checkbox-group v-model="exportOptions.includes">
            <el-checkbox label="budget">预算明细</el-checkbox>
            <el-checkbox label="map">地图截图</el-checkbox>
            <el-checkbox label="hotels">酒店信息</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">确认导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { Document, Picture } from '@element-plus/icons-vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import type { TripPlanResponse } from '@/types'

interface Props {
  tripPlan: TripPlanResponse
  contentRef?: HTMLElement
}

const props = defineProps<Props>()

const exporting = ref(false)
const dialogVisible = ref(false)
const currentFormat = ref<'pdf' | 'image'>('pdf')

const exportOptions = reactive({
  includes: ['budget', 'map', 'hotels']
})

// 处理导出按钮点击
const handleExport = (format: 'pdf' | 'image') => {
  currentFormat.value = format
  dialogVisible.value = true
}

// 确认导出
const confirmExport = async () => {
  dialogVisible.value = false
  
  // 显示加载（在对话框关闭后）
  let loadingInstance: any = null
  
  try {
    // 等待Vue DOM更新和对话框动画完成
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // 现在显示加载提示
    loadingInstance = ElLoading.service({
      lock: true,
      text: '正在生成文件...',
      background: 'rgba(0, 0, 0, 0.7)'
    })
    
    if (currentFormat.value === 'pdf') {
      await exportToPDF()
    } else {
      await exportToImage()
    }
    ElMessage.success('导出成功！')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败，请重试')
  } finally {
    exporting.value = false
    if (loadingInstance) {
      loadingInstance.close()
    }
  }
}

// 导出为 PDF
const exportToPDF = async () => {
  if (!props.contentRef) {
    ElMessage.warning('未找到内容元素')
    return
  }

  // 使用 html2canvas 将内容转为图片
  const canvas = await html2canvas(props.contentRef, {
    scale: 2,
    useCORS: true,
    logging: false,
    backgroundColor: '#ffffff'
  })

  // 创建 PDF
  const imgWidth = 210 // A4 宽度（mm）
  const imgHeight = (canvas.height * imgWidth) / canvas.width
  const pdf = new jsPDF('p', 'mm', 'a4')

  // 如果内容超过一页，需要分页
  let heightLeft = imgHeight
  let position = 0

  const imgData = canvas.toDataURL('image/jpeg', 1.0)
  pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight)
  heightLeft -= 297 // A4 高度

  while (heightLeft > 0) {
    position = heightLeft - imgHeight
    pdf.addPage()
    pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297
  }

  // 生成文件名
  const filename = `${props.tripPlan.trip_title || '行程计划'}_${Date.now()}.pdf`
  pdf.save(filename)
}

// 导出为图片
const exportToImage = async () => {
  if (!props.contentRef) {
    ElMessage.warning('未找到内容元素')
    return
  }

  // 使用 html2canvas 截图
  const canvas = await html2canvas(props.contentRef, {
    scale: 2,
    useCORS: true,
    logging: false,
    backgroundColor: '#ffffff'
  })

  // 转为 blob 并下载
  canvas.toBlob((blob) => {
    if (!blob) {
      ElMessage.error('生成图片失败')
      return
    }

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.tripPlan.trip_title || '行程计划'}_${Date.now()}.png`
    link.click()

    // 清理
    URL.revokeObjectURL(url)
  }, 'image/png')
}

// 快速导出（不显示对话框）
const quickExport = async (format: 'pdf' | 'image') => {
  currentFormat.value = format
  await confirmExport()
}

defineExpose({
  quickExport
})
</script>

<style scoped lang="scss">
.export-buttons {
  :deep(.el-button-group) {
    display: flex;
  }
}
</style>
