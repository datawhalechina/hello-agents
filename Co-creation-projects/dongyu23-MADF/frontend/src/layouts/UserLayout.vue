<template>
  <div class="user-layout-container">
    <div class="user-layout-mask"></div>
    <div class="user-layout-content">
      <div class="top-header">
        <div class="header-logo">
          <span class="title">多智能体圆桌论坛 (MADF)</span>
        </div>
        <div class="header-desc">
          Next-Generation Multi-Agent Discussion Framework
        </div>
      </div>
      
      <div class="main-content">
        <router-view />
      </div>

      <div class="user-layout-footer">
        <div class="links">
          <a href="#">帮助</a>
          <a href="#">隐私</a>
          <a href="#">条款</a>
        </div>
        <div class="copyright">
          Copyright &copy; 2026 Trae AI
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-layout-container {
  width: 100%;
  min-height: 100vh;
  background: #f0f2f5 url(https://gw.alipayobjects.com/zos/rmsportal/TVYTbAXWheQpRcWDaDMu.svg) no-repeat center 110px;
  background-size: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.user-layout-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(2px);
  z-index: 1;
}

.user-layout-content {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 450px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.top-header {
  text-align: center;
  margin-bottom: 40px;
}

.header-logo .title {
  font-size: 32px;
  color: rgba(0, 0, 0, 0.85);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-weight: 600;
  position: relative;
  top: 2px;
}

.header-desc {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 12px;
}

.main-content {
  width: 100%;
  margin-bottom: 40px;
}

.user-layout-footer {
  width: 100%;
  text-align: center;
}

.user-layout-footer .links {
  margin-bottom: 8px;
  font-size: 14px;
}

.user-layout-footer .links a {
  color: rgba(0, 0, 0, 0.45);
  transition: all 0.3s;
  text-decoration: none;
  margin: 0 12px;
}

.user-layout-footer .links a:hover {
  color: rgba(0, 0, 0, 0.65);
}

.user-layout-footer .copyright {
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
}

@media (max-width: 576px) {
  .user-layout-content {
    width: 95%;
    padding: 16px;
  }
  
  .header-logo .title {
    font-size: 24px;
  }
}
</style>
