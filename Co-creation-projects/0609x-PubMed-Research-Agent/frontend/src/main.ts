import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { ElAlert } from 'element-plus/es/components/alert/index'
import { ElAside, ElContainer, ElMain } from 'element-plus/es/components/container/index'
import { ElButton } from 'element-plus/es/components/button/index'
import { ElCard } from 'element-plus/es/components/card/index'
import { ElCol } from 'element-plus/es/components/col/index'
import { ElRow } from 'element-plus/es/components/row/index'
import { ElCollapse, ElCollapseItem } from 'element-plus/es/components/collapse/index'
import {
  ElDescriptions,
  ElDescriptionsItem
} from 'element-plus/es/components/descriptions/index'
import { ElDivider } from 'element-plus/es/components/divider/index'
import { ElDrawer } from 'element-plus/es/components/drawer/index'
import { ElEmpty } from 'element-plus/es/components/empty/index'
import { ElIcon } from 'element-plus/es/components/icon/index'
import { ElInput } from 'element-plus/es/components/input/index'
import { ElInputNumber } from 'element-plus/es/components/input-number/index'
import { ElLink } from 'element-plus/es/components/link/index'
import { ElMenu, ElMenuItem } from 'element-plus/es/components/menu/index'
import { ElOption, ElSelect } from 'element-plus/es/components/select/index'
import { ElProgress } from 'element-plus/es/components/progress/index'
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import { ElTag } from 'element-plus/es/components/tag/index'
import {
  ChatDotRound,
  Clock,
  DataAnalysis,
  DocumentCopy,
  Link,
  Loading,
  Search,
  Share,
  Star,
  StarFilled
} from '@element-plus/icons-vue'

import 'element-plus/es/components/base/style/css'
import 'element-plus/es/components/alert/style/css'
import 'element-plus/es/components/aside/style/css'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/card/style/css'
import 'element-plus/es/components/col/style/css'
import 'element-plus/es/components/collapse/style/css'
import 'element-plus/es/components/collapse-item/style/css'
import 'element-plus/es/components/container/style/css'
import 'element-plus/es/components/descriptions/style/css'
import 'element-plus/es/components/descriptions-item/style/css'
import 'element-plus/es/components/divider/style/css'
import 'element-plus/es/components/drawer/style/css'
import 'element-plus/es/components/empty/style/css'
import 'element-plus/es/components/icon/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/input-number/style/css'
import 'element-plus/es/components/link/style/css'
import 'element-plus/es/components/main/style/css'
import 'element-plus/es/components/menu/style/css'
import 'element-plus/es/components/menu-item/style/css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/option/style/css'
import 'element-plus/es/components/progress/style/css'
import 'element-plus/es/components/row/style/css'
import 'element-plus/es/components/select/style/css'
import 'element-plus/es/components/table/style/css'
import 'element-plus/es/components/table-column/style/css'
import 'element-plus/es/components/tag/style/css'

import App from './App.vue'
import router from './router'
import './styles/global.css'

const app = createApp(App)

const elementPlusComponents = [
  ElAlert,
  ElAside,
  ElButton,
  ElCard,
  ElCol,
  ElCollapse,
  ElCollapseItem,
  ElContainer,
  ElDescriptions,
  ElDescriptionsItem,
  ElDivider,
  ElDrawer,
  ElEmpty,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLink,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElProgress,
  ElRow,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
]

for (const component of elementPlusComponents) {
  app.use(component)
}

const elementPlusIcons = {
  ChatDotRound,
  Clock,
  DataAnalysis,
  DocumentCopy,
  Link,
  Loading,
  Search,
  Share,
  Star,
  StarFilled
}

for (const [name, component] of Object.entries(elementPlusIcons)) {
  app.component(name, component)
}

app.use(createPinia())
app.use(router)
app.mount('#app')
