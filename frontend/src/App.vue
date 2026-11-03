<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from './api'
import ChatPanel from './components/ChatPanel.vue'
import DataPanel from './components/DataPanel.vue'
import DataQualityPanel from './components/DataQualityPanel.vue'
import DiyPanel from './components/DiyPanel.vue'
import FoodcomPanel from './components/FoodcomPanel.vue'
import GeneratePanel from './components/GeneratePanel.vue'
import KgDataPanel from './components/KgDataPanel.vue'
import LinkPredictionPanel from './components/LinkPredictionPanel.vue'
import KgExplorePanel from './components/KgExplorePanel.vue'
import RecipePanel from './components/RecipePanel.vue'
import EvaluationDemoPanel from './components/EvaluationDemoPanel.vue'
import type { IngredientRow, NutritionDatasetOption, Summary, User } from './types'

type ModuleId = 'data' | 'graph' | 'task' | 'diy' | 'qa'
type SectionId = 'linktasks' | 'kg' | 'kgviz' | 'data' | 'quality' | 'foodcom' | 'chat' | 'recipes' | 'generate' | 'diy' | 'evaluation'
interface ModuleItem {
  id: ModuleId
  number: string
  title: string
  english: string
  description: string
  focus: string[]
  sections: { id: SectionId; label: string; description: string }[]
}
const modules: ModuleItem[] = [
  {
    id: 'data', number: '01', title: '数据管理', english: 'DATA MANAGEMENT',
    description: '上传和查看食谱、食材营养等数据，了解每份数据可以用来做什么。',
    focus: ['上传数据', '查看数据来源', '浏览真实食谱'],
    sections: [
      { id: 'kg', label: '不确定知识管理', description: '上传三元组数据集并查看图谱' },
      { id: 'data', label: '营养数据管理', description: '导入营养表和食谱组成' },
      { id: 'quality', label: '数据来源说明', description: '了解食谱和营养数据怎么用' },
      { id: 'foodcom', label: '真实食谱数据', description: '浏览 Food.com 索引' },
    ],
  },
  {
    id: 'graph', number: '02', title: '知识图谱可视化', english: 'KNOWLEDGE GRAPH EXPLORER',
    description: '选择一个数据集，直观看看食材、食谱之间有哪些联系。',
    focus: ['选择数据集', '查看关系', '了解来源'],
    sections: [
      { id: 'kgviz', label: '知识图谱可视化', description: '探索 Food.com 与上传图谱的实体关系' },
    ],
  },
  {
    id: 'task', number: '03', title: '食材关联发现', english: 'INGREDIENT RELATION DISCOVERY',
    description: '选择食材，发现可能的搭配，并查看这些建议参考了哪些已有食谱。',
    focus: ['选择食材', '获取搭配建议', '查看依据'],
    sections: [
      { id: 'linktasks', label: '发现食材搭配', description: '寻找可能的食材搭配' },
      { id: 'recipes', label: '个性化食谱推荐', description: '目标与偏好联合排序' },
      { id: 'generate', label: '调整食材用量', description: '按营养目标调整克数' },
    ],
  },
  {
    id: 'diy', number: '04', title: 'DIY 食谱与评估', english: 'DIY RECIPE EVIDENCE ASSESSMENT',
    description: '输入自己的食谱，看看搭配是否常见、营养目标是否达到。',
    focus: ['输入食谱', '查看搭配依据', '比较结果'],
    sections: [
      { id: 'diy', label: 'DIY 食谱评分', description: '查看证据和营养两类得分' },
      { id: 'evaluation', label: '食谱效果对比', description: '比较调整前后的结果' },
    ],
  },
  {
    id: 'qa', number: '05', title: '营养食谱问答', english: 'NUTRITION QUESTION ANSWERING',
    description: '像聊天一样询问食材搭配、食谱和营养问题，并查看回答依据。',
    focus: ['发起对话', '选择模型', '查看依据'],
    sections: [
      { id: 'chat', label: '营养食谱问答', description: '选择模型并管理对话' },
    ],
  },
]
const user = ref<User | null>(null)
const loading = ref(true)
const error = ref('')
const summary = ref<Summary | null>(null)
const nutritionOptions = ref<NutritionDatasetOption[]>([])
const nutritionDataset = ref<'current' | 'demo'>('demo')
const nutritionSections = new Set<SectionId>(['recipes','generate','diy','evaluation'])
const ingredients = ref<IngredientRow[]>([])
const activeModule = ref<ModuleId>('data')
const activeSection = ref<SectionId>('kg')
const current = computed(() => modules.find(item => item.id === activeModule.value)!)

