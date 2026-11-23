<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ChatApiError, fetchModels, sendChatMessage } from './composables/useChatApi'
import type { Message, ModelInfo } from './types'

const messages = ref<Message[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const models = ref<ModelInfo[]>([])
const selectedModelId = ref<string | null>(null)

onMounted(async () => {
  try {
    models.value = await fetchModels()
    if (models.value.length > 0 && models.value[0]) {
      selectedModelId.value = models.value[0].id
    }
  } catch (err) {
    error.value = err instanceof ChatApiError ? err.message : 'モデル一覧の取得に失敗しました'
  }
})

async function handleSend(text: string) {
  if (isLoading.value) return

  messages.value.push({ id: crypto.randomUUID(), role: 'user', text })
  isLoading.value = true
  error.value = null

  try {
    const result = await sendChatMessage(text, selectedModelId.value ?? undefined)
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      text: result.reply,
      inputTokens: result.input_tokens,
      outputTokens: result.output_tokens,
      bedrockDurationMs: result.bedrock_duration_ms,
      totalDurationMs: result.total_duration_ms,
      estimatedCostUsd: result.estimated_cost_usd,
    })
  } catch (err) {
    error.value = err instanceof ChatApiError ? err.message : 'ネットワークエラーが発生しました'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <a-flex justify="center" class="page">
    <a-card class="app-card" :bordered="false">
      <a-typography-title :level="3">Bedrock RAG Engineering - Chat</a-typography-title>
      <a-alert
        type="info"
        show-icon
        class="notice"
        message="このチャットは単発質問のみに対応しています。画面には会話履歴が表示されますが、Bedrockへは毎回最新のメッセージのみを送信し、過去の履歴は送信しません。"
      />
      <ModelSelector v-model="selectedModelId" :models="models" :disabled="isLoading" class="model-selector" />
      <MessageList :messages="messages" />
      <a-flex v-if="isLoading" align="center" gap="small" class="loading-row">
        <a-spin size="small" />
        <span>AIが応答を生成しています...</span>
      </a-flex>
      <a-alert
        v-if="error"
        type="error"
        show-icon
        closable
        class="error-alert"
        :message="`エラー: ${error}`"
        @close="error = null"
      />
      <ChatInput :disabled="isLoading" @send="handleSend" />
    </a-card>
  </a-flex>
</template>
