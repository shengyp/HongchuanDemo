<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { api } from '../api'
import type { ChatMessage, Conversation } from '../types'

type RecipeReference = NonNullable<Conversation['references']>[number]
type SavedConversation = { id: string; title: string; updated_at: number; messages: ChatMessage[]; references?: RecipeReference[]; server_id?: number }
const storageKey = 'nutrigraph-chat-history-v2'
const modelKey = 'nutrigraph-chat-model-v2'
const deletedLegacyKey = 'nutrigraph-chat-deleted-legacy-v2'
const models = [
  { id: 'knowledge', label: '知识检索', provider: '系统内置' },
  { id: 'gpt', label: 'GPT 系列', provider: 'OpenAI' },
  { id: 'claude', label: 'Claude 系列', provider: 'Anthropic' },
  { id: 'gemini', label: 'Gemini 系列', provider: 'Google' },
  { id: 'deepseek', label: 'DeepSeek 系列', provider: 'DeepSeek' },
  { id: 'qwen', label: '通义千问 Qwen', provider: '阿里云' },
  { id: 'kimi', label: 'Kimi 系列', provider: '月之暗面' },
  { id: 'doubao', label: '豆包系列', provider: '字节跳动' },
  { id: 'glm', label: '智谱 GLM', provider: '智谱' },
  { id: 'llama', label: 'Llama 系列', provider: 'Meta' },
] as const
type ModelId = typeof models[number]['id']
function loadHistory(): SavedConversation[] {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey) || '[]')
    return Array.isArray(value) ? value.filter(item => item && typeof item.id === 'string' && Array.isArray(item.messages)) : []
  } catch { return [] }
}
const histories = ref<SavedConversation[]>(loadHistory())
const selectedId = ref<string | null>(null)
const selectedModel = ref<ModelId>(models.some(item => item.id === localStorage.getItem(modelKey)) ? localStorage.getItem(modelKey) as ModelId : 'knowledge')
const question = ref('')
const search = ref('')
const status = ref('')
const busy = ref(false)
const nutritionDataset = ref<'current' | 'demo'>('demo')
const scroller = ref<HTMLElement | null>(null)
const active = computed(() => histories.value.find(item => item.id === selectedId.value) ?? null)
const activeReferences = computed(() => active.value?.references ?? [])
const sorted = computed(() => [...histories.value].sort((a, b) => b.updated_at - a.updated_at).filter(item => item.title.toLowerCase().includes(search.value.trim().toLowerCase())))
const suggestions = ['推荐一道高蛋白午餐', '我想吃豆腐，如何搭配？', '什么是长尾食材？']
function persist(): void { localStorage.setItem(storageKey, JSON.stringify(histories.value)) }
function newChat(): void { selectedId.value = null; question.value = ''; status.value = '' }
function selectChat(id: string): void { selectedId.value = id; status.value = ''; void nextTick(scrollBottom) }
function deleteChat(id: string): void {
  histories.value = histories.value.filter(item => item.id !== id)
  if (id.startsWith('legacy:')) {
    const deleted = new Set(JSON.parse(localStorage.getItem(deletedLegacyKey) || '[]') as string[])
    deleted.add(id)
    localStorage.setItem(deletedLegacyKey, JSON.stringify([...deleted]))
  }
  if (selectedId.value === id) selectedId.value = null
  persist()
}
function chooseModel(id: ModelId | null): void {
  if (!id) return
  selectedModel.value = id
  localStorage.setItem(modelKey, selectedModel.value)
}
function scrollBottom(): void { scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' }) }
async function send(text = question.value): Promise<void> {
  const value = text.trim()
  if (!value || busy.value) return
  const now = Date.now()
  let conversation = active.value
  if (!conversation) {
    conversation = { id: crypto.randomUUID(), title: value.slice(0, 28), updated_at: now, messages: [] }
    histories.value.unshift(conversation)
    selectedId.value = conversation.id
  }
  conversation.references = []
  conversation.messages.push({ id: now, role: 'user', content: value, mode: selectedModel.value, created_at: now })
  conversation.updated_at = now
  question.value = ''
  persist()
  void nextTick(scrollBottom)
  if (selectedModel.value !== 'knowledge') {
    status.value = '提问已保存。所选模型仅为前端演示，尚未生成回答。'
    return
  }
  busy.value = true
  status.value = '正在通过系统知识检索生成回答…'
  try {
    const result = await api.chat(value, conversation.server_id ?? null, 'knowledge', nutritionDataset.value)
    conversation.server_id = result.id
    conversation.references = result.references ?? []
    const reply = [...result.messages].reverse().find(item => item.role === 'assistant')
    if (reply) conversation.messages.push(reply)
    conversation.updated_at = Date.now()
    persist()
    status.value = ''
    await nextTick()
    scrollBottom()
  } catch (cause) {
    status.value = cause instanceof Error ? '知识检索失败：' + cause.message : '知识检索失败，提问已保存在本地。'
  } finally { busy.value = false }
}
function onKey(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() }
}
function modelLabel(id: string): string { return id === 'knowledge' ? '知识检索' : models.find(item => item.id === id)?.label ?? id }
function groupLabel(timestamp: number): string {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  if (timestamp >= today.getTime()) return '今天'
  if (timestamp >= today.getTime() - 7 * 86400000) return '最近 7 天'
  return '更早'
}
onMounted(async () => {
  try {
    const options = await api.nutritionDatasets()
    nutritionDataset.value = options.some(item => item.id === 'current') ? 'current' : 'demo'
  } catch { /* 演示数据集作为后备 */ }
  try {
    const old = await api.conversations()
    let added = 0
    const deleted = new Set(JSON.parse(localStorage.getItem(deletedLegacyKey) || '[]') as string[])
    for (const item of old) {
      const id = 'legacy:' + item.id
      if (deleted.has(id) || histories.value.some(saved => saved.id === id || saved.server_id === item.id)) continue
      const detail = await api.conversation(item.id)
      histories.value.push({ id, title: detail.title, updated_at: detail.updated_at < 1e12 ? detail.updated_at * 1000 : detail.updated_at, messages: detail.messages, references: detail.references ?? [], server_id: item.id })
      added++
    }
    if (added) persist()
  } catch { /* 历史接口不可用时仍可使用本地对话记录 */ }
})
</script>

