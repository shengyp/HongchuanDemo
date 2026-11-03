<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import type { GeneratedRecipe, NutrientKey, RecipeSummary, Summary } from '../types'

const props = defineProps<{ summary: Summary; nutritionDataset: 'current' | 'demo' }>()
const keys: NutrientKey[] = ['energy_kcal', 'protein_g', 'fat_g', 'carbs_g', 'fiber_g', 'sodium_mg']
const targets = reactive<Record<NutrientKey, number>>({ energy_kcal: 550, protein_g: 35, fat_g: 20, carbs_g: 60, fiber_g: 8, sodium_mg: 500 })
const recipes = ref<RecipeSummary[]>([])
const recipeId = ref('')
const result = ref<GeneratedRecipe | null>(null)
const busy = ref(false)
const error = ref('')
const fmt = (n: number) => n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })

onMounted(async () => {
  try { recipes.value = await api.recipes(props.nutritionDataset); recipeId.value = recipes.value[0]?.id ?? '' }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '食谱加载失败' }
})
async function run(): Promise<void> {
  busy.value = true
  error.value = ''
  result.value = null
  try { result.value = await api.generate(recipeId.value, targets, props.nutritionDataset) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '克数优化失败' }
  finally { busy.value = false }
}
</script>

<template>
  <div class="content-page"><div class="page-heading"><div><p class="eyebrow">RECIPE QUANTITY DESIGN</p><h1>食谱克数生成{{ summary.is_demo ? '（演示）' : '' }}</h1><p>选择基础食谱，按每份营养目标调整食材克数，再用食材营养表逐项验算。</p></div></div>
    <section class="surface"><div class="section-title"><span class="section-icon">◈</span><div><h2>设置生成条件</h2><p>纤维按最低值、钠按最高值；其他指标允许目标值 ±5%。</p></div></div><form @submit.prevent="run"><div class="form-grid two"><label>基础食谱<select v-model="recipeId" required><option v-for="item in recipes" :key="item.id" :value="item.id">{{ item.name }}</option></select></label></div><div class="form-grid three"><label v-for="key in keys" :key="key">{{ summary.nutrients[key] }}<input v-model.number="targets[key]" type="number" min="0.01" step="any" required></label></div><button class="primary" type="submit" :disabled="busy || !recipeId">{{ busy ? '计算中…' : '生成并验算 →' }}</button></form><p v-if="error" class="form-error">{{ error }}</p></section>
    <section v-if="result" class="surface"><div class="generation-heading"><div><h2>{{ result.source_name }} · 克数方案</h2><p>{{ result.servings }} 份 · {{ result.method }}</p></div><strong :class="result.passed ? 'validation-pass' : 'validation-fail'">{{ result.passed ? '六项目标通过' : '未全部达标' }}</strong></div><p v-if="!result.passed" class="muted">当前食材组合与克数范围内未找到全部达标的方案，请调整基础食谱或目标；以下为找到的最接近方案。</p><div class="generated-parts"><span v-for="part in result.ingredients" :key="part.id">{{ part.name }} <b>{{ fmt(part.grams) }} g</b></span></div><div class="validation-grid"><div v-for="key in keys" :key="key"><small>{{ summary.nutrients[key] }}</small><strong>{{ fmt(result.nutrition[key]) }}</strong><span>目标 {{ fmt(result.targets[key] ?? 0) }} · 偏差 {{ fmt((result.deviations[key] ?? 0) * 100) }}%</span></div></div><p class="muted">最大约束偏差 {{ fmt(result.max_deviation * 100) }}%。演示数据仅用于算法验证；真实应用须先导入经过核验的食材数据。</p></section>
  </div>
</template>
