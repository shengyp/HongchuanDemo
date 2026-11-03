<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { FoodcomGraphStatistics, KgDataset, KgExplore, KgGraphNode, KgSummary, KgTriple } from '../types'

const emit = defineEmits<{ (event: 'open-upload'): void }>()
const summary = ref<KgSummary | null>(null)
const graph = ref<KgExplore | null>(null)
const datasetId = ref<number | 'foodcom'>('foodcom')
const datasets = ref<KgDataset[]>([])
const foodcomStats = ref<FoodcomGraphStatistics | null>(null)
const query = ref('')
const nodeType = ref('')
const relation = ref('')
const depth = ref(1)
const layout = ref<'force' | 'ring'>('force')
const zoom = ref(1)
const loading = ref(true)
const exploring = ref(false)
const error = ref('')
const selectedEdge = ref<KgTriple | null>(null)
const selectedNode = ref<KgGraphNode | null>(null)
const palette = ['#1689c7', '#1ab9c3', '#ecab47', '#df7768', '#7e78bd', '#67a991', '#b579a3', '#738fa5']
const nodeColors = computed(() => {
  const result: Record<string, string> = {}
  for (const [index, item] of (summary.value?.node_types ?? []).entries()) result[item.name] = palette[index % palette.length]!
  return result
})
function color(type: string): string { return nodeColors.value[type] ?? '#668e86' }
const focusedId = computed(() => graph.value?.focus?.id ?? '')
const positioned = computed(() => {
  const nodes = graph.value?.nodes ?? []
  if (!nodes.length) return [] as (KgGraphNode & { x: number; y: number })[]
  const center = graph.value?.focus
  const others = nodes.filter(node => node.id !== center?.id)
  const firstIds = new Set<string>()
  for (const edge of graph.value?.edges ?? []) {
    if ((edge.head_id ?? edge.head_type + '::' + edge.head) === center?.id) firstIds.add(edge.tail_id ?? edge.tail_type + '::' + edge.tail)
    if ((edge.tail_id ?? edge.tail_type + '::' + edge.tail) === center?.id) firstIds.add(edge.head_id ?? edge.head_type + '::' + edge.head)
  }
  const sorted = [...others].sort((a, b) => Number(firstIds.has(b.id)) - Number(firstIds.has(a.id)) || b.degree - a.degree || a.id.localeCompare(b.id))
  const positions = new Map<string, { x: number; y: number }>()
  if (center) positions.set(center.id, { x: 380, y: 275 })
  const direct = sorted.filter(node => firstIds.has(node.id))
  const indirect = sorted.filter(node => !firstIds.has(node.id))
  for (const [groupIndex, group] of [direct, indirect].entries()) {
    const radius = groupIndex === 0 ? (group.length > 18 ? 170 : 155) : 233
    group.forEach((node, index) => {
      const angle = -Math.PI / 2 + 2 * Math.PI * index / Math.max(1, group.length) + groupIndex * .13
      positions.set(node.id, { x: 380 + radius * Math.cos(angle), y: 275 + radius * Math.sin(angle) })
    })
  }
  if (layout.value === 'force' && sorted.length > 1) {
    const all = [center, ...sorted].filter(Boolean) as KgGraphNode[]
    const links = (graph.value?.edges ?? []).map(edge => [edge.head_id ?? edge.head_type + '::' + edge.head, edge.tail_id ?? edge.tail_type + '::' + edge.tail])
    for (let step = 0; step < 75; step++) {
      const movement = new Map<string, { x: number; y: number }>()
      for (const node of sorted) movement.set(node.id, { x: 0, y: 0 })
      for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++) {
        const a = positions.get(all[i]!.id)!, b = positions.get(all[j]!.id)!
        const dx = b.x - a.x, dy = b.y - a.y, distance = Math.max(18, Math.hypot(dx, dy))
        const force = Math.min(6, 1600 / (distance * distance))
        if (i > 0) { const m = movement.get(all[i]!.id)!; m.x -= dx / distance * force; m.y -= dy / distance * force }
        if (j > 0) { const m = movement.get(all[j]!.id)!; m.x += dx / distance * force; m.y += dy / distance * force }
      }
      for (const [from, to] of links) {
        const a = positions.get(from), b = positions.get(to)
        if (!a || !b) continue
        const dx = b.x - a.x, dy = b.y - a.y, distance = Math.max(1, Math.hypot(dx, dy))
        const force = (distance - 125) * .0018
        const ma = movement.get(from), mb = movement.get(to)
        if (ma) { ma.x += dx * force; ma.y += dy * force }
        if (mb) { mb.x -= dx * force; mb.y -= dy * force }
      }
      for (const node of sorted) {
        const p = positions.get(node.id)!, m = movement.get(node.id)!
        p.x = Math.max(44, Math.min(716, p.x + m.x + (380 - p.x) * .0007))
        p.y = Math.max(48, Math.min(502, p.y + m.y + (275 - p.y) * .0007))
      }
    }
  }
  return nodes.map(node => ({ ...node, ...positions.get(node.id)! }))
})
const links = computed(() => {
  const map = new Map(positioned.value.map(node => [node.id, node]))
  return (graph.value?.edges ?? []).map(edge => ({
    ...edge,
    from: map.get(edge.head_id ?? edge.head_type + '::' + edge.head),
    to: map.get(edge.tail_id ?? edge.tail_type + '::' + edge.tail),
  })).filter(edge => edge.from && edge.to)
})
const viewBox = computed(() => {
  const width = 760 / zoom.value, height = 550 / zoom.value
  return [380 - width / 2, 275 - height / 2, width, height].join(' ')
})
const related = computed(() => selectedNode.value
  ? (graph.value?.edges ?? []).filter(edge =>
      (edge.head_id ?? edge.head_type + '::' + edge.head) === selectedNode.value!.id ||
      (edge.tail_id ?? edge.tail_type + '::' + edge.tail) === selectedNode.value!.id).slice(0, 12)
  : [])

