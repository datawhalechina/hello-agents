import { createApp } from 'vue'
import {
  Alert, Button, Card, Collapse, Empty, Input, Layout,
  List, Menu, Select, Space, Spin, Table, Tag, Tooltip,
} from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'
const app = createApp(App)
app.use(router)
const comps = [Alert, Button, Card, Collapse, Empty, Input, Layout,
  List, Menu, Select, Space, Spin, Table, Tag, Tooltip]
comps.forEach((c) => app.use(c))
app.mount('#app')