import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import Giscus from './components/Giscus.vue'

export default {
  extends: DefaultTheme,
  Layout: () => {
    return h(DefaultTheme.Layout, null, {
      'doc-bottom': () => h(Giscus),
    })
  },
}