async function changeNutritionDataset(event: Event): Promise<void> {
  const value = (event.target as HTMLSelectElement).value
  if (value !== 'current' && value !== 'demo') return
  nutritionDataset.value = value
  error.value = ''
  try { await loadWorkspace() }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '营养数据集切换失败' }
}
async function refreshAfterImport(): Promise<void> {
  nutritionOptions.value = await api.nutritionDatasets()
  nutritionDataset.value = nutritionOptions.value.some(item => item.id === 'current') ? 'current' : 'demo'
  await loadWorkspace()
}
function retry(): void { window.location.reload() }
function activate(id: ModuleId): void {
  activeModule.value = id
  activeSection.value = modules.find(item => item.id === id)!.sections[0]!.id
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function selectSection(id: SectionId): void { activeSection.value = id }
async function loadWorkspace(): Promise<void> {
  const [newSummary, newIngredients] = await Promise.all([api.summary(nutritionDataset.value), api.ingredients(nutritionDataset.value)])
  summary.value = newSummary
  ingredients.value = newIngredients
}
onMounted(async () => {
  try {
    user.value = await api.me()
    nutritionOptions.value = await api.nutritionDatasets()
    nutritionDataset.value = nutritionOptions.value.some(item => item.id === 'current') ? 'current' : 'demo'
    await loadWorkspace()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '页面加载失败' }
  finally { loading.value = false }
})
</script>

<template>
  <v-app>
    <div v-if="loading" class="loading-page">正在打开营养食谱研究门户…</div>
    <div v-else-if="!user || !summary" class="loading-page">页面暂时无法打开。{{ error }} <button @click="retry">重试</button></div>
    <div v-else class="portal-layout" :data-module="activeModule">
      <header class="portal-header">
        <div class="portal-width portal-header-inner">
          <button class="portal-brand" @click="activate('data')" aria-label="返回数据管理"><span class="portal-brand-mark">✦</span><span><strong>NutriGraph</strong><small>营养食谱研究平台</small></span></button>
          <nav class="portal-nav" aria-label="主要功能">
            <v-btn v-for="item in modules" :key="item.id" variant="text" :class="{active:activeModule===item.id}" @click="activate(item.id)">{{ item.title }}</v-btn>
          </nav>
          <div class="portal-account"><span class="portal-account-avatar">体</span><span>体验用户</span></div>
        </div>
      </header>

      <main class="portal-main">
        <div class="portal-width portal-body" :class="{'portal-body-chat':activeModule==='qa'}">
          <div v-if="error" class="global-error">{{ error }}</div>
          <nav v-if="current.sections.length > 1" class="portal-section-nav" aria-label="本模块功能">
            <button v-for="item in current.sections" :key="item.id" class="portal-subtab" :class="{active:activeSection===item.id}" @click="selectSection(item.id)">{{ item.label }}</button>
          </nav>
          <div v-if="nutritionSections.has(activeSection)" class="dataset-context portal-dataset-context">
            <label>营养计算数据集<select :value="nutritionDataset" @change="changeNutritionDataset"><option v-for="item in nutritionOptions" :key="item.id" :value="item.id">{{ item.name }}{{ item.is_demo ? ' · 演示' : '' }}</option></select></label>
            <label v-if="activeSection==='diy'">食谱证据数据集<select value="foodcom"><option value="foodcom">Food.com 食谱数据 · 默认</option></select></label>
            <p>{{ activeSection==='diy' ? '营养值与真实食谱搭配证据分别读取。' : '本模块按所选营养数据集计算；Food.com 用于真实食谱检索与 DIY 搭配证据。' }}</p>
          </div>
          <div id="module-content" class="portal-content" :key="activeSection + '-' + nutritionDataset">
            <KgDataPanel v-if="activeSection==='kg'" @open-foodcom="activeSection='foodcom'" />
            <DataPanel v-else-if="activeSection==='data'" :summary="summary" @changed="refreshAfterImport" />
            <DataQualityPanel v-else-if="activeSection==='quality'" />
            <FoodcomPanel v-else-if="activeSection==='foodcom'" />
            <KgExplorePanel v-else-if="activeSection==='kgviz'" @open-upload="activate('data')" />
            <EvaluationDemoPanel v-else-if="activeSection==='evaluation'" />
            <LinkPredictionPanel v-else-if="activeSection==='linktasks'" @open-upload="activate('data')" @open-graph="activate('graph')" />
            <ChatPanel v-else-if="activeSection==='chat'" />
            <RecipePanel :nutrition-dataset="nutritionDataset" v-else-if="activeSection==='recipes'" :summary="summary" :ingredients="ingredients" />
            <GeneratePanel :nutrition-dataset="nutritionDataset" v-else-if="activeSection==='generate'" :summary="summary" />
            <DiyPanel :nutrition-dataset="nutritionDataset" v-else-if="activeSection==='diy'" :summary="summary" :ingredients="ingredients" />
          </div>
        </div>
      </main>
    </div>
  </v-app>
</template>
