<script setup lang="ts">
import { reactive, ref } from 'vue'
import { api } from '../api'
import type { IngredientRow, NutrientKey, Recommendation, Summary } from '../types'

const props = defineProps<{ summary: Summary; ingredients: IngredientRow[]; nutritionDataset: 'current' | 'demo' }>()
const keys: NutrientKey[] = ['energy_kcal', 'protein_g', 'fat_g', 'carbs_g', 'fiber_g', 'sodium_mg']
const targets = reactive<Partial<Record<NutrientKey, number>>>({ energy_kcal: 550, protein_g: 35, fat_g: 20, carbs_g: 60, fiber_g: 8, sodium_mg: 500 })
const likes = ref<string[]>([])
const dislikes = ref<string[]>([])
const results = ref<Recommendation[]>([])
const searched = ref(false)
const busy = ref(false)
const error = ref('')
const fmt = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })

async function recommend(): Promise<void> {
  busy.value = true
  error.value = ''
  try { results.value = await api.recommend(targets, likes.value, dislikes.value, props.nutritionDataset); searched.value = true }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '推荐失败' }
  finally { busy.value = false }
}
</script>

<template>
  <div class="content-page"><div class="page-heading"><div><p class="eyebrow">PERSONALIZED RECIPES</p><h1>食谱推荐{{ summary.is_demo ? '（演示）' : '' }}</h1><p>营养约束与食材偏好共同决定推荐排序。</p></div><span class="soft-badge">{{ summary.recipe_count }} 道食谱可检索</span></div>
    <section class="surface"><div class="section-title"><span class="section-icon">◎</span><div><h2>设置每餐目标</h2><p>纤维为下限，钠为上限；其余数值为目标值。</p></div></div><form @submit.prevent="recommend"><div class="form-grid three"><label v-for="key in keys" :key="key">{{ summary.nutrients[key] }}<input v-model.number="targets[key]" type="number" min="1" step="any"></label></div><div class="form-grid two picker-grid">
  <div class="ingredient-picker">
    <div class="picker-caption"><label for="likes">偏好食材</label><span class="picker-count">已选 {{ likes.length }} 项</span></div>
    <v-autocomplete id="likes" v-model="likes" multiple chips closable-chips clearable label="搜索并选择喜欢的食材" :items="ingredients.map(item => ({ title: item.name + (item.tail ? ' · 长尾' : ''), value: item.id, props: { disabled: dislikes.includes(item.id) } }))" item-title="title" item-value="value" />
    <small>选择后以标签展示；长尾食材会参与补偿候选排序。</small>
  </div>
  <div class="ingredient-picker">
    <div class="picker-caption"><label for="dislikes">排除食材</label><span class="picker-count">已选 {{ dislikes.length }} 项</span></div>
    <v-autocomplete id="dislikes" v-model="dislikes" multiple chips closable-chips clearable label="搜索并选择需要排除的食材" :items="ingredients.map(item => ({ title: item.name, value: item.id, props: { disabled: likes.includes(item.id) } }))" item-title="title" item-value="value" />
    <small>含排除食材的食谱会被过滤，点击 × 可移除。</small>
  </div>
</div><button class="primary" :disabled="busy" type="submit">{{ busy ? '计算中…' : '生成推荐 →' }}</button></form><p v-if="error" class="form-error">{{ error }}</p></section>
    <section v-if="searched" class="results"><div class="results-title"><h2>推荐结果</h2><p>找到 {{ results.length }} 道候选 · 营养匹配 70% + 偏好匹配 30%</p></div><p v-if="!results.length" class="empty">没有满足排除条件的食谱，请调整条件。</p><article v-for="(recipe,index) in results" :key="recipe.id" class="recipe-card"><div class="recipe-main"><div><span class="rank">{{ String(index+1).padStart(2,'0') }}</span><h3>{{ recipe.name }}</h3><p>{{ recipe.ingredients.map(x=>`${x.name} ${fmt(x.grams)}g`).join(' · ') }} · {{ recipe.servings }} 份</p></div><div class="recipe-score"><strong>{{ fmt(recipe.score) }}</strong><span>综合匹配</span></div></div><div class="nutrient-pills"><span v-for="key in keys" :key="key">{{ summary.nutrients[key] }} {{ fmt(recipe.nutrition[key]) }}</span></div><div class="recipe-foot"><span>营养 {{ fmt(recipe.nutrition_score) }}</span><span>偏好 {{ fmt(recipe.preference_score) }}</span><span v-if="recipe.tail_ingredients.length">长尾食材：{{ recipe.tail_ingredients.join('、') }}</span></div><p v-if="recipe.inferred_links.length" class="evidence">补偿候选：{{ recipe.inferred_links.map(x=>`${x.requested} → ${x.matched}`).join('；') }}。仅作为排序线索。</p></article></section>
  </div>
</template>
