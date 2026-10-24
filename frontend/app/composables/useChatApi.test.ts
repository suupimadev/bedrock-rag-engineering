import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatApiError, sendChatMessage } from './useChatApi'

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
})
