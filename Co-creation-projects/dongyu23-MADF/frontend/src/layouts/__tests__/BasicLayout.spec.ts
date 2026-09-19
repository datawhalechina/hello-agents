import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Antd from 'ant-design-vue'

import BasicLayout from '../BasicLayout.vue'
import { useAuthStore } from '@/stores/auth'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/dashboard' }),
  useRouter: () => ({ push }),
}))

describe('BasicLayout', () => {
  it('delegates logout navigation to the auth store without redirecting to an unknown route', async () => {
    const wrapper = mount(BasicLayout, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        stubs: { RouterView: true },
      },
    })
    const authStore = useAuthStore()

    await wrapper.find('[data-menu-id="logout"]').trigger('click')

    expect(authStore.logout).toHaveBeenCalledOnce()
    expect(push).not.toHaveBeenCalled()
  })
})
