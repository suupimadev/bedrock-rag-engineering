import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './app.vue'
import { ChatApiError } from './composables/useChatApi'

vi.mock('./composables/useChatApi', async () => {
  const actual = await vi.importActual<typeof import('./composables/useChatApi')>('./composables/useChatApi')
  return {
    ...actual,
    fetchModels: vi.fn(),
    sendChatMessage: vi.fn(),
  }
})

const { fetchModels, sendChatMessage } = await import('./composables/useChatApi')

// ChatInputは実UIを持たないスタブに差し替え、テストから直接@sendを発火できるボタンにする
const ChatInputStub = {
  props: ['disabled'],
  emits: ['send'],
  template: '<button :disabled="disabled" @click="$emit(\'send\', \'こんにちは\')">send</button>',
}

function mountApp() {
  return mount(App, {
    global: {
      stubs: {
        ModelSelector: true,
        MessageList: true,
        ChatInput: ChatInputStub,
      },
    },
  })
}

describe('App', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows an error alert when fetching the model list fails', async () => {
    vi.mocked(fetchModels).mockRejectedValue(new ChatApiError('モデル一覧の取得に失敗しました'))

    const wrapper = mountApp()
    await flushPromises()

    const errorAlert = wrapper.find('.error-alert')
    expect(errorAlert.exists()).toBe(true)
    expect(errorAlert.attributes('message')).toBe('エラー: モデル一覧の取得に失敗しました')
  })

  it('shows no error alert when the model list loads successfully', async () => {
    vi.mocked(fetchModels).mockResolvedValue([{ id: 'amazon.nova-lite-v1:0', display_name: 'Nova Lite', provider: 'Amazon' }])

    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('.error-alert').exists()).toBe(false)
  })

  it('shows an error alert when sending a chat message fails', async () => {
    vi.mocked(fetchModels).mockResolvedValue([])
    vi.mocked(sendChatMessage).mockRejectedValue(new ChatApiError('Bedrock is throttling requests, try again later'))

    const wrapper = mountApp()
    await flushPromises()

    await wrapper.find('button').trigger('click')
    await flushPromises()

    const errorAlert = wrapper.find('.error-alert')
    expect(errorAlert.exists()).toBe(true)
    expect(errorAlert.attributes('message')).toBe('エラー: Bedrock is throttling requests, try again later')
  })
})
