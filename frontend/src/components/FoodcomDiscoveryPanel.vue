<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import type { FoodcomDetail, FoodcomIngredient } from '../types'

const emit = defineEmits<{ (event: 'open-graph'): void }>()

type Reference = { via: string; targetCount: number; candidateCount: number }
type Candidate = { id: number; name: string; supportCount: number; evidenceWeight: number; references: Reference[] }
type FoodTask = {
  id: string; name: string; targetId: number; targetName: string; targetFrequency: number
  tail: boolean; createdAt: string; model: string; scanned: number
  observed: FoodcomDetail['neighbors']; recipes: FoodcomDetail['recipes']; candidates: Candidate[]
}
const modelOptions = ['GTransE', 'UKGE', 'BEUrRE', 'FocusE', 'PASSLEAF', 'UKGsE', 'UPGAT', 'GMUC', 'GMUC+']
const storageKey = 'nutrigraph-foodcom-discovery-v1'
function readTasks(): FoodTask[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(storageKey) || '[]')
    return Array.isArray(value) ? value.filter((item): item is FoodTask =>
      typeof item === 'object' && item !== null && typeof item.id === 'string' &&
      Array.isArray(item.candidates) && Array.isArray(item.observed)).slice(0, 20) : []
  } catch { return [] }
}
const query = ref('')
const hits = ref<FoodcomIngredient[]>([])
const detail = ref<FoodcomDetail | null>(null)
const busy = ref(false)
const error = ref('')
const dialog = ref(false)
const formName = ref('')
const formModel = ref('UKGE')
const formLimit = ref(10)
const formError = ref('')
const tasks = ref<FoodTask[]>(readTasks())
const activeId = ref(tasks.value[0]?.id ?? '')
const candidateId = ref<number | null>(null)
const activeTask = computed(() => tasks.value.find(item => item.id === activeId.value) ?? null)
const activeCandidate = computed(() => activeTask.value?.candidates.find(item => item.id === candidateId.value) ?? activeTask.value?.candidates[0] ?? null)
function fmt(value: number): string { return value.toLocaleString('zh-CN') }
function date(value: string): string { return new Date(value).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }) }

async function search(): Promise<void> {
  if (!query.value.trim()) return
  busy.value = true
  error.value = ''
  detail.value = null
  try { hits.value = (await api.foodcomSearch(query.value.trim())).ingredients }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '食材搜索失败' }
  finally { busy.value = false }
}
async function selectIngredient(id: number): Promise<void> {
  busy.value = true
  error.value = ''
  try { detail.value = await api.foodcomIngredient(id) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '食材信息加载失败' }
  finally { busy.value = false }
}
function openDialog(): void {
  if (!detail.value) return
  formName.value = detail.value.name + ' 搭配发现'
  formModel.value = 'UKGE'
  formLimit.value = 10
  formError.value = ''
  dialog.value = true
}
async function createTask(): Promise<void> {
  const target = detail.value
  if (!target) return
  if (!formName.value.trim()) { formError.value = '请给任务起个名字'; return }
  busy.value = true
  formError.value = ''
  try {
    const observedIds = new Set(target.neighbors.map(item => item.id))
    const references = target.neighbors.slice(0, 8)
    const results = await Promise.allSettled(references.map(item => api.foodcomIngredient(item.id)))
    const candidates = new Map<number, Candidate>()
    let scanned = 0
    results.forEach((result, index) => {
      if (result.status !== 'fulfilled') return
      scanned++
      const via = references[index]!
      for (const item of result.value.neighbors) {
        if (item.id === target.id || observedIds.has(item.id)) continue
        let candidate = candidates.get(item.id)
        if (!candidate) {
          candidate = { id: item.id, name: item.name, supportCount: 0, evidenceWeight: 0, references: [] }
          candidates.set(item.id, candidate)
        }
        candidate.supportCount++
        candidate.evidenceWeight += Math.min(via.cooccur, item.cooccur)
        candidate.references.push({ via: via.name, targetCount: via.cooccur, candidateCount: item.cooccur })
      }
    })
    if (scanned === 0 && references.length) throw new Error('参考食材暂时无法读取，请重试')
    const ranked = [...candidates.values()].sort((a, b) =>
      b.supportCount - a.supportCount || b.evidenceWeight - a.evidenceWeight || a.name.localeCompare(b.name)).slice(0, formLimit.value)
    const task: FoodTask = {
      id: String(Date.now()) + '-' + Math.random().toString(36).slice(2, 7),
      name: formName.value.trim(), targetId: target.id, targetName: target.name,
      targetFrequency: target.frequency, tail: target.tail, createdAt: new Date().toISOString(),
      model: formModel.value, scanned, observed: target.neighbors, recipes: target.recipes, candidates: ranked,
    }
    tasks.value = [task, ...tasks.value].slice(0, 20)
    localStorage.setItem(storageKey, JSON.stringify(tasks.value))
    activeId.value = task.id
    candidateId.value = ranked[0]?.id ?? null
    dialog.value = false
  } catch (cause) { formError.value = cause instanceof Error ? cause.message : '任务创建失败' }
  finally { busy.value = false }
}
function selectTask(id: string): void { activeId.value = id; candidateId.value = null }
</script>

