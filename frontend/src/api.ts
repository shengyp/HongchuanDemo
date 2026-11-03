import type { Conversation, ConversationSummary, DiyAssessment, FoodcomDetail, FoodcomGraphStatistics, FoodcomGraphTriplePage, FoodcomSearch, FoodcomSummary, GeneratedRecipe, IngredientDetail, IngredientRow, ImportData, KgExplore, KgSummary, KgTriplePage, ModelCatalog, NutritionDatasetOption, NutrientKey, PredictionEntity, PredictionTask, PredictionTaskSummary, RecipeSummary, Recommendation, SourceCatalog, Summary, User } from './types'

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const result: unknown = await response.json()
  if (!response.ok) throw new Error(typeof result === 'object' && result !== null && 'error' in result ? String(result.error) : '请求失败')
  return result as T
}

export const api = {
  me: () => request<User>('/api/me'),
  login: (username: string, password: string) => request<User>('/api/login', { username, password }),
  register: (username: string, password: string) => request<User>('/api/register', { username, password }),
  logout: () => request<{ ok: boolean }>('/api/logout', {}),
  conversations: () => request<ConversationSummary[]>('/api/conversations'),
  conversation: (id: number) => request<Conversation>(`/api/conversations/${id}`),
  chat: (question: string, conversation_id: number | null, model_id: string, nutrition_dataset = 'current') => request<Conversation>('/api/chat', { question, conversation_id, model_id, nutrition_dataset }),
  models: () => request<ModelCatalog>('/api/models'),
  nutritionDatasets: () => request<NutritionDatasetOption[]>('/api/nutrition-datasets'),
  summary: (nutrition_dataset = 'current') => request<Summary>('/api/summary?nutrition_dataset=' + nutrition_dataset),
  ingredients: (nutrition_dataset = 'current') => request<IngredientRow[]>('/api/ingredients?nutrition_dataset=' + nutrition_dataset),
  sourceCatalog: () => request<SourceCatalog>('/api/source-catalog'),
  foodcomSummary: () => request<FoodcomSummary>('/api/foodcom/summary'),
  foodcomGraphStatistics: () => request<FoodcomGraphStatistics>('/api/foodcom/graph-statistics'),
  foodcomGraphExplore: (q: string, nodeType: string, depth: number) => request<KgExplore>('/api/foodcom/graph-explore?q=' + encodeURIComponent(q) + '&node_type=' + encodeURIComponent(nodeType) + '&depth=' + depth),
  foodcomGraphTriples: (q: string, page: number) => request<FoodcomGraphTriplePage>('/api/foodcom/graph-triples?q=' + encodeURIComponent(q) + '&page=' + page),
  foodcomSearch: (query: string) => request<FoodcomSearch>(`/api/foodcom/search?q=${encodeURIComponent(query)}`),
  foodcomIngredient: (id: number) => request<FoodcomDetail>(`/api/foodcom/ingredient/${id}`),
  ingredient: (id: string, nutrition_dataset = 'current') => request<IngredientDetail>(`/api/ingredient/${encodeURIComponent(id)}?nutrition_dataset=${nutrition_dataset}`),
  recommend: (targets: Partial<Record<NutrientKey, number>>, likes: string[], dislikes: string[], nutrition_dataset = 'current') => request<Recommendation[]>('/api/recommend', { targets, likes, dislikes, nutrition_dataset }),
  recipes: (nutrition_dataset = 'current') => request<RecipeSummary[]>('/api/recipes?nutrition_dataset=' + nutrition_dataset),
  generate: (recipe_id: string, targets: Partial<Record<NutrientKey, number>>, nutrition_dataset = 'current') => request<GeneratedRecipe>('/api/generate', { recipe_id, targets, nutrition_dataset }),
  importCsv: (ingredient_csv: string, recipe_csv: string, source: string) => request<Summary>('/api/import-csv', { ingredient_csv, recipe_csv, source }),
  importData: (data: ImportData) => request<Summary>('/api/import', data),
  kgSummary: (datasetId?: number) => request<KgSummary>('/api/kg/summary' + (datasetId ? '?dataset_id=' + datasetId : '')),
  kgTriples: (datasetId: number, q: string, page: number) => request<KgTriplePage>('/api/kg/triples?dataset_id=' + datasetId + '&q=' + encodeURIComponent(q) + '&page=' + page),
  kgExplore: (datasetId: number, q: string, nodeType: string, relation: string, depth: number) => request<KgExplore>('/api/kg/explore?dataset_id=' + datasetId + '&q=' + encodeURIComponent(q) + '&node_type=' + encodeURIComponent(nodeType) + '&relation=' + encodeURIComponent(relation) + '&depth=' + depth),
  predictionEntities: (datasetId: number, q: string, relation: string) => request<PredictionEntity[]>('/api/kg/entities?dataset_id=' + datasetId + '&q=' + encodeURIComponent(q) + '&relation=' + encodeURIComponent(relation)),
  predictionTasks: () => request<PredictionTaskSummary[]>('/api/kg/prediction-tasks'),
  predictionTask: (id: number) => request<PredictionTask>('/api/kg/prediction-tasks/' + id),
  createPredictionTask: (name: string, dataset_id: number, target_name: string, target_type: string, relation: string, max_candidates: number) => request<PredictionTask>('/api/kg/prediction-tasks', { name, dataset_id, target_name, target_type, relation, max_candidates }),
  kgImport: (filename: string, content: string, dataset_name: string, source: string) => request<KgSummary>('/api/kg/import', { filename, content, dataset_name, source }),
  kgRename: (dataset_id: number, name: string) => request<KgSummary>('/api/kg/datasets/rename', { dataset_id, name }),
  kgDelete: (dataset_id: number) => request<KgSummary>('/api/kg/datasets/delete', { dataset_id }),
  diyAssess: (parts: { id: string; grams: number }[], servings: number, targets: Record<NutrientKey, number>, nutrition_dataset = 'current') => request<DiyAssessment>('/api/diy/assess', { parts, servings, targets, nutrition_dataset }),
  reset: () => request<Summary>('/api/reset', {}),
}
