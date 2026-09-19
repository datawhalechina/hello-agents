import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import HomeView from '../HomeView.vue'
import { createTestingPinia } from '@pinia/testing'
import { createI18n } from 'vue-i18n'
import Antd from 'ant-design-vue'

const i18n = createI18n({
  locale: 'en',
  legacy: false,
  messages: {
    en: {
      agent: {
        title: 'Agent Chat',
        inputPlaceholder: 'Enter...',
        send: 'Send',
        thinking: 'Thinking...',
        clear: 'Clear',
        history: 'History'
      }
    }
  }
})

describe('HomeView', () => {
  it('renders properly', () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [
          createTestingPinia({ createSpy: vi.fn }),
          i18n,
          Antd
        ],
        stubs: {
          RouterLink: { template: '<a><slot /></a>' }
        }
      }
    })
    expect(wrapper.text()).toContain('欢迎回来')
  })
})
