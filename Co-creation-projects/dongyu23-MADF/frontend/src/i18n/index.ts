import { createI18n } from 'vue-i18n'

const messages = {
  en: {
    common: {
      home: 'Home',
      test: 'Test Page',
      darkMode: 'Dark Mode',
      lightMode: 'Light Mode',
      language: 'Language',
    },
    agent: {
      title: 'Agent Chat',
      inputPlaceholder: 'Enter your instruction...',
      send: 'Send',
      thinking: 'Thinking...',
      history: 'History',
      clear: 'Clear History',
    },
    test: {
      title: 'API Test Dashboard',
      createUser: 'Create User',
      createPersona: 'Create Persona',
      createForum: 'Create Forum',
      chat: 'Chat',
      username: 'Username',
      email: 'Email',
      password: 'Password',
      personaName: 'Persona Name',
      personaDesc: 'Description',
      forumName: 'Forum Name',
      forumDesc: 'Description',
      instruction: 'Instruction',
      submit: 'Submit',
      result: 'Result',
    }
  },
  zh: {
    common: {
      home: '首页',
      test: '测试页',
      darkMode: '暗黑模式',
      lightMode: '亮色模式',
      language: '语言',
    },
    agent: {
      title: '智能体对话',
      inputPlaceholder: '请输入指令...',
      send: '发送',
      thinking: '思考中...',
      history: '历史记录',
      clear: '清空历史',
    },
    test: {
      title: 'API 测试面板',
      createUser: '创建用户',
      createPersona: '创建角色',
      createForum: '创建论坛',
      chat: '对话',
      username: '用户名',
      email: '邮箱',
      password: '密码',
      personaName: '角色名',
      personaDesc: '描述',
      forumName: '论坛名',
      forumDesc: '描述',
      instruction: '指令',
      submit: '提交',
      result: '结果',
    }
  }
}

const i18n = createI18n({
  locale: 'zh', // set locale
  fallbackLocale: 'en', // set fallback locale
  messages, // set locale messages
  legacy: false, // use Composition API
})

export default i18n
