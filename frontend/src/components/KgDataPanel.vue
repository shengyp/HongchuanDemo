<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { FoodcomGraphStatistics, FoodcomGraphTriplePage, FoodcomSummary, KgSummary, KgTriplePage } from '../types'

const emit = defineEmits<{ (event: 'open-foodcom'): void }>()

const summary = ref<KgSummary | null>(null)
const foodcom = ref<FoodcomSummary | null>(null)
const foodcomStats = ref<FoodcomGraphStatistics | null>(null)
const foodcomTriples = ref<FoodcomGraphTriplePage | null>(null)
const deleteDialog = ref(false)
const deleting = ref(false)
const datasetNotice = ref('')
const selectedKgDataset = computed(() => selectedDataset.value === 'foodcom' ? null : summary.value?.datasets.find(item => item.id === selectedDataset.value) ?? null)
const selectedDataset = ref<number | 'foodcom'>('foodcom')
const renameName = ref('')
const renaming = ref(false)
const triples = ref<KgTriplePage | null>(null)
const file = ref<File | null>(null)
const name = ref('')
const source = ref('')
const search = ref('')
const page = ref(1)
const busy = ref(false)
const loading = ref(true)
const error = ref('')
const success = ref('')
const selectedId = computed(() => selectedDataset.value === 'foodcom' ? 0 : selectedDataset.value)
const bins = computed(() => summary.value?.confidence_bins ?? [])
const maxBin = computed(() => Math.max(1, ...bins.value.map(item => item.count)))
const totalPages = computed(() => Math.max(1, Math.ceil(((selectedDataset.value === 'foodcom' ? foodcomTriples.value : triples.value)?.total ?? 0) / 20)))

