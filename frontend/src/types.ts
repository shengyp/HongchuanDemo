export type NutrientKey = 'energy_kcal' | 'protein_g' | 'fat_g' | 'carbs_g' | 'fiber_g' | 'sodium_mg'
export type Nutrients = Record<NutrientKey, number>
export interface NutritionDatasetOption { id: 'current' | 'demo'; name: string; is_demo: boolean }
export interface Summary { ingredient_count: number; recipe_count: number; tail_count: number; tail_threshold: number; edge_count: number; nutrients: Record<NutrientKey, string>; dataset_title: string; is_demo: boolean }
export interface IngredientRow { id: string; name: string; category: string; frequency: number; tail: boolean }
export interface Ingredient { id: string; name: string; category?: string; per_100g: Nutrients }
export interface SimilarIngredient { id: string; name: string; score: number; frequency: number }
export interface Neighbor { id: string; name: string; score: number; source: 'observed' | 'inferred' }
export interface IngredientDetail { ingredient: Ingredient; frequency: number; tail: boolean; similar: SimilarIngredient[]; neighbors: Neighbor[] }
export interface RecipePart { name: string; grams: number }
export interface InferredLink { requested: string; matched: string; score: number }
export interface Recommendation { id: string; name: string; score: number; nutrition_score: number; preference_score: number; nutrition: Nutrients; ingredients: RecipePart[]; servings: number; tail_ingredients: string[]; inferred_links: InferredLink[]; deviation: number | null }
export interface RecipeSummary { id: string; name: string; nutrition: Nutrients }
export interface GeneratedRecipe { source_id: string; source_name: string; servings: number; ingredients: (RecipePart & { id: string })[]; nutrition: Nutrients; targets: Partial<Nutrients>; deviations: Partial<Nutrients>; max_deviation: number; passed: boolean; tolerance: number; iterations: number; method: string }
export interface ImportData { ingredients: Ingredient[]; recipes: { id: string; name: string; servings: number; ingredients: { id: string; grams: number }[] }[] }
export interface User { id: number; username: string }
export interface ConversationSummary { id: number; title: string; updated_at: number }
export interface ChatMessage { id: number; role: 'user' | 'assistant'; content: string; mode: string; created_at: number }
export interface Conversation extends ConversationSummary { messages: ChatMessage[]; references?: { name: string; score: number; per_serving: Nutrients }[] }
export interface ModelOption { id: string; label: string; provider: string; available: boolean; message: string }
export interface ModelCatalog { default: string; models: ModelOption[] }
export interface SourceCatalog { source: string | null; source_file?: string; sha256?: string; foundation_count?: number; complete_count?: number; selection?: string; records: { fdc_id: string; name: string; publication_date: string; per_100g: Nutrients; energy_nutrient_id: string }[] }
export interface FoodcomIngredient { id: number; name: string; frequency: number }
export interface FoodcomRecipe { id: number; name: string; minutes?: number; ingredient_count?: number }
export interface FoodcomSummary { available: boolean; source?: string; source_file?: string; recipe_count?: number; ingredient_count?: number; tail_count?: number; link_count?: number; tail_threshold?: number; skipped_rows?: number; note?: string; top_ingredients?: FoodcomIngredient[]; tail_examples?: FoodcomIngredient[] }
export interface FoodcomGraphStatistics {
  available: boolean; node_count: number; edge_count: number; entity_type_count: number; relation_type_count: number
  node_types: KgCount[]; relation_types: KgCount[]; frequency_bins: { label: string; count: number }[]
}
export interface FoodcomGraphTriple {
  recipe_id: number; recipe_name: string; ingredient_id: number; ingredient_name: string; ingredient_frequency: number
}
export interface FoodcomGraphTriplePage {
  items: FoodcomGraphTriple[]; total: number; page: number; page_size: number
}
export interface FoodcomSearch { ingredients: FoodcomIngredient[]; recipes: FoodcomRecipe[] }
export interface FoodcomDetail extends FoodcomIngredient { tail: boolean; neighbors: (FoodcomIngredient & { cooccur: number })[]; recipes: FoodcomRecipe[] }

export interface KgDataset { id: number; name: string; filename: string; source: string; imported_at: string; triple_count: number }
export interface KgCount { name: string; count: number }
export interface KgSummary {
  available: boolean; datasets: KgDataset[]; dataset: KgDataset | null
  node_count?: number; edge_count?: number; entity_type_count?: number; relation_type_count?: number
  node_types?: KgCount[]; relation_types?: KgCount[]; confidence_bins?: { label: string; count: number }[]
  average_confidence?: number
}
export interface KgTriple {
  id: number; dataset_id: number; head: string; relation: string; tail: string; confidence: number | null
  head_id?: string; tail_id?: string
  evidence: string; source: string; head_type: string; tail_type: string
}
export interface KgTriplePage { items: KgTriple[]; total: number; page: number; page_size: number }

export interface KgGraphNode { id: string; label: string; type: string; degree: number }
export interface KgExplore {
  dataset: KgDataset | null; focus: KgGraphNode | null
  nodes: KgGraphNode[]; edges: KgTriple[]; depth: number
}

export interface PredictionEntity { name: string; type: string; degree: number }
export interface PredictionTaskSummary {
  id: number; dataset_id: number; dataset_name: string; name: string; target_name: string; target_type: string
  relation: string; method: string; created_at: string; candidate_count: number
}
export interface PredictionReference {
  reference_id: number; similar_entity: string
  shared_neighbors: { relation: string; entity: string; entity_type: string }[]
  similarity: number; observed_confidence: number; source: string; evidence: string
}
export interface PredictionCandidate {
  rank: number; tail: string; tail_type: string; score: number
  support_count: number; status: string; references: PredictionReference[]
}
export interface PredictionTask {
  id: number; name: string; created_at: string; dataset: KgDataset
  target_name: string; target_type: string; relation: string; method: string
  note: string; existing_count: number; candidates: PredictionCandidate[]
}

export interface DiyCheck { key: NutrientKey; actual: number; target: number; deviation: number; passed: boolean }
export interface DiyEvidenceRecipe { id: number; name: string; ingredient_count: number; overlap: number; similarity: number }
export interface DiyPairEvidence {
  first: string; second: string; count: number; mapped: boolean
  examples: { id: number; name: string }[]
}
export interface DiyEvidence {
  available: boolean; source?: string
  mapped: { local_id: string; local_name: string; foodcom_id: number; foodcom_name: string; frequency: number }[]
  unmapped: string[]; related_recipes: DiyEvidenceRecipe[]
  pairs: DiyPairEvidence[]; pair_total: number; pair_supported: number
  pair_strength?: number; support_score: number | null; note: string
}
export interface DiyAssessment {
  dataset_title: string; is_demo_nutrition: boolean
  parts: { id: string; name: string; grams: number }[]; servings: number
  nutrition: Nutrients; nutrition_score: number; checks: DiyCheck[]
  nutrition_passed: boolean; evidence: DiyEvidence
}

