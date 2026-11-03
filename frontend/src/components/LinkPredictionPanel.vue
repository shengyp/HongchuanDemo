<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import FoodcomDiscoveryPanel from './FoodcomDiscoveryPanel.vue'
import type { FoodcomSummary, KgSummary, PredictionCandidate, PredictionEntity, PredictionTask, PredictionTaskSummary } from '../types'

const emit = defineEmits<{ (event: 'open-upload' | 'open-graph'): void }>()
const summary = ref<KgSummary | null>(null)
const foodcom = ref<FoodcomSummary | null>(null)
const sourceDataset = ref<number | 'foodcom'>('foodcom')
const tasks = ref<PredictionTaskSummary[]>([])
const activeTask = ref<PredictionTask | null>(null)
const activeCandidate = ref<PredictionCandidate | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const dialog = ref(false)
const formError = ref('')
const formDataset = ref(0)
const formSummary = ref<KgSummary | null>(null)
const formName = ref('')
const formRelation = ref('')
const formLimit = ref(10)
type LinkModel = 'gtranse' | 'ukge' | 'beurre' | 'focuse' | 'passleaf' | 'ukgse' | 'upgat' | 'gmuc' | 'gmuc-plus'
const formModel = ref<LinkModel>('ukge')
const modelOptions: { id: LinkModel; label: string; group: '常规模型' | '少样本模型' }[] = [
  { id: 'gtranse', label: 'GTransE', group: '常规模型' },
  { id: 'ukge', label: 'UKGE', group: '常规模型' },
  { id: 'beurre', label: 'BEUrRE', group: '常规模型' },
  { id: 'focuse', label: 'FocusE', group: '常规模型' },
  { id: 'passleaf', label: 'PASSLEAF', group: '常规模型' },
  { id: 'ukgse', label: 'UKGsE', group: '常规模型' },
  { id: 'upgat', label: 'UPGAT', group: '常规模型' },
  { id: 'gmuc', label: 'GMUC', group: '少样本模型' },
  { id: 'gmuc-plus', label: 'GMUC+', group: '少样本模型' },
]
function readModelChoices(): Record<number, LinkModel> {
  try {
    const raw = JSON.parse(localStorage.getItem('nutrigraph-link-models') || '{}') as Record<string, string>
    const valid = new Set(modelOptions.map(item => item.id))
    return Object.fromEntries(Object.entries(raw).filter(([, model]) => valid.has(model as LinkModel))) as Record<number, LinkModel>
  } catch { return {} }
}
const taskModels = ref<Record<number, LinkModel>>(readModelChoices())
function modelForTask(id: number): LinkModel | null { return taskModels.value[id] ?? null }
function modelLabel(model: LinkModel): string { return modelOptions.find(item => item.id === model)?.label ?? model }
const entitySearch = ref('')
const entities = ref<PredictionEntity[]>([])
const chosenEntity = ref<PredictionEntity | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | undefined
const visibleTasks = computed(() => tasks.value.filter(item => item.dataset_id === sourceDataset.value))
const totalCandidates = computed(() => visibleTasks.value.reduce((sum, item) => sum + item.candidate_count, 0))
const selectedDataset = computed(() => summary.value?.datasets.find(item => item.id === formDataset.value))

