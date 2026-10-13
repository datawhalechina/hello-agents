<template>
  <el-container class="app-shell">
    <el-aside width="220px" class="app-aside">
      <div class="brand">
        <el-icon :size="26" color="#409eff"><Search /></el-icon>
        <span class="brand-text">PubMed Research Agent</span>
      </div>

      <el-menu router :default-active="$route.path" class="app-menu">
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <span>文献检索</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 问答</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <span>检索历史</span>
        </el-menu-item>
        <el-menu-item index="/graph">
          <el-icon><Share /></el-icon>
          <span>知识图谱</span>
        </el-menu-item>
        <el-menu-item index="/library">
          <el-icon><Star /></el-icon>
          <span>文献收藏</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>研究看板</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-footer">FastAPI · Vue3 · Neo4j</div>
    </el-aside>

    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
// Root layout: sidebar navigation + routed page content.
</script>

<style scoped>
.app-shell {
  height: 100vh;
}
.app-aside {
  display: flex;
  flex-direction: column;
  background: var(--aside-bg, #0f172a);
  color: #e2e8f0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.brand-text {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  line-height: 1.3;
}
.app-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}
.app-menu :deep(.el-menu-item) {
  color: #cbd5e1;
}
.app-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.app-menu :deep(.el-menu-item.is-active) {
  background: var(--el-color-primary);
  color: #fff;
}
.aside-footer {
  padding: 14px 16px;
  font-size: 12px;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.app-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
