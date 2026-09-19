import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LoginView from '../LoginView.vue'
import { createTestingPinia } from '@pinia/testing'
import Antd from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

// Mock router
const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  }),
  useRoute: () => ({
    query: {}
  })
}))

describe('LoginView Button Interactions', () => {
  beforeEach(() => {
    pushMock.mockClear()
  })

  it('triggers login action when submit button is clicked', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: {
                loading: false,
                error: null
              }
            }
          }),
          Antd
        ],
        stubs: {
          'router-link': true,
          'user-outlined': true,
          'lock-outlined': true,
          'warning-outlined': true
        }
      }
    })

    const authStore = useAuthStore()
    
    // Find inputs and set values
    const usernameInput = wrapper.find('input[type="text"]')
    const passwordInput = wrapper.find('input[type="password"]')
    
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('password123')
    
    // Find the submit button
    // Note: Ant Design Button renders as a button element with class ant-btn
    const submitBtn = wrapper.find('.submit-btn')
    expect(submitBtn.exists()).toBe(true)
    
    // Simulate form submission
    // Since Ant Design form handles validation and submission internally, 
    // we can trigger the form submit event or click the button.
    // Triggering the form submit is more reliable for Ant Design forms in tests.
    await wrapper.find('form').trigger('submit')
    
    // Wait for async operations
    await flushPromises()
    
    // Verify login was called with correct credentials
    expect(authStore.login).toHaveBeenCalledTimes(1)
    expect(authStore.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'password123'
    })
  })

  it('shows loading state on button when auth is loading', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: {
                loading: true, // Set loading to true
                error: null
              }
            }
          }),
          Antd
        ],
        stubs: {
          'router-link': true,
          'user-outlined': true,
          'lock-outlined': true,
          'warning-outlined': true
        }
      }
    })

    const submitBtn = wrapper.find('.submit-btn')
    // Ant Design button adds .ant-btn-loading class when loading prop is true
    expect(submitBtn.classes()).toContain('ant-btn-loading')
    // Or check if the loading icon exists
    expect(wrapper.find('.anticon-loading').exists()).toBe(true)
  })
})
