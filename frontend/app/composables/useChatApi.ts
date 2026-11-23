import { FetchError, ofetch } from 'ofetch'
import type { ChatApiResponse, ModelInfo } from '../types'

export class ChatApiError extends Error {}

function extractErrorDetail(error: FetchError, fallbackStatus: number | undefined): string {
  const detail = error.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  // FastAPI/Pydanticのバリデーションエラーは {"detail": [{"msg": "..."}, ...]} という配列形式で返る
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') {
    return detail[0].msg
  }
  return `リクエストに失敗しました (HTTP ${fallbackStatus})`
}

export async function sendChatMessage(message: string, modelId?: string): Promise<ChatApiResponse> {
  try {
    return await ofetch<ChatApiResponse>('/api/chat', {
      method: 'POST',
      body: { message, model_id: modelId ?? null },
    })
  } catch (error) {
    if (error instanceof FetchError) {
      throw new ChatApiError(extractErrorDetail(error, error.statusCode))
    }
    throw error
  }
}

export async function fetchModels(): Promise<ModelInfo[]> {
  try {
    return await ofetch<ModelInfo[]>('/api/models')
  } catch (error) {
    if (error instanceof FetchError) {
      throw new ChatApiError(extractErrorDetail(error, error.statusCode))
    }
    throw error
  }
}
