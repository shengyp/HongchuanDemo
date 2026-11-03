<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { FoodcomSummary, SourceCatalog } from '../types'

const foodcom = ref<FoodcomSummary | null>(null)
const catalog = ref<SourceCatalog | null>(null)
const loading = ref(true)
const error = ref('')
const tailShare = computed(() => foodcom.value?.ingredient_count && foodcom.value.tail_count != null
  ? (foodcom.value.tail_count / foodcom.value.ingredient_count * 100).toFixed(1) + '%' : '—')
const fmt = (value?: number) => value == null ? '—' : value.toLocaleString('zh-CN')
async function refresh(): Promise<void> {
  loading.value = true
  error.value = ''
  const [a, b] = await Promise.allSettled([api.foodcomSummary(), api.sourceCatalog()])
  foodcom.value = a.status === 'fulfilled' ? a.value : null
  catalog.value = b.status === 'fulfilled' ? b.value : null
  if (a.status === 'rejected' || b.status === 'rejected') error.value = '部分数据源暂时无法读取，请检查本地服务。'
  loading.value = false
}
onMounted(refresh)
</script>

<template>
  <div class="content-page data-quality-page">
    <header class="page-heading"><div><p class="eyebrow">DATA SOURCES</p><h1>数据来源说明</h1><p>看看系统用了哪些数据，以及哪些结果可以直接使用。</p></div><v-btn variant="outlined" color="primary" :loading="loading" @click="refresh">刷新状态</v-btn></header>
    <p v-if="error" class="form-error" role="status">{{ error }}</p>
    <section class="quality-grid" aria-label="数据源概览">
      <v-card variant="outlined" class="quality-card"><span>Food.com 食谱</span><strong>{{ fmt(foodcom?.recipe_count) }}</strong><small>道食谱 · {{ fmt(foodcom?.ingredient_count) }} 种食材</small><v-chip size="small" :color="foodcom?.available ? 'success' : 'warning'" variant="tonal">{{ foodcom?.available ? '可以浏览' : '未就绪' }}</v-chip></v-card>
      <v-card variant="outlined" class="quality-card"><span>少见食材</span><strong>{{ tailShare }}</strong><small>{{ fmt(foodcom?.tail_count) }} 种 · 出现次数 ≤ {{ foodcom?.tail_threshold ?? '—' }}</small><v-chip size="small" color="info" variant="tonal">在少量食谱中出现</v-chip></v-card>
      <v-card variant="outlined" class="quality-card"><span>USDA 营养数据</span><strong>{{ fmt(catalog?.complete_count) }}</strong><small>条营养记录可供查询</small><v-chip size="small" :color="catalog?.source ? 'success' : 'warning'" variant="tonal">{{ catalog?.source ? '可以查询' : '未就绪' }}</v-chip></v-card>
    </section>
    <section class="surface">
      <div class="research-section-head"><div><h2>这些数据怎样一起使用</h2><p>查看真实食谱搭配时可以直接用 Food.com；计算营养前还需要匹配食材和填写用量。</p></div><span class="soft-badge">使用说明</span></div>
      <div class="quality-checks">
        <div><span class="quality-step">01</span><div><strong>先确认是同一种食材</strong><p>例如“鸡胸肉”需要对应到准确的营养记录，避免名称相近却不是同一种食物。</p></div><v-chip size="small" color="warning" variant="tonal">尚未批量匹配</v-chip></div>
        <div><span class="quality-step">02</span><div><strong>再填写每种食材的用量</strong><p>原始食谱清单没有可靠的逐项克数；填入克数后才能计算整道菜的营养。</p></div><v-chip size="small" color="warning" variant="tonal">需要补充</v-chip></div>
        <div><span class="quality-step">03</span><div><strong>最后查看营养来源</strong><p>计算结果应能查看所用的营养记录和食材用量，方便核对。</p></div><v-chip size="small" color="info" variant="tonal">可追溯</v-chip></div>
      </div>
      <v-alert class="quality-alert" type="info" variant="tonal" density="comfortable">Food.com 和 USDA 目前是两套独立数据。上面的数量只表示各自有多少记录；食材还没有全部对齐，所以暂时不能把 Food.com 食谱的营养值当作精确计算结果。</v-alert>
    </section>
  </div>
</template>

<style scoped>
.quality-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:18px}.quality-card{display:flex;flex-direction:column;align-items:flex-start;gap:8px;padding:20px;border-radius:16px!important;background:#fff}.quality-card span{font-size:13px;font-weight:700;color:#547366}.quality-card strong{font-size:30px;line-height:1.1;color:#174e3f}.quality-card small{color:#708b7b}.quality-card .v-chip{margin-top:7px}.quality-checks>div{display:flex;align-items:center;gap:15px;padding:17px 0;border-bottom:1px solid #e4eee7}.quality-checks>div:last-child{border-bottom:0}.quality-step{display:grid;place-items:center;flex:none;width:36px;height:36px;border-radius:10px;background:#e8f4ed;color:#16826a;font-weight:800}.quality-checks>div>div{flex:1;min-width:0}.quality-checks strong{color:#1e4b3a}.quality-checks p{margin:4px 0 0;color:#718b7c;font-size:13px}.quality-alert{margin-top:13px}@media(max-width:820px){.quality-grid{grid-template-columns:1fr}.quality-checks>div{align-items:flex-start;flex-wrap:wrap}.quality-checks .v-chip{margin-left:51px}}
</style>
