export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  inputTokens?: number
  outputTokens?: number
  bedrockDurationMs?: number
  totalDurationMs?: number
  estimatedCostUsd?: number | null
}

export interface ChatApiResponse {
  reply: string
  model_id: string
  input_tokens: number
  output_tokens: number
  bedrock_duration_ms: number
  total_duration_ms: number
  estimated_cost_usd: number | null
}

export interface ModelInfo {
  id: string
  display_name: string
  provider: string
}
