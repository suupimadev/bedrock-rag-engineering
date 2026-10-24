<script setup lang="ts">
import type { Message } from './types'

const messages = ref<Message[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)

async function handleSend(text: string) {
  if (isLoading.value) return

  messages.value.push({ id: crypto.randomUUID(), role: 'user', text })
  isLoading.value = true
  error.value = null

  try {
    const result = await sendChatMessage(text)
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      text: result.reply,
      inputTokens: result.input_tokens,
      outputTokens: result.output_tokens,
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
