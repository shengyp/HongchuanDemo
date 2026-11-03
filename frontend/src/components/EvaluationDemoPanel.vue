<script setup lang="ts">
import { computed, ref } from 'vue'

type Metric = { name: string; baseline: number | null; compensated: number | null }
const experiment = ref('')
const sampleCount = ref<number | null>(null)
const rows = ref<Metric[]>([
  { name: '少见食材被推荐的比例', baseline: null, compensated: null },
  { name: '前 10 条搭配建议命中率', baseline: null, compensated: null },
  { name: '推荐符合需求的比例', baseline: null, compensated: null },
  { name: '营养目标达标率', baseline: null, compensated: null },
])
const result = ref<Metric[] | null>(null)
const resultName = ref('')
const resultCount = ref<number | null>(null)
const message = ref('')
const ready = computed(() => experiment.value.trim() && sampleCount.value !== null && sampleCount.value > 0 &&
  rows.value.every(row => row.baseline !== null && row.compensated !== null &&
    Number.isFinite(Number(row.baseline)) && Number.isFinite(Number(row.compensated)) &&
    Number(row.baseline) >= 0 && Number(row.baseline) <= 100 &&
    Number(row.compensated) >= 0 && Number(row.compensated) <= 100))
function loadExample(): void {
  experiment.value = '演示样例：加入少见食材建议'
  sampleCount.value = 120
  rows.value = [
    { name: '少见食材被推荐的比例', baseline: 36, compensated: 54 },
    { name: '前 10 条搭配建议命中率', baseline: 42, compensated: 51 },
    { name: '推荐符合需求的比例', baseline: 48, compensated: 53 },
    { name: '营养目标达标率', baseline: 68, compensated: 68 },
  ]
  result.value = null
  message.value = '已填入示例数据。数字仅用于体验页面，可直接修改。'
}
function generate(): void {
  if (!ready.value) { message.value = '请填写对比名称、食谱数量和 0–100 范围内的结果。'; return }
  resultName.value = experiment.value.trim()
  resultCount.value = sampleCount.value
  result.value = rows.value.map(row => ({ ...row }))
  message.value = '已生成页面预览。结果来自你填写的数据，尚未经过实际测试。'
}
function clear(): void {
  experiment.value = ''
  sampleCount.value = null
  rows.value = rows.value.map(row => ({ ...row, baseline: null, compensated: null }))
  result.value = null
  message.value = ''
}
function delta(row: Metric): string {
  const value = Number(row.compensated) - Number(row.baseline)
  return (value > 0 ? '+' : '') + value.toFixed(1) + ' 个百分点'
}
</script>

