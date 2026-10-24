export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  inputTokens?: number
  outputTokens?: number
}

export interface ChatApiResponse {
  reply: string
  model_id: string
  input_tokens: number
  output_tokens: number
}
