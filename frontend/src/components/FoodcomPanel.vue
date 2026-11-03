<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import type { FoodcomDetail, FoodcomIngredient, FoodcomSearch, FoodcomSummary } from '../types'

const summary = ref<FoodcomSummary | null>(null)
const searchText = ref('chicken')
const results = ref<FoodcomSearch>({ ingredients: [], recipes: [] })
const selected = ref<FoodcomDetail | null>(null)
const loading = ref(false)
const error = ref('')
const fmt = (n?: number) => (n ?? 0).toLocaleString('zh-CN')

async function search(): Promise<void> {
  loading.value = true
  error.value = ''
  selected.value = null
  try { results.value = await api.foodcomSearch(searchText.value) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '检索失败' }
  finally { loading.value = false }
}
async function choose(item: FoodcomIngredient): Promise<void> {
  error.value = ''
  try { selected.value = await api.foodcomIngredient(item.id) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '食材加载失败' }
}
onMounted(async () => {
  try { summary.value = await api.foodcomSummary(); if (summary.value.available) await search() }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '数据加载失败' }
})
</script>

<template>
  <div class="content-page"><div class="page-heading"><div><p class="eyebrow">FOOD.COM DATA EXPLORER</p><h1>真实食谱与长尾分析</h1><p>基于你提供的 Food.com 食谱清单，统计食材频次和实际共现。</p></div></div>
    <p v-if="error" class="form-error">{{ error }}</p>
    <section v-if="summary?.available" class="surface"><div class="foodcom-stats"><div><strong>{{ fmt(summary.recipe_count) }}</strong><span>食谱</span></div><div><strong>{{ fmt(summary.ingredient_count) }}</strong><span>食材</span></div><div><strong>{{ fmt(summary.tail_count) }}</strong><span>长尾食材</span></div><div><strong>≤ {{ summary.tail_threshold }}</strong><span>长尾频次阈值</span></div></div><p class="muted">{{ summary.note }} 名称保留 Food.com 原始英文；长尾按食材在食谱中出现的次数定义。</p></section>
    <section v-if="summary?.available" class="surface"><div class="section-title"><span class="section-icon">⌕</span><div><h2>搜索食材或食谱</h2><p>输入英文关键词；点击食材查看真实共现与部分关联食谱。</p></div></div><form class="foodcom-search" @submit.prevent="search"><input v-model="searchText" maxlength="100" placeholder="例如 chicken、tofu、rice"><button class="primary" :disabled="loading">{{ loading ? '检索中…' : '搜索' }}</button></form><div class="foodcom-columns"><div><h3>食材 · {{ results.ingredients.length }} 条显示</h3><button v-for="item in results.ingredients" :key="item.id" class="foodcom-list-button" @click="choose(item)"><span>{{ item.name }}</span><small>{{ fmt(item.frequency) }} 道食谱</small></button><p v-if="!results.ingredients.length" class="muted">无匹配食材</p></div><div><h3>食谱 · {{ results.recipes.length }} 条显示</h3><div v-for="item in results.recipes" :key="item.id" class="foodcom-recipe"><strong>{{ item.name }}</strong><small>ID {{ item.id }} · {{ item.ingredient_count }} 种食材</small></div><p v-if="!results.recipes.length" class="muted">无匹配食谱</p></div></div></section>
    <section v-if="selected" class="surface"><div class="section-title"><span class="section-icon">◇</span><div><h2>{{ selected.name }} <em v-if="selected.tail" class="tail-label">长尾</em></h2><p>出现在 {{ fmt(selected.frequency) }} 道食谱中 · 下列均为原始食谱中的实际共现</p></div></div><div class="foodcom-columns"><div><h3>共现食材</h3><button v-for="item in selected.neighbors" :key="item.id" class="foodcom-list-button" @click="choose(item)"><span>{{ item.name }}</span><small>共现 {{ item.cooccur }} 次</small></button></div><div><h3>相关食谱样例</h3><div v-for="item in selected.recipes" :key="item.id" class="foodcom-recipe"><strong>{{ item.name }}</strong><small>ID {{ item.id }}</small></div></div></div></section>
    <section v-if="summary?.available" class="surface"><div class="foodcom-columns"><div><h3>高频食材</h3><button v-for="item in summary.top_ingredients" :key="item.id" class="foodcom-list-button" @click="choose(item)"><span>{{ item.name }}</span><small>{{ fmt(item.frequency) }} 次</small></button></div><div><h3>长尾食材示例</h3><button v-for="item in summary.tail_examples" :key="item.id" class="foodcom-list-button" @click="choose(item)"><span>{{ item.name }}</span><small>{{ fmt(item.frequency) }} 次</small></button></div></div></section>
    <p v-if="summary && !summary.available" class="empty">尚未导入 Food.com 食谱索引。</p>
  </div>
</template>
