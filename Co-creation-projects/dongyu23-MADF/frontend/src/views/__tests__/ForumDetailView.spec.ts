import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ForumDetailView from '../ForumDetailView.vue'
import { createTestingPinia } from '@pinia/testing'

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))

// Mock useRoute, useRouter
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: { id: '1' } })),
  useRouter: vi.fn(() => ({
    push: pushMock
  }))
}))

// Mock useForumWebSocket
vi.mock('@/composables/useForumWebSocket', () => ({
  useForumWebSocket: vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    isConnected: { value: true }
  }))
}))

// Mock ant-design-vue message
vi.mock('ant-design-vue', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('ForumDetailView', () => {
  it('renders header buttons correctly', async () => {
    pushMock.mockClear()
    const wrapper = mount(ForumDetailView, {
      global: {
        plugins: [createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            forum: {
              currentForum: {
                id: 1,
                topic: 'Test Forum',
                status: 'running',
                start_time: new Date().toISOString(),
                duration_minutes: 30
              },
              messages: [],
              loading: false
            },
            auth: { user: { id: 1 } },
            persona: { personas: [] }
          }
        })],
        stubs: {
            // Stub complex children
            MessageList: true,
            ForumTimer: true,
            ParticipantList: true,
            SystemLogConsole: true,
            // Stub icons
            ArrowLeftOutlined: true,
            TeamOutlined: true,
            DeleteOutlined: true,
            PlayCircleOutlined: true,
            CodeOutlined: true,
            // Stub UI components to simple HTML to verify presence
            'a-button': { template: '<button class="ant-btn"><slot /></button>' },
            'a-input-search': { template: '<div><slot name="prefix" /></div>' },
            'a-space': { template: '<div><slot /></div>' },
            'a-tag': { template: '<span><slot /></span>' },
            'a-popconfirm': { template: '<div><slot /></div>' },
            'a-modal': true
        }
      }
    })

    // 1. Verify Header Presence
    const header = wrapper.find('.forum-header')
    expect(header.exists()).toBe(true)

    // 2. Verify Topic
    expect(wrapper.find('.forum-topic').text()).toBe('Test Forum')

    // 3. Verify Buttons
    // Back button (first button in left header)
    const backButton = wrapper.find('.header-left button')
    expect(backButton.exists()).toBe(true)

    // Right header buttons
    const rightButtons = wrapper.findAll('.header-right button')
    // Should have: Stop, Participants, Delete, Logs (Start is hidden for running)
    expect(rightButtons.length).toBe(4)
    expect(wrapper.text()).toContain('停止论坛')
    
    // 4. Verify Z-Index Logic (Static check of class name or style if inline)
    // Since we used scoped CSS, we can't easily check computed style here without full browser.
    // But we can verify the structure allows clicking.
    
    // Simulate click on back button
    await backButton.trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/forums')
  })
})