async function load(datasetId?: number): Promise<void> {
  summary.value = await api.kgSummary(datasetId)
  if (selectedDataset.value !== 'foodcom' && summary.value.dataset) {
    triples.value = await api.kgTriples(summary.value.dataset.id, search.value, page.value)
  } else {
    triples.value = null
  }
}
onMounted(async () => {
  try {
    await load()
    foodcom.value = await api.foodcomSummary()
    if (foodcom.value.available) [foodcomStats.value, foodcomTriples.value] = await Promise.all([api.foodcomGraphStatistics(), api.foodcomGraphTriples('', 1)])
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '数据集加载失败' }
  finally { loading.value = false }
})
function pick(event: Event): void {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  if (file.value) name.value = ''
  error.value = ''
  success.value = ''
}
async function upload(): Promise<void> {
  error.value = ''
  success.value = ''
  datasetNotice.value = ''
  if (!file.value) { error.value = '请先选择 CSV 或 JSON 文件'; return }
  if (!name.value.trim()) { error.value = '请填写数据集名称'; return }
  if (!/\.(csv|json)$/i.test(file.value.name)) { error.value = '仅支持 CSV 或 JSON 文件'; return }
  if (file.value.size > 20_000_000) { error.value = '文件不能超过 20 MB'; return }
  busy.value = true
  try {
    const result = await api.kgImport(file.value.name, await file.value.text(), name.value.trim(), source.value.trim())
    summary.value = result
    selectedDataset.value = result.dataset!.id
    renameName.value = result.dataset!.name
    page.value = 1
    search.value = ''
    triples.value = await api.kgTriples(result.dataset!.id, '', 1)
    success.value = '已导入 ' + result.dataset!.triple_count.toLocaleString() + ' 条三元组，图谱统计已更新。'
    file.value = null
    const input = document.getElementById('kg-file') as HTMLInputElement | null
    if (input) input.value = ''
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '上传失败' }
  finally { busy.value = false }
}
async function changeDataset(id: number | 'foodcom'): Promise<void> {
  selectedDataset.value = id
  error.value = ''
  datasetNotice.value = ''
  page.value = 1
  search.value = ''
  if (id === 'foodcom') { triples.value = null; renameName.value = ''; if (foodcom.value?.available) foodcomTriples.value = await api.foodcomGraphTriples('', 1); return }
  try {
    await load(id)
    renameName.value = summary.value?.dataset?.name ?? ''
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '切换失败' }
}
async function saveName(): Promise<void> {
  if (selectedDataset.value === 'foodcom' || renaming.value) return
  if (!renameName.value.trim()) { error.value = '请填写数据集名称'; return }
  renaming.value = true
  error.value = ''
  success.value = ''
  try {
    summary.value = await api.kgRename(selectedDataset.value, renameName.value.trim())
    renameName.value = summary.value.dataset?.name ?? renameName.value
    success.value = '数据集已重命名为“' + renameName.value + '”。'
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '重命名失败' }
  finally { renaming.value = false }
}
async function deleteSelected(): Promise<void> {
  if (selectedDataset.value === 'foodcom' || deleting.value || !selectedKgDataset.value) return
  deleting.value = true
  error.value = ''
  const deletedName = selectedKgDataset.value.name
  try {
    summary.value = await api.kgDelete(selectedDataset.value)
    selectedDataset.value = 'foodcom'
    renameName.value = ''
    triples.value = null
    page.value = 1
    search.value = ''
    deleteDialog.value = false
    datasetNotice.value = '已删除“' + deletedName + '”及其关联发现任务。Food.com 数据未受影响。'
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '删除失败'; deleteDialog.value = false }
  finally { deleting.value = false }
}
function count(value?: number): string { return (value ?? 0).toLocaleString('zh-CN') }
async function searchTriples(nextPage = 1): Promise<void> {
  page.value = nextPage
  try {
    if (selectedDataset.value === 'foodcom') foodcomTriples.value = await api.foodcomGraphTriples(search.value, page.value)
    else triples.value = await api.kgTriples(selectedId.value, search.value, page.value)
  }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '检索失败' }
}
function downloadTemplate(): void {
  const csv = '\uFEFFhead,relation,tail,confidence,evidence,source,head_type,tail_type\n菠菜,富含,铁,0.85,示例证据,示例来源,食材,营养素\n'
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = '不确定知识三元组模板.csv'
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="kg-page">
    <div class="kg-heading">
      <div><p class="kg-eyebrow">UNCERTAIN KNOWLEDGE MANAGEMENT</p><h2>不确定知识管理</h2><p>上传带置信度的知识三元组，查看当前数据集形成的图谱结构与证据记录。</p></div>
      <button class="kg-light-button" type="button" @click="downloadTemplate">下载 CSV 模板</button>
    </div>

    <section class="kg-upload">
      <div class="kg-section-title"><span class="kg-step">01</span><div><h3>数据集上传</h3><p>先选择 CSV 或 JSON 文件，再为数据集命名；每次上传保存为独立数据集。</p></div></div>
      <div class="kg-upload-grid">
        <label class="kg-file-box" for="kg-file">
          <input id="kg-file" type="file" accept=".csv,.json,text/csv,application/json" @change="pick">
          <span class="kg-upload-icon">↑</span>
          <strong>{{ file ? file.name : '选择三元组数据集' }}</strong>
          <small>{{ file ? (file.size / 1024).toFixed(1) + ' KB · 已选择' : '点击选择 CSV / JSON 文件，最大 20 MB' }}</small>
        </label>
        <div class="kg-upload-fields">
          <label>数据集名称 <b class="kg-required">*</b><input v-model="name" maxlength="100" placeholder="选择文件后填写名称"></label>
          <label>数据来源<input v-model="source" maxlength="300" placeholder="例如：研究团队整理（可选）"></label>
          <button class="kg-primary-button" type="button" :disabled="busy" @click="upload">{{ busy ? '正在导入…' : '上传并构建图谱' }} <span>→</span></button>
        </div>
      </div>
      <p class="kg-format">必需字段：<code>head</code>、<code>relation</code>、<code>tail</code>、<code>confidence</code>（0–1）；可选：<code>evidence</code>、<code>source</code>、<code>head_type</code>、<code>tail_type</code>。</p>
      <p v-if="error" class="kg-error" role="alert">{{ error }}</p>
      <p v-if="success" class="kg-success" role="status">{{ success }}</p>
    </section>

    <div v-if="loading" class="kg-empty">正在读取数据集…</div>
    <template v-else>
      <section class="kg-datasets">
        <div class="kg-section-title"><span class="kg-step">02</span><div><h3>数据集列表</h3><p>选择一个数据集，下方展示对应的数据概览和明细。</p></div></div>
        <div class="kg-dataset-grid">
          <button class="kg-dataset-card" :class="{active:selectedDataset==='foodcom'}" :aria-pressed="selectedDataset==='foodcom'" @click="changeDataset('foodcom')">
            <span class="kg-dataset-top"><strong>Food.com 食谱数据</strong><em>已接入</em></span>
            <span class="kg-dataset-kind">真实食谱索引 · 默认数据集</span>
            <span class="kg-dataset-meta">{{ foodcom?.available ? count(foodcom.recipe_count) + ' 道食谱 · ' + count(foodcom.ingredient_count) + ' 种食材' : '尚未导入 Food.com 索引' }}</span>
            <small>{{ foodcom?.source ?? 'Food.com' }}</small>
          </button>
          <button v-for="item in summary?.datasets ?? []" :key="item.id" class="kg-dataset-card" :class="{active:selectedDataset===item.id}" :aria-pressed="selectedDataset===item.id" @click="changeDataset(item.id)">
            <span class="kg-dataset-top"><strong>{{ item.name }}</strong><em>已上传</em></span>
            <span class="kg-dataset-kind">知识三元组数据集</span>
            <span class="kg-dataset-meta">{{ count(item.triple_count) }} 条关系 · {{ item.filename }}</span>
            <small>{{ item.source }} · {{ item.imported_at.slice(0,10) }}</small>
          </button>
        </div>
        <form v-if="selectedDataset!=='foodcom'" class="kg-rename" @submit.prevent="saveName">
          <label>当前数据集名称<input v-model="renameName" maxlength="100" aria-label="当前数据集名称" placeholder="输入新的数据集名称"></label>
          <button type="submit" :disabled="renaming || !renameName.trim()">{{ renaming ? '保存中…' : '保存名称' }}</button>
          <button class="kg-delete-trigger" type="button" @click="deleteDialog=true">删除数据集</button>
          <small>重命名只修改显示名称；删除将移除三元组及关联发现任务。</small>
        </form>
        <p v-if="datasetNotice" class="kg-success" role="status">{{ datasetNotice }}</p>
        <div v-if="deleteDialog && selectedKgDataset" class="kg-delete-backdrop" @click.self="deleteDialog=false">
          <section class="kg-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="kg-delete-title">
            <span class="kg-delete-icon">!</span>
            <h3 id="kg-delete-title">删除数据集？</h3>
            <p>将永久删除 <strong>{{ selectedKgDataset.name }}</strong>、{{ count(selectedKgDataset.triple_count) }} 条三元组及关联发现任务。此操作无法撤销。</p>
            <div><button type="button" @click="deleteDialog=false">取消</button><button class="kg-delete-confirm" type="button" :disabled="deleting" @click="deleteSelected">{{ deleting ? '删除中…' : '确认删除' }}</button></div>
          </section>
        </div>
      </section>

      <section v-if="selectedDataset==='foodcom' && foodcom?.available" class="kg-foodcom-overview">
        <div class="kg-foodcom-head"><div class="kg-section-title"><span class="kg-step">03</span><div><h3>图谱概览 · Food.com</h3><p>基于真实食谱与食材组成关系构建的二部图。</p></div></div><button class="kg-light-button" @click="emit('open-foodcom')">查看食谱明细 →</button></div>
        <div class="kg-status"><span class="kg-status-dot"></span><div><strong>当前选中 Food.com</strong><small>{{ foodcom.source }} · {{ foodcom.source_file }}</small></div></div>
        <div class="kg-stats">
          <article><span>食谱</span><strong>{{ count(foodcom.recipe_count) }}</strong><small>真实食谱记录</small></article>
          <article><span>食材</span><strong>{{ count(foodcom.ingredient_count) }}</strong><small>原始食材名称</small></article>
          <article><span>长尾食材</span><strong>{{ count(foodcom.tail_count) }}</strong><small>频次 ≤ {{ foodcom.tail_threshold }}</small></article>
          <article><span>食材与食谱关联</span><strong>{{ count(foodcom.link_count) }}</strong><small>食谱组成记录</small></article>
        </div>
        <div class="kg-foodcom-examples"><div><h4>高频食材示例</h4><p v-for="item in foodcom.top_ingredients?.slice(0,5)" :key="item.id"><strong>{{ item.name }}</strong><span>{{ count(item.frequency) }} 道食谱</span></p></div><div><h4>长尾食材示例</h4><p v-for="item in foodcom.tail_examples?.slice(0,5)" :key="item.id"><strong>{{ item.name }}</strong><span>{{ count(item.frequency) }} 道食谱</span></p></div></div>
        <p class="kg-foodcom-note">{{ foodcom.note }} Food.com 食谱索引与上传的三元组图谱分别管理，不能把食谱关联数当作三元组关系数。</p>
      </section>
      <section v-if="selectedDataset==='foodcom' && foodcomStats?.available" class="kg-insights">
        <div class="kg-section-title"><span class="kg-step">04</span><div><h3>图谱统计</h3><p>节点和关系均来自已观察的食谱组成；食材频次表示出现在多少道食谱中。</p></div></div>
        <div class="kg-stats kg-foodcom-graph-stats">
          <article><span>节点总数</span><strong>{{ count(foodcomStats.node_count) }}</strong><small>食谱 + 食材</small></article>
          <article><span>关系总数</span><strong>{{ count(foodcomStats.edge_count) }}</strong><small>真实食谱组成</small></article>
          <article><span>实体类型</span><strong>{{ foodcomStats.entity_type_count }}</strong><small>食谱、食材</small></article>
          <article><span>关系类型</span><strong>{{ foodcomStats.relation_type_count }}</strong><small>包含食材</small></article>
        </div>
        <div class="kg-insight-grid">
          <article class="kg-chart-card"><div class="kg-card-head"><div><span>INGREDIENT FREQUENCY</span><h4>食材出现频次分布</h4></div></div>
            <div class="kg-bars"><div v-for="item in foodcomStats.frequency_bins" :key="item.label" class="kg-bar-item"><span class="kg-bar-count">{{ count(item.count) }}</span><div class="kg-bar-track"><div :style="{ height: Math.max(4, item.count / Math.max(1,...foodcomStats.frequency_bins.map(bin=>bin.count)) * 100) + '%' }"></div></div><small>{{ item.label }}</small></div></div>
            <p class="kg-foodcom-note">横轴为出现的食谱数（21+ 表示至少 21 道）；纵向柱高为对应食材数量。</p>
          </article>
          <div class="kg-type-stack">
            <article class="kg-type-card"><div class="kg-card-head"><div><span>NODE TYPES</span><h4>实体类型分布</h4></div></div><div class="kg-chips"><span v-for="item in foodcomStats.node_types" :key="item.name">{{ item.name }} <b>{{ count(item.count) }}</b></span></div></article>
            <article class="kg-type-card"><div class="kg-card-head"><div><span>RELATION TYPES</span><h4>关系类型分布</h4></div></div><div class="kg-chips relation"><span v-for="item in foodcomStats.relation_types" :key="item.name">{{ item.name }} <b>{{ count(item.count) }}</b></span></div></article>
          </div>
        </div>
      </section>
      <section v-if="selectedDataset==='foodcom' && foodcom?.available" class="kg-table-section">
        <div class="kg-table-top"><div class="kg-section-title"><span class="kg-step">05</span><div><h3>三元组明细</h3><p>真实食谱 → 包含食材 → 食材。该数据源未提供关系置信度。</p></div></div><form class="kg-search" @submit.prevent="searchTriples(1)"><input v-model="search" placeholder="检索食谱或食材" aria-label="检索 Food.com 三元组"><button type="submit">查询</button></form></div>
        <div class="kg-table-scroll"><table><thead><tr><th>食谱 ID</th><th>起始实体（食谱）</th><th>关系</th><th>目标实体（食材）</th><th>食材出现频次</th><th>来源</th></tr></thead><tbody><tr v-for="item in foodcomTriples?.items" :key="item.recipe_id+'-'+item.ingredient_id"><td class="kg-muted">{{ item.recipe_id }}</td><td><strong>{{ item.recipe_name }}</strong><small>食谱</small></td><td><span class="kg-relation">包含食材</span></td><td><strong>{{ item.ingredient_name }}</strong><small>食材 ID {{ item.ingredient_id }}</small></td><td>{{ count(item.ingredient_frequency) }} 道食谱</td><td>Food.com 原始食谱</td></tr><tr v-if="!foodcomTriples?.items.length"><td colspan="6" class="kg-table-empty">没有符合条件的食谱组成关系</td></tr></tbody></table></div>
        <div class="kg-pagination"><span>共 {{ count(foodcomTriples?.total) }} 条 · 第 {{ page }} / {{ totalPages }} 页</span><div><button :disabled="page<=1" @click="searchTriples(page-1)">上一页</button><button :disabled="page>=totalPages" @click="searchTriples(page+1)">下一页</button></div></div>
      </section>
      <div v-if="selectedDataset==='foodcom' && !foodcom?.available" class="kg-empty">Food.com 索引尚未导入。</div>
      <div v-if="selectedDataset!=='foodcom' && !summary?.available" class="kg-empty">尚无已上传的知识三元组数据集。</div>
      <template v-if="selectedDataset!=='foodcom' && summary?.available">
      <section class="kg-overview">
        <div class="kg-overview-top"><div class="kg-section-title"><span class="kg-step">03</span><div><h3>图谱概览</h3><p>当前选中：{{ summary.dataset?.name }}。下列指标依据该数据集实时计算。</p></div></div></div>
        <div class="kg-status"><span class="kg-status-dot"></span><div><strong>本地图谱已构建</strong><small>{{ summary.dataset?.name }} · {{ summary.dataset?.filename }} · {{ summary.dataset?.source }}</small></div><span class="kg-status-date">{{ summary.dataset?.imported_at.slice(0, 10) }}</span></div>
        <div class="kg-stats">
          <article><span>实体节点</span><strong>{{ summary.node_count?.toLocaleString() }}</strong><small>名称与类型去重</small></article>
          <article><span>知识关系</span><strong>{{ summary.edge_count?.toLocaleString() }}</strong><small>已导入三元组</small></article>
          <article><span>实体类型</span><strong>{{ summary.entity_type_count }}</strong><small>节点类别</small></article>
          <article><span>关系类型</span><strong>{{ summary.relation_type_count }}</strong><small>关系类别</small></article>
        </div>
      </section>

      <section class="kg-insights">
        <div class="kg-section-title"><span class="kg-step">04</span><div><h3>图谱统计</h3><p>观察关系置信度及类型分布，辅助判断数据质量与结构。</p></div></div>
        <div class="kg-insight-grid">
          <article class="kg-chart-card"><div class="kg-card-head"><div><span>CONFIDENCE DISTRIBUTION</span><h4>关系置信度分布</h4></div><strong>均值 {{ summary.average_confidence?.toFixed(2) }}</strong></div>
            <div class="kg-bars"><div v-for="item in bins" :key="item.label" class="kg-bar-item"><span class="kg-bar-count">{{ item.count }}</span><div class="kg-bar-track"><div :style="{ height: Math.max(4, item.count / maxBin * 100) + '%' }"></div></div><small>{{ item.label }}</small></div></div>
          </article>
          <div class="kg-type-stack">
            <article class="kg-type-card"><div class="kg-card-head"><div><span>NODE TYPES</span><h4>实体类型分布</h4></div><small>{{ summary.entity_type_count }} 类实体</small></div><div class="kg-chips"><span v-for="item in summary.node_types" :key="item.name">{{ item.name }} <b>{{ item.count }}</b></span></div></article>
            <article class="kg-type-card"><div class="kg-card-head"><div><span>RELATION TYPES</span><h4>关系类型分布</h4></div><small>{{ summary.relation_type_count }} 类关系</small></div><div class="kg-chips relation"><span v-for="item in summary.relation_types" :key="item.name">{{ item.name }} <b>{{ item.count }}</b></span></div></article>
          </div>
        </div>
      </section>

      <section class="kg-table-section">
        <div class="kg-table-top"><div class="kg-section-title"><span class="kg-step">05</span><div><h3>三元组明细</h3><p>查看知识关系、置信度、来源和原文证据。</p></div></div><form class="kg-search" @submit.prevent="searchTriples(1)"><input v-model="search" placeholder="检索实体、关系或证据" aria-label="检索三元组"><button type="submit">查询</button></form></div>
        <div class="kg-table-scroll"><table><thead><tr><th>ID</th><th>起始实体</th><th>关系</th><th>目标实体</th><th>置信度</th><th>来源</th><th>原文证据</th></tr></thead><tbody><tr v-for="item in triples?.items" :key="item.id"><td class="kg-muted">{{ item.id }}</td><td><strong>{{ item.head }}</strong><small>{{ item.head_type }}</small></td><td><span class="kg-relation">{{ item.relation }}</span></td><td><strong>{{ item.tail }}</strong><small>{{ item.tail_type }}</small></td><td><span class="kg-confidence">{{ ((item.confidence ?? 0) * 100).toFixed(0) }}%</span></td><td>{{ item.source }}</td><td class="kg-evidence">{{ item.evidence || '未提供' }}</td></tr><tr v-if="!triples?.items.length"><td colspan="7" class="kg-table-empty">没有符合条件的三元组</td></tr></tbody></table></div>
        <div class="kg-pagination"><span>共 {{ triples?.total ?? 0 }} 条 · 第 {{ page }} / {{ totalPages }} 页</span><div><button :disabled="page<=1" @click="searchTriples(page-1)">上一页</button><button :disabled="page>=totalPages" @click="searchTriples(page+1)">下一页</button></div></div>
      </section>
      </template>
    </template>
  </div>
</template>
