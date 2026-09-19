import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import './styles/index.css'

const app = createApp(App)

app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
