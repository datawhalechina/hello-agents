import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Antd from 'ant-design-vue'

import ForumListView from '../ForumListView.vue'

describe('ForumListView', () => {
  it('exposes the create action through the responsive page header', () => {
    const wrapper = mount(ForumListView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        mocks: {
          $router: { push: vi.fn() },
        },
      },
    })

    const createButton = wrapper.get('.create-forum-btn')
    expect(createButton.text()).toContain('发起新讨论')
    expect(wrapper.find('.forum-grid').exists()).toBe(true)
  })

  it('keeps participant and moderator selectors searchable for large datasets', async () => {
    const wrapper = mount(ForumListView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        mocks: {
          $router: { push: vi.fn() },
        },
      },
    })

    await wrapper.get('.create-forum-btn').trigger('click')
    const selects = wrapper.findAllComponents({ name: 'ASelect' })
    expect(selects).toHaveLength(2)
    expect(selects[0].props('showSearch')).toBe(true)
    expect(selects[0].props('optionFilterProp')).toBe('label')
    expect(selects[1].props('showSearch')).toBe(true)
  })

  it('uses a dedicated numeric input for duration so topic focus cannot capture digits', async () => {
    const wrapper = mount(ForumListView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        mocks: { $router: { push: vi.fn() } },
      },
    })

    await wrapper.get('.create-forum-btn').trigger('click')
    const duration = document.querySelector('input.duration-input') as HTMLInputElement | null
    const topic = document.querySelector('input[placeholder="例如：人工智能对未来就业的影响"]') as HTMLInputElement | null
    expect(duration).not.toBeNull()
    expect(duration?.type).toBe('number')
    expect(duration?.min).toBe('1')
    expect(duration?.max).toBe('120')
    expect(topic).not.toBeNull()
  })
})
