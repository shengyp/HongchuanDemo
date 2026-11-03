<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import type { FoodcomSummary } from '../types'

const emit = defineEmits<{ open: [] }>()
const summary = ref<FoodcomSummary | null>(null)
onMounted(async () => {
  try { summary.value = await api.foodcomSummary() }
  catch { summary.value = null }
})
const fmt = (value?: number) => (value ?? 0).toLocaleString('zh-CN')
</script>

<template>
  <section v-if="summary?.available" class="real-data-hero">
    <div class="real-data-copy"><span class="real-data-kicker">已接入真实食谱数据 · FOOD.COM</span><h2>从真实食谱中发现长尾食材</h2><p>查看食材出现频次、真实共现和关联食谱。营养克数计算仍使用单独的演示食谱。</p><button @click="emit('open')">打开真实食谱分析 <span>↗</span></button></div>
    <div class="real-data-numbers"><div><strong>{{ fmt(summary.recipe_count) }}</strong><span>真实食谱</span></div><div><strong>{{ fmt(summary.ingredient_count) }}</strong><span>食材名称</span></div><div><strong>{{ fmt(summary.tail_count) }}</strong><span>长尾食材</span></div><div><strong>{{ fmt(summary.link_count) }}</strong><span>食谱食材记录</span></div></div>
  </section>
</template>
