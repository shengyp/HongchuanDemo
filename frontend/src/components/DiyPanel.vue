<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import type { DiyAssessment, IngredientRow, NutrientKey, Summary } from '../types'

const props = defineProps<{ ingredients: IngredientRow[]; summary: Summary; nutritionDataset: 'current' | 'demo' }>()
const keys: NutrientKey[] = ['energy_kcal', 'protein_g', 'fat_g', 'carbs_g', 'fiber_g', 'sodium_mg']
const defaults: Record<NutrientKey, number> = { energy_kcal: 550, protein_g: 35, fat_g: 20, carbs_g: 60, fiber_g: 8, sodium_mg: 500 }
const parts = ref<{ id: string; grams: number }[]>([])
const servings = ref(1)
const recipeName = ref('')
const targets = reactive<Record<NutrientKey, number>>({ ...defaults })
const result = ref<DiyAssessment | null>(null)
const busy = ref(false)
const error = ref('')
const fmt = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const mappedLabel = computed(() => result.value?.evidence.mapped.map(item => item.local_name + ' → ' + item.foodcom_name) ?? [])

onMounted(() => {
  if (props.ingredients[0]) parts.value = [{ id: props.ingredients[0].id, grams: 100 }]
})
watch([parts, servings, targets], () => { result.value = null }, { deep: true })
function addPart(): void {
  const unused = props.ingredients.find(item => !parts.value.some(part => part.id === item.id))
  if (unused) parts.value.push({ id: unused.id, grams: 100 })
}
function removePart(index: number): void { parts.value.splice(index, 1) }
function reset(): void {
  parts.value = props.ingredients[0] ? [{ id: props.ingredients[0].id, grams: 100 }] : []
  servings.value = 1
  Object.assign(targets, defaults)
  recipeName.value = ''
  result.value = null
  error.value = ''
}
async function assess(): Promise<void> {
  error.value = ''
  if (!parts.value.length || parts.value.some(part => !part.id || !Number.isFinite(part.grams) || part.grams <= 0)) {
    error.value = '请填写有效食材及克数。'; return
  }
  if (new Set(parts.value.map(part => part.id)).size !== parts.value.length) {
    error.value = '同一种食材只需填写一次。'; return
  }
  if (!Number.isInteger(servings.value) || servings.value < 1 || keys.some(key => !Number.isFinite(targets[key]) || targets[key] <= 0)) {
    error.value = '份数须为正整数，六项营养目标须大于 0。'; return
  }
  busy.value = true
  try { result.value = await api.diyAssess(parts.value, servings.value, { ...targets }, props.nutritionDataset) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '食谱评分失败' }
  finally { busy.value = false }
}
</script>

