import { FetchError, ofetch } from 'ofetch'
import type { ChatApiResponse } from '../types'

export class ChatApiError extends Error {}

export async function sendChatMessage(message: string): Promise<ChatApiResponse> {
  try {
    return await ofetch<ChatApiResponse>('/api/chat', {
      method: 'POST',
      body: { message },
    })
  } catch (error) {
    if (error instanceof FetchError) {
      const detail =
        error.data && typeof error.data.detail === 'string'
          ? error.data.detail
          : `リクエストに失敗しました (HTTP ${error.statusCode})`
      throw new ChatApiError(detail)
    }
    throw error
  }
}
