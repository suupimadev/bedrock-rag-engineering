<script setup lang="ts">
import type { Message } from '../types'

defineProps<{
  messages: Message[]
}>()
</script>

<template>
  <a-empty
    v-if="messages.length === 0"
    description="まだメッセージがありません。下の欄から質問してみてください。"
  />
  <a-list v-else class="message-list" :data-source="messages" :split="false">
    <template #renderItem="{ item }">
      <a-list-item :class="['message-item', item.role]">
        <a-list-item-meta>
          <template #title>
            <a-tag :color="item.role === 'user' ? 'blue' : 'green'">
              {{ item.role === 'user' ? 'あなた' : 'AI' }}
            </a-tag>
          </template>
          <template #description>
            <div class="message-text">{{ item.text }}</div>
            <a-typography-text
              v-if="item.role === 'assistant' && item.inputTokens !== undefined && item.outputTokens !== undefined"
              type="secondary"
              class="message-tokens"
            >
              入力: {{ item.inputTokens }} tokens / 出力: {{ item.outputTokens }} tokens
            </a-typography-text>
          </template>
        </a-list-item-meta>
      </a-list-item>
    </template>
  </a-list>
</template>
