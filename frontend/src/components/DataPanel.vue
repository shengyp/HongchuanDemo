<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { ImportData, SourceCatalog, Summary } from '../types'

defineProps<{ summary: Summary }>()
const emit = defineEmits<{ changed: [] }>()
const message = ref('')
const busy = ref(false)
const ingredientCsv = ref<File | null>(null)
const recipeCsv = ref<File | null>(null)
const source = ref('用户整理的数据')
const catalog = ref<SourceCatalog | null>(null)
const catalogSearch = ref('')
const catalogRows = computed(() => catalog.value?.records.filter(row => `${row.fdc_id} ${row.name}`.toLowerCase().includes(catalogSearch.value.toLowerCase())).slice(0, 30) ?? [])
onMounted(async () => { try { catalog.value = await api.sourceCatalog() } catch { /* Catalog is optional. */ } })
function selectIngredient(event: Event): void { ingredientCsv.value = (event.target as HTMLInputElement).files?.[0] ?? null }
function selectRecipe(event: Event): void { recipeCsv.value = (event.target as HTMLInputElement).files?.[0] ?? null }
async function importCsv(): Promise<void> {
  if (!ingredientCsv.value || !recipeCsv.value) { message.value = '请同时选择两张 CSV 表。'; return }
  busy.value = true
  try { await api.importCsv(await ingredientCsv.value.text(), await recipeCsv.value.text(), source.value); emit('changed'); message.value = 'CSV 导入成功，数据已保存在本机。' }
  catch (error) { message.value = `导入失败：${error instanceof Error ? error.message : '未知错误'}` }
  finally { busy.value = false }
}

async function importFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  busy.value = true
  try { const data: unknown = JSON.parse(await file.text()); await api.importData(data as ImportData); emit('changed'); message.value = '导入成功，数据已保存在本机。' }
  catch (error) { message.value = `导入失败：${error instanceof Error ? error.message : '未知错误'}` }
  finally { busy.value = false; input.value = '' }
}
async function reset(): Promise<void> {
  busy.value = true
  try { await api.reset(); emit('changed'); message.value = '已恢复演示数据。' }
  catch (error) { message.value = error instanceof Error ? error.message : '恢复失败' }
  finally { busy.value = false }
}
</script>

<template>
  <div class="content-page"><div class="page-heading"><div><p class="eyebrow">DATA MANAGEMENT</p><h1>数据管理</h1><p>管理食材营养密度、食谱组成与系统演示数据。</p></div></div><section class="surface"><div class="section-title"><span class="section-icon">▣</span><div><h2>当前营养计算数据集{{ summary.is_demo ? '（演示）' : '' }}</h2><p>{{ summary.ingredient_count }} 种食材 · {{ summary.recipe_count }} 道食谱 · {{ summary.tail_count }} 个长尾食材</p></div></div><div class="data-actions"><label class="upload-button">导入 JSON 数据<input type="file" accept=".json,application/json" :disabled="busy" @change="importFile"></label><button :disabled="busy" @click="reset">恢复演示数据</button></div><p role="status">{{ message }}</p></section><section class="surface"><div class="section-title"><span class="section-icon">▤</span><div><h2>导入 CSV 数据</h2><p>按模板准备食材营养表和食谱组成表，两张表一起上传。</p></div></div><div class="csv-import-grid"><label>食材营养表 CSV<input type="file" accept=".csv,text/csv" :disabled="busy" @change="selectIngredient"><small>{{ ingredientCsv?.name ?? '尚未选择' }}</small></label><label>食谱组成表 CSV<input type="file" accept=".csv,text/csv" :disabled="busy" @change="selectRecipe"><small>{{ recipeCsv?.name ?? '尚未选择' }}</small></label><label>数据来源<input v-model="source" maxlength="300" placeholder="例如 USDA FoodData Central + 自建食谱"></label></div><p class="muted">模板位于安装目录的 templates 文件夹。营养列必须是每 100 g 数值；食谱克数是整道菜的可食部克数。</p><button class="primary" :disabled="busy" @click="importCsv">导入两张 CSV 表</button></section><section class="surface"><div class="section-title"><span class="section-icon">{ }</span><div><h2>JSON 数据格式</h2><p>也支持一次上传 JSON：食材以每 100 g 标注营养；食谱填写整道菜的克数和份数。</p></div></div><pre class="code-example">{
  "ingredients": [{
    "id": "chicken", "name": "鸡胸肉", "category": "肉类",
    "per_100g": {
      "energy_kcal": 165, "protein_g": 31, "fat_g": 3.6,
      "carbs_g": 0, "fiber_g": 0, "sodium_mg": 74
    }
  }],
  "recipes": [{
    "id": "r1", "name": "示例食谱", "servings": 1,
    "ingredients": [{"id": "chicken", "grams": 120}]
  }]
}</pre><p class="muted">演示数据仅用于功能验证，不用于真实膳食建议。</p></section><section v-if="catalog?.source" class="surface"><div class="section-title"><span class="section-icon">◉</span><div><h2>USDA 食材来源目录</h2><p>{{ catalog.complete_count }} 条六项营养齐全的 Foundation Foods 记录 / 原始主食物 {{ catalog.foundation_count }} 条</p></div></div><p class="muted">{{ catalog.selection }} 此目录与演示食谱分开保存；可依据 FDC ID 查验原始食物。</p><input v-model="catalogSearch" class="catalog-search" placeholder="搜索英文食物名称或 FDC ID"><div class="catalog-table-wrap"><table class="catalog-table"><thead><tr><th>FDC ID</th><th>食物名称</th><th>能量 kcal</th><th>蛋白质 g</th><th>脂肪 g</th><th>碳水 g</th><th>纤维 g</th><th>钠 mg</th></tr></thead><tbody><tr v-for="row in catalogRows" :key="row.fdc_id"><td>{{ row.fdc_id }}</td><td>{{ row.name }}</td><td>{{ row.per_100g.energy_kcal }}</td><td>{{ row.per_100g.protein_g }}</td><td>{{ row.per_100g.fat_g }}</td><td>{{ row.per_100g.carbs_g }}</td><td>{{ row.per_100g.fiber_g }}</td><td>{{ row.per_100g.sodium_mg }}</td></tr></tbody></table></div><p class="muted">显示前 30 条匹配结果；数值单位为每 100 g 可食部。来源文件：{{ catalog.source_file }}。</p></section></div>
</template>