onMounted(async () => {
  try {
    const [newSummary, newTasks, food] = await Promise.all([api.kgSummary(), api.predictionTasks(), api.foodcomSummary()])
    summary.value = newSummary
    tasks.value = newTasks
    foodcom.value = food
    if (!food.available && newSummary.dataset) sourceDataset.value = newSummary.dataset.id
    if (sourceDataset.value !== 'foodcom') await selectTaskForDataset(sourceDataset.value)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '任务加载失败' }
  finally { loading.value = false }
})
async function selectTaskForDataset(id: number): Promise<void> {
  const first = tasks.value.find(item => item.dataset_id === id)
  if (first) await loadTask(first.id)
  else { activeTask.value = null; activeCandidate.value = null }
}
async function changeSource(event: Event): Promise<void> {
  const value = (event.target as HTMLSelectElement).value
  sourceDataset.value = value === 'foodcom' ? 'foodcom' : Number(value)
  error.value = ''
  if (sourceDataset.value === 'foodcom') { activeTask.value = null; activeCandidate.value = null }
  else await selectTaskForDataset(sourceDataset.value)
}
async function loadTask(id: number): Promise<void> {
  error.value = ''
  try {
    activeTask.value = await api.predictionTask(id)
    activeCandidate.value = activeTask.value.candidates[0] ?? null
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '任务结果加载失败' }
}
async function openDialog(): Promise<void> {
  dialog.value = true
  formError.value = ''
  formDataset.value = sourceDataset.value === 'foodcom' ? (summary.value?.dataset?.id ?? 0) : sourceDataset.value
  formSummary.value = summary.value
  formRelation.value = summary.value?.relation_types?.find(item => item.name.includes('搭配'))?.name
    ?? summary.value?.relation_types?.[0]?.name ?? ''
  formName.value = ''
  formLimit.value = 10
  formModel.value = 'ukge'
  entitySearch.value = ''
  chosenEntity.value = null
  await refreshEntities()
}
async function changeDataset(event: Event): Promise<void> {
  formDataset.value = Number((event.target as HTMLSelectElement).value)
  formSummary.value = await api.kgSummary(formDataset.value)
  formRelation.value = formSummary.value.relation_types?.[0]?.name ?? ''
  chosenEntity.value = null
  await refreshEntities()
}
async function refreshEntities(): Promise<void> {
  if (!formDataset.value || !formRelation.value) { entities.value = []; return }
  try { entities.value = await api.predictionEntities(formDataset.value, entitySearch.value, formRelation.value) }
  catch (cause) { formError.value = cause instanceof Error ? cause.message : '实体加载失败' }
}
watch(entitySearch, () => {
  if (!dialog.value) return
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { void refreshEntities() }, 220)
})
watch(formRelation, () => {
  if (!dialog.value) return
  chosenEntity.value = null
  void refreshEntities()
})
async function createTask(): Promise<void> {
  formError.value = ''
  if (!formName.value.trim()) { formError.value = '请输入任务名称'; return }
  if (!chosenEntity.value) { formError.value = '请选择目标实体'; return }
  if (!formRelation.value) { formError.value = '请选择预测关系'; return }
  busy.value = true
  try {
    const result = await api.createPredictionTask(
      formName.value.trim(), formDataset.value, chosenEntity.value.name, chosenEntity.value.type,
      formRelation.value, formLimit.value,
    )
    tasks.value = await api.predictionTasks()
    taskModels.value = { ...taskModels.value, [result.id]: formModel.value }
    localStorage.setItem('nutrigraph-link-models', JSON.stringify(taskModels.value))
    sourceDataset.value = result.dataset.id
    activeTask.value = result
    activeCandidate.value = result.candidates[0] ?? null
    dialog.value = false
  } catch (cause) { formError.value = cause instanceof Error ? cause.message : '创建任务失败' }
  finally { busy.value = false }
}
function score(value: number): string { return value.toFixed(3) }
function date(value: string): string { return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
</script>

<template>
  <div class="lp-page">
    <div class="lp-heading"><div><p class="lp-kicker">INGREDIENT RELATION DISCOVERY</p><h2>{{ sourceDataset==='foodcom' ? '食材搭配发现' : '关联发现任务' }}</h2><p>{{ sourceDataset==='foodcom' ? '选择食材，查看已有搭配，再探索可能的新搭配。' : '选择目标和关系，查看有依据的关联建议。' }}</p></div><button v-if="sourceDataset!=='foodcom' && summary?.available" class="lp-primary" @click="openDialog"><span>＋</span> 创建发现任务</button></div>
    <div class="dataset-context"><label>当前数据集<select :value="sourceDataset" @change="changeSource"><option v-if="foodcom?.available" value="foodcom">Food.com 食谱数据 · 默认</option><option v-for="item in summary?.datasets ?? []" :key="item.id" :value="item.id">{{ item.name }} · #{{ item.id }}</option></select></label><p>{{ sourceDataset==='foodcom' ? '查看真实搭配，创建发现任务，并核查新的搭配建议。' : '在所选上传图谱中创建并查看关联发现任务。' }}</p></div>
    <p v-if="error" class="lp-error" role="alert">{{ error }}</p>
    <div v-if="loading" class="lp-empty">正在读取任务与图谱信息…</div>
    <FoodcomDiscoveryPanel v-else-if="sourceDataset==='foodcom'" @open-graph="emit('open-graph')" />
    <div v-else-if="!summary?.available" class="lp-empty"><span>◇</span><h3>先上传知识数据集</h3><p>关联发现需要已观察的三元组作为依据。上传完成后即可创建任务。</p><button @click="emit('open-upload')">前往数据管理 →</button></div>
    <template v-else>
      <div class="lp-steps"><div><b>01</b><span>选择数据集与目标实体</span></div><i>→</i><div><b>02</b><span>寻找共享邻居的相似实体</span></div><i>→</i><div><b>03</b><span>核查候选关系与原始证据</span></div></div>
      <div class="lp-stats"><article><span>可用数据集</span><strong>{{ summary.datasets.length + (foodcom?.available ? 1 : 0) }}</strong><small>含默认 Food.com</small></article><article><span>已创建任务</span><strong>{{ visibleTasks.length }}</strong><small>当前数据集的任务</small></article><article><span>待核查候选</span><strong>{{ totalCandidates }}</strong><small>未写入真实图谱</small></article></div>
      <div class="lp-workspace">
        <section class="lp-task-list"><div class="lp-section-head"><div><span>TASK HISTORY</span><h3>发现任务</h3></div><button @click="openDialog">新建任务 ＋</button></div><div v-if="visibleTasks.length" class="lp-task-scroll"><button v-for="item in visibleTasks" :key="item.id" class="lp-task-item" :class="{active:activeTask?.id===item.id}" @click="loadTask(item.id)"><div><strong>{{ item.name }}</strong><small>#{{ item.id }} · {{ date(item.created_at) }}</small></div><p>{{ item.dataset_name }} · {{ item.target_name }} <em>{{ item.relation }}</em> ?</p><span>{{ item.candidate_count }} 个候选 →</span></button></div><div v-else class="lp-list-empty">尚无发现任务。点击“创建发现任务”开始。</div></section>
        <section class="lp-result">
          <div v-if="!activeTask" class="lp-result-empty"><span>◈</span><h3>等待任务结果</h3><p>从左侧选择任务，或创建一项新的发现任务。</p></div>
          <template v-else>
            <div class="lp-result-head"><div><span>RESULT · TASK #{{ activeTask.id }}</span><h3>{{ activeTask.name }}</h3><p>{{ activeTask.dataset.name }} · {{ date(activeTask.created_at) }}</p></div><button @click="emit('open-graph')">查看原始图谱 ↗</button></div>
            <div class="lp-query-line"><span>目标实体</span><strong>{{ activeTask.target_name }}</strong><i>— {{ activeTask.relation }} →</i><b>待预测实体</b></div>
            <div class="lp-result-metrics"><div><span>已观察的该类关系</span><strong>{{ activeTask.existing_count }}</strong></div><div><span>待核查候选</span><strong>{{ activeTask.candidates.length }}</strong></div><div><span>排序方法</span><strong class="lp-method">共享邻居 + 关系置信度</strong></div></div>
            <div class="lp-notice"><strong>链接预测模型</strong><span>{{ modelForTask(activeTask.id) ? modelLabel(modelForTask(activeTask.id)!) + ' · 演示选择，未参与本次计算' : '既有任务未指定模型' }}</span></div>
            <div class="lp-notice"><strong>结果边界</strong><span>分数用于候选排序，不是校准概率；候选关系尚未核实，不会改变原图谱或食材营养值。</span></div>
            <div class="lp-candidate-section"><div class="lp-section-head"><div><span>CANDIDATE LINKS</span><h3>候选关系</h3></div><small>{{ activeTask.candidates.length }} 条</small></div>
              <p v-if="!activeTask.candidates.length" class="lp-no-candidate">{{ activeTask.note }}</p>
              <div v-else class="lp-candidate-grid"><div class="lp-candidate-list"><button v-for="item in activeTask.candidates" :key="item.rank" :class="{active:activeCandidate?.rank===item.rank}" @click="activeCandidate=item"><span class="lp-rank">{{ String(item.rank).padStart(2,'0') }}</span><div><strong>{{ activeTask.target_name }} → {{ item.tail }}</strong><small>{{ item.tail_type }} · {{ item.support_count }} 个相似实体支持</small></div><span class="lp-score">{{ score(item.score) }}</span></button></div>
                <aside v-if="activeCandidate" class="lp-evidence"><span class="lp-evidence-kicker">候选关系 · 待核查</span><h4>{{ activeTask.target_name }} <em>{{ activeTask.relation }}</em> {{ activeCandidate.tail }}</h4><p>排序分数 <strong>{{ score(activeCandidate.score) }}</strong> · {{ activeCandidate.support_count }} 个相似实体支持</p><div v-for="reference in activeCandidate.references" :key="reference.reference_id" class="lp-reference"><div><strong>参考实体：{{ reference.similar_entity }}</strong><small>真实关系 #{{ reference.reference_id }} · 置信度 {{ (reference.observed_confidence*100).toFixed(0) }}%</small></div><p>共同邻居：<span v-for="neighbor in reference.shared_neighbors" :key="neighbor.relation+neighbor.entity">{{ neighbor.relation }} {{ neighbor.entity }}　</span></p><blockquote>{{ reference.evidence || '该真实关系未提供原文证据。' }}</blockquote><small>来源：{{ reference.source }}</small></div></aside>
              </div>
            </div>
          </template>
        </section>
      </div>
    </template>

    <div v-if="dialog" class="lp-modal-backdrop" @click.self="dialog=false">
      <section class="lp-modal" role="dialog" aria-modal="true" aria-labelledby="lp-modal-title">
        <div class="lp-modal-head"><div><span>CREATE DISCOVERY TASK</span><h2 id="lp-modal-title">创建发现任务</h2><p>配置目标实体和待预测关系</p></div><button aria-label="关闭" @click="dialog=false">×</button></div>
        <div class="lp-modal-body">
          <label>任务名称 <b>*</b><input v-model="formName" maxlength="100" placeholder="例如：菠菜搭配关系探索"></label>
          <div class="lp-form-row"><label>数据集 <b>*</b><select :value="formDataset" @change="changeDataset"><option v-for="item in summary?.datasets" :key="item.id" :value="item.id">{{ item.name }} · #{{ item.id }}</option></select></label><label>待预测关系 <b>*</b><select v-model="formRelation"><option v-for="item in formSummary?.relation_types" :key="item.name" :value="item.name">{{ item.name }}</option></select></label></div>
          <label>链接预测模型 <b>*</b><select v-model="formModel"><optgroup label="常规模型"><option v-for="item in modelOptions.filter(model => model.group === '常规模型')" :key="item.id" :value="item.id">{{ item.label }}</option></optgroup><optgroup label="少样本模型"><option v-for="item in modelOptions.filter(model => model.group === '少样本模型')" :key="item.id" :value="item.id">{{ item.label }}</option></optgroup></select></label>
          <p class="lp-modal-tip">以上为 unKR 论文收录的模型，仅供前端演示选择。当前候选仍由“共享邻居 + 关系置信度”排序，所选模型未参与计算。</p>
          <label>目标实体 <b>*</b><input v-model="entitySearch" placeholder="输入实体名称筛选"></label>
          <div class="lp-entity-list"><button v-for="item in entities" :key="item.type+'::'+item.name" :class="{active:chosenEntity?.name===item.name && chosenEntity?.type===item.type}" @click="chosenEntity=item"><span><strong>{{ item.name }}</strong><small>{{ item.type }} · {{ item.degree }} 条该类真实关系</small></span><em>{{ chosenEntity?.name===item.name && chosenEntity?.type===item.type ? '已选择' : '选择' }}</em></button><p v-if="!entities.length">没有找到具备该类关系的实体，请更换关键词或关系类型。</p></div>
          <label>最多返回候选<select v-model.number="formLimit"><option :value="5">5 条</option><option :value="10">10 条</option><option :value="20">20 条</option><option :value="30">30 条</option></select></label>
          <p class="lp-modal-tip">数据来源：{{ selectedDataset?.source }}。候选仅依据同类型实体的共享邻居与已观察关系排序。</p>
          <p v-if="formError" class="lp-error" role="alert">{{ formError }}</p>
        </div>
        <div class="lp-modal-actions"><button @click="dialog=false">取消</button><button class="lp-primary" :disabled="busy" @click="createTask">{{ busy ? '正在计算…' : '创建任务并查看结果' }}</button></div>
      </section>
    </div>
  </div>
</template>

