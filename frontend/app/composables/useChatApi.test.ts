import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatApiError, fetchModels, sendChatMessage } from './useChatApi'

describe('sendChatMessage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the parsed response on success', async () => {
    const mockResponse = {
      reply: 'こんにちは',
      model_id: 'amazon.nova-lite-v1:0',
      input_tokens: 5,
      output_tokens: 8,
      bedrock_duration_ms: 345.6,
      total_duration_ms: 350.2,
      estimated_cost_usd: 0.000003,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(mockResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    const result = await sendChatMessage('こんにちは')

    expect(result).toEqual(mockResponse)
  })

  it('throws ChatApiError with the backend detail message on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        async () =>
          new Response(JSON.stringify({ detail: 'Bedrock is throttling requests, try again later' }), {
            status: 429,
            headers: { 'Content-Type': 'application/json' },
          }),
      ),
    )

    await expect(sendChatMessage('hello')).rejects.toThrow(ChatApiError)
    await expect(sendChatMessage('hello')).rejects.toThrow('Bedrock is throttling requests, try again later')
  })

  it('throws ChatApiError using the first message from a FastAPI validation error array', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        async () =>
          new Response(
            JSON.stringify({
              detail: [{ type: 'value_error', loc: ['body', 'model_id'], msg: "Value error, model_id 'x' is not in the allowed list" }],
            }),
            { status: 422, headers: { 'Content-Type': 'application/json' } },
          ),
      ),
    )

    await expect(sendChatMessage('hello', 'x')).rejects.toThrow(ChatApiError)
    await expect(sendChatMessage('hello', 'x')).rejects.toThrow('is not in the allowed list')
  })
})

describe('fetchModels', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the list of available models', async () => {
    const mockModels = [
      { id: 'amazon.nova-lite-v1:0', display_name: 'Nova Lite', provider: 'Amazon' },
      { id: 'apac.amazon.nova-pro-v1:0', display_name: 'Nova Pro', provider: 'Amazon' },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(mockModels), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    const result = await fetchModels()

    expect(result).toEqual(mockModels)
  })
})