<template>
  <div class="dc-page">
    <header class="dc-heading"><div><p class="dc-kicker">DIY RECIPE EVIDENCE ASSESSMENT</p><h2>DIY 食谱证据与营养评估</h2><p>输入食材和克数，先检索相关真实食谱，再分别计算搭配证据与营养目标得分。</p></div><span class="dc-source-badge">{{ summary.dataset_title }}</span></header>
    <div class="dc-intro"><span>01 填写食谱</span><i>→</i><span>02 查找相关食谱</span><i>→</i><span>03 查看评分与依据</span></div>
    <div class="dc-form-grid">
      <section class="dc-card"><div class="dc-card-head"><div><span>RECIPE INPUT</span><h3>待评估 DIY 食谱</h3><p>食材用量为整道食谱的可食部重量</p></div><button class="dc-light-button" @click="addPart">＋ 添加食材</button></div>
        <label class="dc-name">食谱名称（可选）<input v-model="recipeName" maxlength="100" placeholder="例如：菠菜豆腐米饭"></label>
        <div class="dc-parts"><div v-for="(part,index) in parts" :key="index" class="dc-part-row"><span class="dc-part-index">{{ String(index+1).padStart(2,'0') }}</span><label>食材<select v-model="part.id"><option v-for="item in ingredients" :key="item.id" :value="item.id" :disabled="parts.some((other,i) => i!==index && other.id===item.id)">{{ item.name }}{{ item.tail ? ' · 长尾' : '' }}</option></select></label><label>用量（g）<input v-model.number="part.grams" type="number" min="0.1" max="5000" step="0.1"></label><button class="dc-remove" :disabled="parts.length<2" :aria-label="'删除第'+(index+1)+'种食材'" @click="removePart(index)">×</button></div></div>
        <p v-if="!ingredients.length" class="dc-hint">暂无食材，请先在数据管理中导入营养食材表。</p>
        <label class="dc-servings">食谱份数<input v-model.number="servings" type="number" min="1" max="100" step="1"></label>
        <p class="dc-hint">至少选择两种食材，才能计算搭配证据支持分。</p>
      </section>
      <section class="dc-card"><div class="dc-card-head"><div><span>NUTRITION TARGETS</span><h3>每份营养目标</h3><p>纤维为下限，钠为上限，其余为目标值</p></div></div>
        <div class="dc-target-grid"><label v-for="key in keys" :key="key">{{ summary.nutrients[key] }}<input v-model.number="targets[key]" type="number" min="0.01" step="any"></label></div>
        <div class="dc-form-actions"><button class="dc-primary" :disabled="busy || !ingredients.length" @click="assess">{{ busy ? '正在查找食谱并评分…' : '查找相关食谱并评分 →' }}</button><button class="dc-light-button" @click="reset">重置</button></div>
        <p v-if="error" class="dc-error" role="alert">{{ error }}</p>
        <div class="dc-method-note"><strong>评分说明</strong><p>证据支持分基于 Food.com 已观察的食材共现次数、成对覆盖率和相关食谱相似度；营养匹配分依据当前食材营养表计算。两项分数均不是经过校准的概率。</p></div>
      </section>
    </div>
    <section v-if="!result" class="dc-empty"><span>◇</span><h3>等待食谱评分</h3><p>填写 DIY 食谱后点击“查找相关食谱并评分”，这里将展示真实食谱和逐项依据。</p></section>
    <template v-else>
      <section class="dc-results"><div class="dc-result-head"><div><span>ASSESSMENT RESULT</span><h3>{{ recipeName || 'DIY 食谱' }} · 评分结果</h3><p>{{ result.parts.map(item => item.name + ' ' + fmt(item.grams) + ' g').join(' / ') }} · {{ result.servings }} 份</p></div><span :class="result.is_demo_nutrition ? 'dc-demo-badge' : 'dc-real-badge'">{{ result.is_demo_nutrition ? '营养表为演示数据' : '营养表来自当前导入数据' }}</span></div>
        <div class="dc-score-grid"><article><div><span>食谱搭配证据支持分</span><strong>{{ result.evidence.support_score===null ? '—' : fmt(result.evidence.support_score) }}</strong><small>/ 100 · 来自真实食谱索引</small></div><div class="dc-progress"><i :style="{width:(result.evidence.support_score ?? 0)+'%'}"></i></div><p>已观察搭配 {{ result.evidence.pair_supported }} / {{ result.evidence.pair_total }} 组</p></article><article><div><span>营养目标匹配分</span><strong>{{ fmt(result.nutrition_score) }}</strong><small>/ 100 · 来自食材每 100 g 营养值</small></div><div class="dc-progress nutrition"><i :style="{width:result.nutrition_score+'%'}"></i></div><p>{{ result.checks.filter(item=>item.passed).length }} / 6 项营养目标达标</p></article></div>
        <div class="dc-score-note"><strong>结果解读</strong><p>{{ result.evidence.note }} 证据支持分用于说明当前食谱在所选数据源中的搭配依据，不代表食用安全性或临床结论。</p></div>
      </section>
      <div class="dc-evidence-grid"><section class="dc-card"><div class="dc-card-head"><div><span>RELATED RECIPES</span><h3>相关真实食谱</h3><p>Food.com 原始食谱中与本次食材重合的记录</p></div><small>{{ result.evidence.related_recipes.length }} 道</small></div><div v-if="result.evidence.related_recipes.length" class="dc-recipe-list"><div v-for="item in result.evidence.related_recipes" :key="item.id"><span class="dc-recipe-mark">R</span><div><strong>{{ item.name }}</strong><small>Food.com #{{ item.id }} · 重合 {{ item.overlap }} 种食材 / 原食谱 {{ item.ingredient_count }} 种</small></div><b>{{ (item.similarity*100).toFixed(0) }}%</b></div></div><p v-else class="dc-hint">没有检索到相关食谱。请检查食材映射或导入更多食材。</p><div class="dc-mapping"><strong>食材名称映射</strong><p>{{ mappedLabel.join('；') || '暂无精确映射' }}</p><small v-if="result.evidence.unmapped.length">未映射：{{ result.evidence.unmapped.join('、') }}</small></div></section>
        <section class="dc-card"><div class="dc-card-head"><div><span>PAIR EVIDENCE</span><h3>食材搭配证据</h3><p>统计两种食材在同一道真实食谱中的共同出现</p></div><small>{{ result.evidence.pair_supported }} / {{ result.evidence.pair_total }} 组</small></div><div v-if="result.evidence.pairs.length" class="dc-pair-list"><div v-for="(pair,index) in result.evidence.pairs" :key="index"><div><strong>{{ pair.first }} ＋ {{ pair.second }}</strong><span :class="pair.count ? 'supported' : 'unknown'">{{ pair.count ? '共现 '+pair.count+' 道' : pair.mapped ? '未观察到共现' : '名称未映射' }}</span></div><p v-if="pair.examples.length">例：<span v-for="example in pair.examples" :key="example.id">{{ example.name }}（#{{ example.id }}）　</span></p></div></div><p v-else class="dc-hint">请添加第二种食材以查看搭配证据。</p></section></div>
      <section class="dc-card dc-nutrition"><div class="dc-card-head"><div><span>NUTRITION CHECK</span><h3>六项营养逐项验算</h3><p>按食材克数与份数计算每份营养值</p></div><span :class="result.nutrition_passed ? 'dc-pass' : 'dc-fail'">{{ result.nutrition_passed ? '全部达标' : '部分未达标' }}</span></div><div class="dc-check-grid"><article v-for="item in result.checks" :key="item.key" :class="{passed:item.passed}"><div><span>{{ summary.nutrients[item.key] }}</span><b>{{ item.passed ? '达标' : '未达标' }}</b></div><strong>{{ fmt(item.actual) }}</strong><small>目标 {{ fmt(item.target) }} · 偏差 {{ fmt(item.deviation*100) }}%</small></article></div><p v-if="result.is_demo_nutrition" class="dc-demo-note">当前营养值使用功能演示数据；正式分析需先导入真实食材营养表。Food.com 食谱记录不提供这里的克数与营养值，两类数据分别展示。</p></section>
    </template>
  </div>
</template>