<template>
  <div class="fc-discovery">
    <div class="lp-steps"><div><b>01</b><span>选择食材</span></div><i>→</i><div><b>02</b><span>查看已有搭配</span></div><i>→</i><div><b>03</b><span>发现新建议</span></div></div>
    <section class="lp-foodcom-card">
      <div class="fc-head"><div><h3>选择一个食材</h3><p>搜索 Food.com 食材，先查看真实食谱，再创建搭配发现任务。</p></div><button v-if="detail" class="lp-primary" :disabled="busy" @click="openDialog">＋ 创建发现任务</button></div>
      <form class="lp-foodcom-search" @submit.prevent="search"><input v-model="query" maxlength="100" placeholder="输入英文食材，如 tofu、spinach" aria-label="检索 Food.com 食材"><button :disabled="busy || !query.trim()">{{ busy ? '检索中…' : '搜索' }}</button></form>
      <div v-if="hits.length" class="lp-foodcom-hits"><button v-for="item in hits" :key="item.id" :class="{active:detail?.id===item.id}" @click="selectIngredient(item.id)">{{ item.name }} <small>{{ fmt(item.frequency) }} 道食谱</small></button></div>
      <p v-if="error" class="lp-error" role="alert">{{ error }}</p>
      <div v-if="detail" class="fc-observed"><h4>{{ detail.name }} · 已有真实搭配 <small>{{ detail.tail ? '少见食材' : '常见食材' }}，见于 {{ fmt(detail.frequency) }} 道食谱</small></h4><div class="fc-observed-list"><span v-for="item in detail.neighbors" :key="item.id">{{ item.name }} <small>共现 {{ item.cooccur }} 次</small></span></div><p>原食谱示例：{{ detail.recipes.slice(0, 3).map(item => item.name + ' (#' + item.id + ')').join('、') || '暂无' }}</p></div>
    </section>
    <div class="lp-stats"><article><span>Food.com 任务</span><strong>{{ tasks.length }}</strong><small>保存在当前浏览器</small></article><article><span>当前候选建议</span><strong>{{ activeTask?.candidates.length ?? 0 }}</strong><small>需要人工核查</small></article><article><span>参考真实搭配</span><strong>{{ activeTask?.scanned ?? 0 }}</strong><small>本次参与计算的食材</small></article></div>
    <div class="lp-workspace">
      <section class="lp-task-list"><div class="lp-section-head"><div><span>HISTORY</span><h3>发现任务</h3></div></div><div v-if="tasks.length" class="lp-task-scroll"><button v-for="item in tasks" :key="item.id" class="lp-task-item" :class="{active:activeId===item.id}" @click="selectTask(item.id)"><div><strong>{{ item.name }}</strong><small>{{ date(item.createdAt) }}</small></div><p>{{ item.targetName }} · {{ item.tail ? '少见食材' : '常见食材' }}</p><span>{{ item.candidates.length }} 条搭配建议 →</span></button></div><div v-else class="lp-list-empty">还没有任务。先搜索并选择一种食材。</div></section>
      <section class="lp-result">
        <div v-if="!activeTask" class="lp-result-empty"><span>◈</span><h3>从一种食材开始</h3><p>创建任务后，这里会显示搭配建议和参考依据。</p></div>
        <template v-else>
          <div class="lp-result-head"><div><span>FOOD.COM · DISCOVERY</span><h3>{{ activeTask.name }}</h3><p>{{ activeTask.targetName }} · {{ date(activeTask.createdAt) }}</p></div><button @click="emit('open-graph')">查看原始图谱 ↗</button></div>
          <div class="lp-query-line"><span>当前食材</span><strong>{{ activeTask.targetName }}</strong><i>→</i><b>可能的搭配</b></div>
          <div class="lp-notice"><strong>结果说明</strong><span>建议根据两段已观察到的共现线索排序，不代表目标食材与候选食材一定搭配，也可能已出现在未展示的食谱中。请进一步核查原始食谱。</span></div>
          <div class="lp-notice"><strong>所选模型</strong><span>{{ activeTask.model }} · 演示选择；本次排序未运行该模型，也没有使用关系置信度。</span></div>
          <div class="lp-candidate-section"><div class="lp-section-head"><div><span>SUGGESTIONS</span><h3>待核查的搭配建议</h3></div><small>{{ activeTask.candidates.length }} 条</small></div>
            <p v-if="!activeTask.candidates.length" class="lp-no-candidate">当前参考范围内没有找到新的建议。可以换一种食材再试。</p>
            <div v-else class="lp-candidate-grid"><div class="lp-candidate-list"><button v-for="(item,index) in activeTask.candidates" :key="item.id" :class="{active:activeCandidate?.id===item.id}" @click="candidateId=item.id"><span class="lp-rank">{{ String(index+1).padStart(2,'0') }}</span><div><strong>{{ activeTask.targetName }} ＋ {{ item.name }}</strong><small>{{ item.supportCount }} 条共同食材线索</small></div><span class="lp-score">查看 →</span></button></div>
              <aside v-if="activeCandidate" class="lp-evidence"><span class="lp-evidence-kicker">搭配建议 · 待核查</span><h4>{{ activeTask.targetName }} ＋ {{ activeCandidate.name }}</h4><p>由 {{ activeCandidate.supportCount }} 条间接线索支持；以下两段共现分别来自原始食谱统计。</p><div v-for="reference in activeCandidate.references" :key="reference.via" class="lp-reference"><div><strong>参考食材：{{ reference.via }}</strong></div><p>{{ activeTask.targetName }} 与 {{ reference.via }} 共现 {{ reference.targetCount }} 次；{{ reference.via }} 与 {{ activeCandidate.name }} 共现 {{ reference.candidateCount }} 次。</p></div><small>来源：Food.com 食谱共现索引；此处未证明目标与候选直接共现。</small></aside>
            </div>
          </div>
        </template>
      </section>
    </div>
    <div v-if="dialog" class="lp-modal-backdrop" @click.self="dialog=false"><section class="lp-modal" role="dialog" aria-modal="true" aria-labelledby="fc-dialog-title"><div class="lp-modal-head"><div><span>NEW TASK</span><h2 id="fc-dialog-title">创建搭配发现任务</h2><p>以 {{ detail?.name }} 为目标食材</p></div><button aria-label="关闭" @click="dialog=false">×</button></div><div class="lp-modal-body"><label>任务名称<input v-model="formName" maxlength="100" placeholder="给任务起个名字"></label><div class="lp-form-row"><label>展示模型<select v-model="formModel"><option v-for="model in modelOptions" :key="model" :value="model">{{ model }}</option></select></label><label>最多显示建议<select v-model.number="formLimit"><option :value="5">5 条</option><option :value="10">10 条</option><option :value="20">20 条</option><option :value="30">30 条</option></select></label></div><p class="lp-modal-tip">模型名称仅用于页面演示。当前从真实共现中查找间接线索，按支持线索数排序；候选不写入原始食谱。</p><p v-if="formError" class="lp-error" role="alert">{{ formError }}</p></div><div class="lp-modal-actions"><button @click="dialog=false">取消</button><button class="lp-primary" :disabled="busy" @click="createTask">{{ busy ? '正在整理线索…' : '创建任务并查看建议' }}</button></div></section></div>
  </div>
</template>

<style scoped>
.fc-head{display:flex;justify-content:space-between;align-items:center;gap:18px}.fc-head p{margin:0;color:#71877a;font-size:13px}.fc-observed{margin-top:20px;border-top:1px solid #e5eee8;padding-top:17px}.fc-observed h4{margin:0 0 13px;color:#245640}.fc-observed h4 small{font-size:12px;font-weight:400;color:#7b9385}.fc-observed-list{display:flex;flex-wrap:wrap;gap:8px}.fc-observed-list span{background:#eef7f1;border:1px solid #d8e9de;border-radius:7px;padding:7px 10px;color:#35634d;font-size:12px}.fc-observed-list small{color:#799488}.fc-observed p{font-size:12px;color:#71877a;margin:13px 0 0;line-height:1.6}@media(max-width:700px){.fc-head{align-items:flex-start;flex-direction:column}}
</style>
