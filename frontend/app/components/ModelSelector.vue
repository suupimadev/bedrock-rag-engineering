<script setup lang="ts">
import type { ModelInfo } from '../types'

defineProps<{
  models: ModelInfo[]
  modelValue: string | null
  disabled: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <a-select
    :value="modelValue ?? undefined"
    :disabled="disabled"
    style="width: 240px"
    placeholder="モデルを選択"
    @update:value="(value) => emit('update:modelValue', value as string)"
  >
    <a-select-option v-for="model in models" :key="model.id" :value="model.id">
      {{ model.display_name }}（{{ model.provider }}）
    </a-select-option>
  </a-select>
</template>