function foodcomSummary(): KgSummary {
  const stats = foodcomStats.value!
  return {
    available: true, datasets: datasets.value,
    dataset: { id: 0, name: 'Food.com 食谱数据', filename: 'Food.com 原始食谱索引', source: 'Food.com', imported_at: '', triple_count: stats.edge_count },
    node_count: stats.node_count, edge_count: stats.edge_count,
    entity_type_count: stats.entity_type_count, relation_type_count: stats.relation_type_count,
    node_types: stats.node_types, relation_types: stats.relation_types,
  }
}
async function loadSummary(): Promise<void> {
  const [kg, food] = await Promise.all([api.kgSummary(), api.foodcomGraphStatistics()])
  datasets.value = kg.datasets
  foodcomStats.value = food.available ? food : null
  if (foodcomStats.value) {
    datasetId.value = 'foodcom'
    summary.value = foodcomSummary()
    await explore()
  } else {
    datasetId.value = kg.dataset?.id ?? 0
    summary.value = kg
    if (datasetId.value) await explore()
  }
}
onMounted(async () => {
  try { await loadSummary() }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '图谱加载失败' }
  finally { loading.value = false }
})
async function explore(): Promise<void> {
  if (!datasetId.value) return
  exploring.value = true
  error.value = ''
  try {
    graph.value = datasetId.value === 'foodcom'
      ? await api.foodcomGraphExplore(query.value.trim(), nodeType.value, depth.value)
      : await api.kgExplore(datasetId.value, query.value.trim(), nodeType.value, relation.value, depth.value)
    selectedNode.value = graph.value.focus
    selectedEdge.value = graph.value.edges[0] ?? null
    zoom.value = 1
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '图谱探索失败' }
  finally { exploring.value = false }
}
async function changeDataset(event: Event): Promise<void> {
  const value = (event.target as HTMLSelectElement).value
  datasetId.value = value === 'foodcom' ? 'foodcom' : Number(value)
  summary.value = datasetId.value === 'foodcom' ? foodcomSummary() : await api.kgSummary(datasetId.value)
  query.value = ''; nodeType.value = ''; relation.value = ''; depth.value = 1
  await explore()
}
async function selectNode(node: KgGraphNode & { x: number; y: number }): Promise<void> {
  query.value = node.label
  nodeType.value = node.type
  await explore()
}
function selectEdge(edge: KgTriple): void {
  selectedEdge.value = edge
  selectedNode.value = null
}
function resetGraph(): void {
  query.value = ''; nodeType.value = ''; relation.value = ''; depth.value = 1
  layout.value = 'force'; zoom.value = 1
  void explore()
}
function zoomBy(multiplier: number): void { zoom.value = Math.max(.7, Math.min(2.2, zoom.value * multiplier)) }
</script>

