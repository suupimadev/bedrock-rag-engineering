<script setup lang="ts">
const props = defineProps<{
  disabled: boolean
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const value = ref('')

const isEmpty = computed(() => value.value.trim().length === 0)

function handleSend() {
  const trimmed = value.value.trim()
  if (!trimmed || props.disabled) return
  emit('send', trimmed)
  value.value = ''
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <a-flex gap="small" align="flex-end" class="chat-input">
    <a-textarea
      v-model:value="value"
      :disabled="disabled"
      placeholder="メッセージを入力... (Enterで送信 / Shift+Enterで改行)"
      :auto-size="{ minRows: 2, maxRows: 6 }"
      @keydown="handleKeydown"
    />
    <a-button type="primary" :disabled="disabled || isEmpty" @click="handleSend">
      送信
    </a-button>
  </a-flex>
</template>
