import { flushPromises, mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { describe, expect, it, vi } from 'vitest'
import Antd from 'ant-design-vue'

import RegisterView from '@/views/RegisterView.vue'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

describe('RegisterView', () => {
  it('submits email together with a valid password', async () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        stubs: {
          'router-link': true,
          'user-outlined': true,
          'lock-outlined': true,
          'warning-outlined': true
        }
      }
    })

    const store = useAuthStore()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('new-user')
    await inputs[1].setValue('new-user@example.com')
    await inputs[2].setValue('password123')
    await inputs[3].setValue('password123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(store.register).toHaveBeenCalledWith(expect.objectContaining({
      username: 'new-user',
      email: 'new-user@example.com',
      password: 'password123'
    }))
  })
})