<template>
  <div class="kgx-page">
    <header class="kgx-heading">
      <div><p class="kgx-eyebrow">GRAPH EXPLORER</p><h2>知识图谱可视化</h2><p>检索实体、筛选类型，选择 Food.com 或已上传图谱，探索真实关系及其来源。</p></div>
      <div v-if="summary?.available" class="kgx-layout-actions"><button :class="{active:layout==='force'}" @click="layout='force'">力导向</button><button :class="{active:layout==='ring'}" @click="layout='ring'">环形</button><button @click="resetGraph">↺ 重置</button></div>
    </header>
    <div v-if="error" class="kgx-error" role="alert">{{ error }}</div>
    <div v-if="loading" class="kgx-empty">正在加载图谱…</div>
    <div v-else-if="!summary?.available" class="kgx-empty"><span>◇</span><h3>还没有可视化的数据集</h3><p>请先在数据管理模块上传知识三元组，图谱会自动出现在这里。</p><button @click="emit('open-upload')">前往上传数据集 →</button></div>
    <template v-else>
      <form class="kgx-toolbar" @submit.prevent="explore">
        <label class="kgx-dataset">数据集<select :value="datasetId" @change="changeDataset"><option v-if="foodcomStats?.available" value="foodcom">Food.com 食谱数据 · 默认</option><option v-for="item in datasets" :key="item.id" :value="item.id">{{ item.name }} · #{{ item.id }}（{{ item.triple_count }} 条）</option></select></label>
        <label class="kgx-query">实体检索<input v-model="query" placeholder="输入实体名称，如菠菜"></label>
        <label>实体类型<select v-model="nodeType"><option value="">全部类型</option><option v-for="item in summary.node_types" :key="item.name" :value="item.name">{{ item.name }}</option></select></label>
        <label>关系类型<select v-model="relation"><option value="">全部关系</option><option v-for="item in summary.relation_types" :key="item.name" :value="item.name">{{ item.name }}</option></select></label>
        <label>探索层级<select v-model.number="depth"><option :value="1">1 层邻居</option><option :value="2">2 层邻居</option></select></label>
        <button type="submit" :disabled="exploring">{{ exploring ? '探索中…' : '探索图谱 →' }}</button>
      </form>
      <div class="kgx-meta"><span><i></i> {{ graph?.nodes.length ?? 0 }} 个节点　—　{{ graph?.edges.length ?? 0 }} 条关系</span><span>当前数据集：{{ summary.dataset?.name }} · 共 {{ summary.edge_count }} 条{{ datasetId==='foodcom' ? '食谱组成关系' : '三元组' }}</span></div>
      <div class="kgx-workspace">
        <section class="kgx-canvas">
          <div class="kgx-canvas-head"><div><strong>{{ graph?.focus ? graph.focus.label + ' · 局部关系图' : '未找到匹配实体' }}</strong><small>点击节点切换中心实体，点击连线查看证据</small></div><div class="kgx-zoom"><button aria-label="缩小图谱" @click="zoomBy(1/1.2)">−</button><span>{{ Math.round(zoom*100) }}%</span><button aria-label="放大图谱" @click="zoomBy(1.2)">＋</button></div></div>
          <div v-if="!graph?.focus" class="kgx-no-match">没有找到符合条件的实体。请修改检索词或筛选条件。</div>
          <svg v-else class="kgx-svg" :viewBox="viewBox" role="img" :aria-label="graph.focus.label + ' 的知识图谱'">
            <defs><filter id="kgx-shadow"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#1d4d42" flood-opacity=".13"/></filter></defs>
            <g v-for="edge in links" :key="'edge-'+edge.id" class="kgx-edge" :class="{active:selectedEdge?.id===edge.id}" @click="selectEdge(edge)">
              <line :x1="edge.from!.x" :y1="edge.from!.y" :x2="edge.to!.x" :y2="edge.to!.y" stroke-width="12" stroke="transparent" />
              <line :x1="edge.from!.x" :y1="edge.from!.y" :x2="edge.to!.x" :y2="edge.to!.y" :stroke="selectedEdge?.id===edge.id ? '#13a68b' : '#b8cbc5'" :stroke-width="selectedEdge?.id===edge.id ? 2.8 : 1.5" :stroke-opacity="datasetId==='foodcom' ? .65 : Math.max(.32,edge.confidence ?? 0)" />
            </g>
            <g v-for="node in positioned" :key="node.id" class="kgx-node" :class="{focused:node.id===focusedId}" @click="selectNode(node)">
              <circle :cx="node.x" :cy="node.y" :r="node.id===focusedId ? 29 : 18" :fill="color(node.type)" stroke="white" stroke-width="3" filter="url(#kgx-shadow)" />
              <text :x="node.x" :y="node.y+4" text-anchor="middle" fill="white" :font-size="node.id===focusedId ? 12 : 10" font-weight="700">{{ node.label.length > 5 ? node.label.slice(0,5) + '…' : node.label }}</text>
              <text v-if="node.id!==focusedId" class="kgx-node-label" :x="node.x" :y="node.y+34" text-anchor="middle">{{ node.label.length>10 ? node.label.slice(0,10)+'…' : node.label }}</text>
            </g>
          </svg>
          <div class="kgx-legend"><span v-for="item in summary.node_types" :key="item.name"><i :style="{background:color(item.name)}"></i>{{ item.name }}</span><small>{{ datasetId==='foodcom' ? '连线均来自真实食谱组成；未提供置信度' : '连线深浅反映置信度；仅展示局部关系' }}</small></div>
        </section>
        <aside class="kgx-detail">
          <template v-if="selectedEdge">
            <div class="kgx-detail-kicker">知识关系 · #{{ selectedEdge.id }}</div>
            <h3>{{ selectedEdge.relation }}</h3>
            <p class="kgx-detail-intro">当前选中的三元组关系及其上传时保留的来源与原文证据。</p>
            <div class="kgx-triple"><strong>{{ selectedEdge.head }}</strong><span>{{ selectedEdge.relation }} →</span><strong>{{ selectedEdge.tail }}</strong></div>
            <dl class="kgx-facts"><div><dt>起始实体类型</dt><dd>{{ selectedEdge.head_type }}</dd></div><div><dt>目标实体类型</dt><dd>{{ selectedEdge.tail_type }}</dd></div><div><dt>置信度</dt><dd><b>{{ selectedEdge.confidence==null ? '未提供' : (selectedEdge.confidence*100).toFixed(0)+'%' }}</b></dd></div><div><dt>数据来源</dt><dd>{{ selectedEdge.source }}</dd></div></dl>
            <div class="kgx-evidence"><span>原文证据</span><p>{{ selectedEdge.evidence || '该条关系未提供原文证据。' }}</p></div>
          </template>
          <template v-else-if="selectedNode">
            <div class="kgx-detail-kicker">实体节点</div><h3>{{ selectedNode.label }}</h3><p class="kgx-detail-intro">类型：{{ selectedNode.type }} · 当前局部图谱关联 {{ related.length }} 条关系</p>
            <div class="kgx-related"><h4>关联关系</h4><button v-for="edge in related" :key="edge.id" @click="selectEdge(edge)"><span>{{ edge.head }} <b>{{ edge.relation }}</b> {{ edge.tail }}</span><em>{{ edge.confidence==null ? '真实关联' : (edge.confidence*100).toFixed(0)+'%' }}</em></button><p v-if="!related.length">暂无符合筛选条件的关系。</p></div>
          </template>
          <template v-else><div class="kgx-detail-kicker">图谱详情</div><h3>选择节点或关系</h3><p class="kgx-detail-intro">在左侧图谱中点击节点或连线，查看相应信息。</p></template>
        </aside>
      </div>
      <p class="kgx-footnote">{{ datasetId==='foodcom' ? 'Food.com 关系均来自真实食谱组成，未提供置信度。' : '图中的置信度来自上传数据；原文证据为空时按“未提供”显示。' }}局部视图最多展示 100 条关系。</p>
    </template>
  </div>
</template>