<template>
  <section class="chat-shell">
    <aside class="chat-history">
      <div class="chat-history-top"><strong>对话记录</strong><v-btn class="chat-history-new" variant="outlined" color="primary" prepend-icon="mdi-plus" @click="newChat">新建对话</v-btn></div>
      <input v-model="search" class="chat-history-search" placeholder="搜索对话" aria-label="搜索对话记录">
      <div class="chat-history-list">
        <p v-if="!sorted.length" class="chat-history-empty">{{ search ? '没有匹配的对话' : '暂无对话，开始提问后自动保存' }}</p>
        <template v-for="(item, index) in sorted" :key="item.id">
          <div v-if="index === 0 || groupLabel(sorted[index-1]!.updated_at) !== groupLabel(item.updated_at)" class="chat-history-group">{{ groupLabel(item.updated_at) }}</div>
          <div class="chat-history-row" :class="{active:selectedId===item.id}">
            <button class="chat-history-title" @click="selectChat(item.id)">{{ item.title }}</button>
            <button class="chat-history-delete" :aria-label="'删除对话 '+item.title" title="删除对话" @click="deleteChat(item.id)">×</button>
          </div>
        </template>
      </div>
      <p class="chat-history-foot">记录保存在当前浏览器</p>
    </aside>

    <div class="chat-main">
      <div class="chat-main-head"><div><span class="chat-main-eyebrow">NUTRITION QUESTION ANSWERING</span><h1>营养食谱问答</h1></div><div class="chat-model-picker"><label for="qa-model">选择模型</label><v-select id="qa-model" density="compact" variant="outlined" hide-details :model-value="selectedModel" :items="models.map(item => ({ title: item.label + ' · ' + item.provider, value: item.id }))" aria-label="选择模型" @update:model-value="chooseModel" /><small>知识检索可用；其他模型为界面演示</small></div></div>
      <div ref="scroller" class="chat-main-scroll">
        <div v-if="!active?.messages.length" class="chat-welcome-new"><span class="chat-welcome-icon">✦</span><h2>今天想了解什么？</h2><p>可以询问食材搭配、营养目标或食谱建议。</p><div class="chat-starters"><button v-for="item in suggestions" :key="item" @click="send(item)">{{ item }} <span>↗</span></button></div></div>
        <div v-else class="chat-message-list"><article v-for="item in active.messages" :key="item.id" class="chat-message-row" :class="item.role"><div class="chat-message-avatar">{{ item.role === 'user' ? '我' : '✦' }}</div><div class="chat-message-content"><div class="chat-message-meta">{{ item.role === 'user' ? '你' : '营养助手' }} <span>{{ modelLabel(item.mode) }}</span></div><p>{{ item.content }}</p></div></article></div>
      </div>
      <div class="chat-compose"><p v-if="status" class="chat-demo-status" role="status">{{ status }}</p><div class="chat-compose-box"><textarea v-model="question" rows="2" maxlength="3000" placeholder="输入你的问题…" aria-label="输入你的问题" :disabled="busy" @keydown="onKey"></textarea><v-btn color="primary" :loading="busy" :disabled="busy || !question.trim()" append-icon="mdi-arrow-up" @click="send()">发送</v-btn></div><small>Enter 发送 · Shift + Enter 换行</small></div>
    </div>

    <aside class="chat-reference" aria-label="本轮回答依据">
      <div class="chat-reference-head"><span>ANSWER CONTEXT</span><h2>回答依据</h2><p>当前对话最近一次回答检索到的候选食谱</p></div>
      <div v-if="activeReferences.length" class="chat-reference-list">
        <article v-for="(recipe,index) in activeReferences" :key="recipe.name + index">
          <div class="chat-reference-number">{{ String(index + 1).padStart(2, '0') }}</div>
          <h3>{{ recipe.name }}</h3>
          <p>约 {{ Math.round(recipe.per_serving.energy_kcal) }} kcal／份 · 蛋白质 {{ recipe.per_serving.protein_g.toFixed(1) }} g</p>
          <small>匹配分数 {{ recipe.score.toFixed(2) }}</small>
        </article>
      </div>
      <div v-else class="chat-reference-empty">{{ active?.messages.length ? '本轮暂无可展示的食谱依据。' : '发送问题后，这里会显示本轮检索到的候选食谱。' }}</div>
      <p class="chat-reference-foot">候选食谱用于说明回答来源，推荐结果仍需结合食材用量与营养目标核对。</p>
    </aside>
  </section>
