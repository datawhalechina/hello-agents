import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Antd, { message } from 'ant-design-vue'

import PersonaView from '../PersonaView.vue'

describe('PersonaView', () => {
  it('keeps both primary actions inside the responsive header action group', () => {
    const wrapper = mount(PersonaView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        stubs: {
          RealGodAgentModal: true,
        },
      },
    })

    const actions = wrapper.get('.header-actions')
    expect(actions.text()).toContain('上帝生成真实角色')
    expect(actions.text()).toContain('创建智能体')
    expect(actions.findAll('button')).toHaveLength(2)
  })

  it('rejects a whitespace-only persona name before calling the store', async () => {
    const wrapper = mount(PersonaView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), Antd],
        stubs: {
          RealGodAgentModal: true,
        },
      },
    })
    const warning = vi.spyOn(message, 'warning').mockImplementation(() => undefined as never)

    const createButton = wrapper.findAll('.header-actions button').find(button =>
      button.text().includes('创建智能体'),
    )
    expect(createButton).toBeDefined()
    await createButton?.trigger('click')
    await wrapper.vm.$nextTick()
    const nameInput = document.body.querySelector(
      'input[placeholder="例如：苏格拉底"]',
    ) as HTMLInputElement
    expect(nameInput).not.toBeNull()
    nameInput.value = '   '
    nameInput.dispatchEvent(new Event('input'))
    const modal = document.body.querySelector('.ant-modal')
    expect(modal).not.toBeNull()
    ;(modal?.querySelector('.ant-btn-primary') as HTMLButtonElement).click()
    await wrapper.vm.$nextTick()

    expect(warning).toHaveBeenCalledWith('请输入智能体名称')
    warning.mockRestore()
  })

  it('keeps pagination above card content for large persona collections', () => {
    const wrapper = mount(PersonaView, {
      global: {
        plugins: [createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            persona: {
              personas: Array.from({ length: 7 }, (_, index) => ({
                id: index + 1,
                owner_id: 1,
                name: `Persona ${index + 1}`,
                bio: 'Bio',
                theories: [],
                stance: 'Neutral',
                is_public: false,
              })),
            },
          },
        }), Antd],
        stubs: {
          RealGodAgentModal: true,
        },
      },
    })

    expect(wrapper.get('.pagination-wrapper').classes()).toContain('pagination-wrapper')
  })
})
