import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ModelSelector from './ModelSelector.vue'
import type { ModelInfo } from '../types'

const MODELS: ModelInfo[] = [
  { id: 'amazon.nova-lite-v1:0', display_name: 'Nova Lite', provider: 'Amazon' },
  { id: 'apac.amazon.nova-pro-v1:0', display_name: 'Nova Pro', provider: 'Amazon' },
]

// ant-design-vueの<a-select>はNuxtプラグインとして登録されるため、
// 単体テストでは「値を変更したらupdate:valueイベントを出す」という
// 必要最小限の振る舞いだけを持つ簡易スタブに差し替える。
const SelectStub = {
  props: ['value', 'disabled'],
  emits: ['update:value'],
  template: '<select :disabled="disabled" @change="$emit(\'update:value\', $event.target.value)"><slot /></select>',
}
const OptionStub = {
  props: ['value'],
  template: '<option :value="value"><slot /></option>',
}

function mountSelector(props: { models: ModelInfo[]; modelValue: string | null; disabled: boolean }) {
  return mount(ModelSelector, {
    props,
    global: {
      stubs: {
        ASelect: SelectStub,
        ASelectOption: OptionStub,
      },
    },
  })
}

describe('ModelSelector', () => {
  it('renders one option per model with its display name and provider', () => {
    const wrapper = mountSelector({ models: MODELS, modelValue: null, disabled: false })

    const options = wrapper.findAll('option')
    expect(options).toHaveLength(2)
    expect(options[0]?.text()).toBe('Nova Lite（Amazon）')
    expect(options[1]?.text()).toBe('Nova Pro（Amazon）')
  })

  it('emits update:modelValue with the selected model id', async () => {
    const wrapper = mountSelector({ models: MODELS, modelValue: null, disabled: false })

    await wrapper.find('select').setValue('apac.amazon.nova-pro-v1:0')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['apac.amazon.nova-pro-v1:0'])
  })

  it('disables the select while disabled is true', () => {
    const wrapper = mountSelector({ models: MODELS, modelValue: null, disabled: true })

    expect(wrapper.find('select').attributes('disabled')).toBeDefined()
  })
})