</template>

<style scoped>
.chat-shell{display:grid;grid-template-columns:260px minmax(0,1fr);height:min(760px,calc(100vh - 120px));min-height:580px;overflow:hidden;border:1px solid #dfe9e1;border-radius:20px;background:#fff;box-shadow:0 15px 40px #164d3010}
.chat-history{display:flex;flex-direction:column;min-height:0;padding:18px 11px 10px;background:#f4f8f5;border-right:1px solid #e0eae2}
.chat-history-top{display:grid;gap:14px;padding:4px 7px 12px}.chat-history-top strong{color:#234d3b;font-size:15px}
.chat-history-new{border:1px solid #cce0d1;border-radius:10px;background:#fff;color:#176b4c;padding:10px 13px;font-weight:700;text-align:left}
.chat-history-search{margin:0 7px 12px;padding:9px 11px;border:1px solid #d9e5db;border-radius:9px;background:white;outline:none;min-width:0}
.chat-history-list{overflow:auto;flex:1;padding:0 3px}.chat-history-group{padding:12px 12px 5px;color:#799285;font-size:11px;font-weight:700}
.chat-history-row{display:flex;align-items:center;border-radius:10px;margin:2px 0}.chat-history-row:hover,.chat-history-row.active{background:#e5f2e9}
.chat-history-title{flex:1;min-width:0;border:0;background:transparent;color:#315744;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:10px 9px;font-size:12px}
.chat-history-delete{border:0;background:transparent;color:#8aa397;font-size:20px;padding:4px 9px;line-height:1}.chat-history-delete:hover{color:#b74444}
.chat-history-empty,.chat-history-foot{color:#8a9f91;font-size:11px;padding:0 10px}.chat-history-foot{margin:12px 2px 2px}
.chat-main{display:flex;flex-direction:column;min-width:0;min-height:0}
.chat-main-head{display:flex;justify-content:space-between;gap:18px;align-items:center;padding:20px 26px;border-bottom:1px solid #e9f0ea}
.chat-main-eyebrow{font-size:10px;letter-spacing:.16em;color:#29926d;font-weight:800}.chat-main-head h1{font-size:22px;margin:5px 0 0;color:#174435}
.chat-model-picker{display:grid;gap:4px;min-width:230px}.chat-model-picker label{font-size:11px;color:#6b8575;font-weight:700}.chat-model-picker select{min-height:39px;border:1px solid #cbded2;border-radius:9px;padding:7px 10px;background:#f9fcfa;color:#1b6348;font-weight:700;max-width:270px}.chat-model-picker small{font-size:10px;color:#91a69a}
.chat-main-scroll{flex:1;min-height:0;overflow:auto;padding:22px 28px}
.chat-welcome-new{text-align:center;max-width:630px;margin:clamp(40px,9vh,95px) auto}.chat-welcome-icon{display:grid;place-items:center;width:66px;height:66px;margin:auto;background:#e9f5ee;color:#278c65;border-radius:19px;font-size:32px}.chat-welcome-new h2{font-size:25px;margin:21px 0 9px;color:#203f32}.chat-welcome-new p{font-size:13px;color:#829287}
.chat-starters{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:29px}.chat-starters button{border:1px solid #dce9de;border-radius:11px;padding:13px;background:#fff;color:#426650;text-align:left}.chat-starters span{float:right;color:#23845e}
.chat-message-list{max-width:760px;margin:auto}.chat-message-row{display:flex;gap:12px;margin:20px 0}.chat-message-row.user{flex-direction:row-reverse}.chat-message-avatar{width:30px;height:30px;flex:none;border-radius:9px;display:grid;place-items:center;background:#e0f2e8;color:#207852}.chat-message-row.user .chat-message-avatar{background:#e3edf1;color:#3d7083}.chat-message-content{max-width:80%;border:1px solid #e2ece5;border-radius:13px;padding:12px 15px;background:#fff}.chat-message-row.user .chat-message-content{background:#edf7f0}.chat-message-meta{font-size:11px;font-weight:700;color:#316e50}.chat-message-meta span{font-weight:400;color:#8aa092;margin-left:7px}.chat-message-content p{white-space:pre-wrap;font-size:13px;line-height:1.7;margin:7px 0 0}
.chat-compose{padding:11px 25px 14px;border-top:1px solid #ebf0ec}.chat-compose-box{display:flex;align-items:end;gap:10px;border:1px solid #d5e4d8;border-radius:13px;padding:9px;background:#fff}.chat-compose textarea{flex:1;min-width:0;resize:none;border:0;outline:0;padding:7px;color:#243e2e}.chat-compose button{border:0;border-radius:9px;background:#148064;color:#fff;padding:10px 17px;font-weight:700}.chat-compose button:disabled{opacity:.5}.chat-compose>small{display:block;text-align:center;margin-top:6px;color:#9aab9e;font-size:10px}.chat-demo-status{font-size:11px;color:#718d7d;margin:0 0 8px}
@media(max-width:800px){.chat-shell{grid-template-columns:190px minmax(0,1fr)}.chat-main-head{padding:15px}.chat-main-scroll{padding:16px}}
@media(max-width:600px){.chat-shell{display:flex;flex-direction:column;height:750px}.chat-history{height:190px;flex:none;border-right:0;border-bottom:1px solid #e0eae2}.chat-history-top{display:flex;align-items:center;justify-content:space-between}.chat-history-new{padding:7px 9px}.chat-history-list{display:flex;gap:5px;overflow:auto}.chat-history-group,.chat-history-foot{display:none}.chat-history-row{flex:0 0 150px}.chat-history-search{margin-bottom:6px}.chat-main-head{display:block}.chat-model-picker{margin-top:10px}.chat-starters{grid-template-columns:1fr}}

/* Three-column question answering layout. */
.chat-shell{grid-template-columns:235px minmax(0,1fr) 278px}
.chat-reference{min-width:0;min-height:0;overflow:auto;padding:22px 17px;background:#f5f9fc;border-left:1px solid #e2eaf0}
.chat-reference-head{padding:2px 4px 14px;border-bottom:1px solid #e2eaf0}
.chat-reference-head span{display:block;color:#1688c0;font-size:10px;font-weight:800;letter-spacing:.14em}
.chat-reference-head h2{margin:5px 0 5px;color:#183e57;font-size:17px}
.chat-reference-head p{margin:0;color:#8295a2;font-size:11px;line-height:1.55}
.chat-reference-list{display:grid;gap:9px;margin-top:14px}
.chat-reference-list article{padding:13px 12px;border:1px solid #e2eaf0;border-radius:10px;background:#fff;box-shadow:0 3px 12px #173b5410}
.chat-reference-number{display:inline-grid;place-items:center;min-width:24px;height:24px;padding:0 5px;border-radius:6px;background:#e5f4fb;color:#1688c0;font-size:10px;font-weight:800}
.chat-reference-list h3{margin:8px 0 5px;color:#274459;font-size:12px;line-height:1.45}
.chat-reference-list p{margin:0;color:#718797;font-size:10px;line-height:1.6}
.chat-reference-list small{display:block;margin-top:8px;color:#1384b7;font-size:10px;font-weight:700}
.chat-reference-empty{margin-top:14px;padding:19px 13px;border:1px dashed #d8e7ef;border-radius:9px;background:#fff;color:#8194a2;font-size:11px;line-height:1.7}
.chat-reference-foot{margin:16px 4px 0;color:#95a5af;font-size:10px;line-height:1.6}
@media(max-width:1100px){.chat-shell{grid-template-columns:200px minmax(0,1fr) 245px}.chat-reference{padding:16px 12px}}
@media(max-width:900px){.chat-shell{grid-template-columns:190px minmax(0,1fr);overflow:visible}.chat-history,.chat-main{height:620px}.chat-reference{grid-column:1/-1;max-height:300px;border-left:0;border-top:1px solid #e2eaf0}}
@media(max-width:600px){.chat-shell{display:flex;flex-direction:column}.chat-history{height:190px}.chat-main{height:540px}.chat-reference{max-height:none;overflow:visible}}
</style>