<template>
  <div class="content-page research-page evaluation-demo">
    <header class="page-heading">
      <div><p class="eyebrow">RECIPE COMPARISON</p><h1>食谱效果对比 <span class="evaluation-demo-badge">界面演示</span></h1><p>对同一批食谱，比较加入少见食材搭配建议前后的结果。</p></div>
    </header>
    <div class="evaluation-steps"><div><span>01</span><strong>选定同一批食谱</strong><p>两种方案使用同一批食谱</p></div><div><span>02</span><strong>填写对比结果</strong><p>输入原有方案和新方案的数据</p></div><div><span>03</span><strong>比较结果</strong><p>看看哪些方面有改善</p></div></div>
    <section class="surface evaluation-demo-form">
      <div class="research-section-head"><div><h2>填写对比数据</h2><p>可以先试用示例数据；真实结果请填写实际测试得到的数字。</p></div><span class="soft-badge">前端模拟</span></div>
      <div class="evaluation-demo-config">
        <label>对比名称<input v-model="experiment" placeholder="例如：低频食材补偿对照" maxlength="60"></label>
        <label>参与对比的食谱数量<input v-model.number="sampleCount" type="number" min="1" step="1" placeholder="例如：120"></label>
      </div>
      <div class="evaluation-table-wrap"><table class="evaluation-table"><thead><tr><th>对比内容</th><th>原有方案 (%)</th><th>加入搭配建议 (%)</th></tr></thead><tbody><tr v-for="row in rows" :key="row.name"><td>{{ row.name }}</td><td><input v-model.number="row.baseline" :aria-label="row.name+'无补偿'" type="number" min="0" max="100" step="0.1" placeholder="0–100"></td><td><input v-model.number="row.compensated" :aria-label="row.name+'有补偿'" type="number" min="0" max="100" step="0.1" placeholder="0–100"></td></tr></tbody></table></div>
      <div class="evaluation-demo-actions"><button type="button" @click="loadExample">试用示例数据</button><button class="primary" type="button" @click="generate">查看对比结果</button><button type="button" @click="clear">清空</button></div>
      <p v-if="message" class="evaluation-demo-message" role="status">{{ message }}</p>
    </section>
    <section v-if="result" class="surface">
      <div class="research-section-head"><div><h2>{{ resultName }}</h2><p>同一批食谱 {{ resultCount }} 条 · 根据页面输入生成</p></div><span class="soft-badge">页面预览</span></div>
      <div class="evaluation-result-grid"><article v-for="row in result" :key="row.name" class="evaluation-result-card"><div class="evaluation-result-head"><strong>{{ row.name }}</strong><span :class="{ positive: Number(row.compensated) > Number(row.baseline) }">{{ delta(row) }}</span></div><div class="evaluation-bars"><div><small>原有方案</small><span class="evaluation-track"><i :style="{width: row.baseline + '%'}"></i></span><b>{{ row.baseline }}%</b></div><div><small>加入搭配建议</small><span class="evaluation-track after"><i :style="{width: row.compensated + '%'}"></i></span><b>{{ row.compensated }}%</b></div></div></article></div>
      <p class="research-empty">这里展示的是手工填写的数据。要判断推荐效果，需要用同一批真实食谱测试两种方案。</p>
    </section>
    <section class="surface"><div class="research-section-head"><h2>查看推荐依据</h2></div><div class="evaluation-case"><div><strong>原食谱搭配</strong><p>查看原始食谱里确实出现过的搭配。</p></div><div><strong>新的搭配建议</strong><p>查看建议参考了哪些相似食材和食谱。</p></div><div><strong>对比食谱结果</strong><p>比较推荐是否更合适、营养目标是否达成。</p></div></div></section>
  </div>
</template>

<style scoped>
.evaluation-demo-badge{display:inline-flex;vertical-align:middle;font-size:12px;font-weight:700;color:#087d68;background:#e6f5ed;border:1px solid #a4d5bd;border-radius:999px;padding:5px 11px}
.evaluation-demo-config{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin:20px 0}
.evaluation-demo-config label{display:grid;gap:8px;color:#2d5448;font-weight:650}
.evaluation-demo-config input,.evaluation-table input{width:100%;min-height:42px;border:1px solid #cddfd6;border-radius:10px;padding:9px 12px;background:#fff;color:#183e33;font:inherit}
.evaluation-table input{max-width:160px}
.evaluation-demo-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.evaluation-demo-actions button{border:1px solid #c7ddd1;border-radius:10px;padding:10px 16px;background:#fff;color:#165d4c;font:inherit;font-weight:650;cursor:pointer;white-space:nowrap}
.evaluation-demo-actions button.primary{background:#087d68;border-color:#087d68;color:#fff}
.evaluation-demo-actions button:hover{filter:brightness(.96)}
.evaluation-demo-message{margin:14px 0 0;color:#426a5c}
.evaluation-result-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:20px 0}.evaluation-result-card{padding:18px;border:1px solid #e0ece4;border-radius:14px;background:#fcfefc}.evaluation-result-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:16px}.evaluation-result-head strong{color:#204b3a}.evaluation-result-head span{font-size:12px;color:#7a897d;white-space:nowrap}.evaluation-result-head span.positive{color:#087d68;font-weight:700}.evaluation-bars{display:grid;gap:11px}.evaluation-bars>div{display:grid;grid-template-columns:88px minmax(0,1fr) 47px;gap:10px;align-items:center}.evaluation-bars small{color:#687f70}.evaluation-bars b{font-size:12px;text-align:right;color:#315646}.evaluation-track{height:9px;border-radius:99px;background:#e7eee9;overflow:hidden}.evaluation-track i{display:block;height:100%;border-radius:99px;background:#a8bdad}.evaluation-track.after i{background:#178e70}@media(max-width:760px){.evaluation-result-grid,.evaluation-demo-config{grid-template-columns:1fr}}
</style>
