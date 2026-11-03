"""Long-tail aware recipe recommendation. All nutrient values are per serving."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

NUTRIENTS = ("energy_kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", "sodium_mg")
LABELS = {"energy_kcal": "能量 kcal", "protein_g": "蛋白质 g", "fat_g": "脂肪 g", "carbs_g": "碳水 g", "fiber_g": "膳食纤维 g", "sodium_mg": "钠 mg"}


def tokens(value: str) -> set[str]:
    value = value.lower().strip()
    words = set(re.findall(r"[a-z0-9]+", value))
    chinese = re.findall(r"[\u4e00-\u9fff]+", value)
    for phrase in chinese:
        words.add(phrase)
        words.update(phrase[i : i + 2] for i in range(len(phrase) - 1))
    return words


def cosine(a: list[float], b: list[float]) -> float:
    den = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / den if den else 0.0


def validated_data(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("数据必须是 JSON 对象")
    ingredients = data.get("ingredients")
    recipes = data.get("recipes")
    if not isinstance(ingredients, list) or not isinstance(recipes, list):
        raise ValueError("数据需要 ingredients 和 recipes 数组")
    if len(ingredients) > 10000 or len(recipes) > 100000:
        raise ValueError("数据量超出当前版本限制")
    ids = set()
    for ing in ingredients:
        if not isinstance(ing, dict) or not isinstance(ing.get("id"), str) or not ing.get("name"):
            raise ValueError("食材必须有 id 和 name")
        if ing["id"] in ids:
            raise ValueError(f"食材 id 重复：{ing['id']}")
        ids.add(ing["id"])
        nutrient = ing.get("per_100g")
        if not isinstance(nutrient, dict):
            raise ValueError(f"食材 {ing['id']} 缺少 per_100g")
        for key in NUTRIENTS:
            v = nutrient.get(key)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0:
                raise ValueError(f"食材 {ing['id']} 的 {key} 必须是非负数")
    recipe_ids = set()
    for recipe in recipes:
        if not isinstance(recipe, dict) or not isinstance(recipe.get("id"), str) or not recipe.get("name"):
            raise ValueError("食谱必须有 id 和 name")
        if recipe["id"] in recipe_ids:
            raise ValueError(f"食谱 id 重复：{recipe['id']}")
        recipe_ids.add(recipe["id"])
        if not isinstance(recipe.get("servings"), int) or recipe["servings"] < 1:
            raise ValueError(f"食谱 {recipe['id']} 的 servings 必须是正整数")
        parts = recipe.get("ingredients")
        if not isinstance(parts, list) or not parts:
            raise ValueError(f"食谱 {recipe['id']} 缺少食材")
        for part in parts:
            if not isinstance(part, dict) or part.get("id") not in ids:
                raise ValueError(f"食谱 {recipe['id']} 引用了未知食材")
            grams = part.get("grams")
            if not isinstance(grams, (int, float)) or isinstance(grams, bool) or not math.isfinite(grams) or grams <= 0:
                raise ValueError(f"食谱 {recipe['id']} 的食材克数必须为正数")
    return data


class Engine:
    def __init__(self, data: dict):
        self.data = validated_data(data)
        self.ingredients = {i["id"]: i for i in data["ingredients"]}
        self.recipes = data["recipes"]
        self.frequency = Counter()
        self.cooccur = defaultdict(Counter)
        for recipe in self.recipes:
            ids = {p["id"] for p in recipe["ingredients"]}
            self.frequency.update(ids)
            for a in ids:
                for b in ids - {a}:
                    self.cooccur[a][b] += 1
        counts = sorted(self.frequency.values())
        self.tail_threshold = counts[max(0, math.ceil(len(counts) * 0.25) - 1)] if counts else 0

    def is_tail(self, ingredient_id: str) -> bool:
        return self.frequency[ingredient_id] <= self.tail_threshold

    def similar_ingredients(self, ingredient_id: str, limit: int = 3) -> list[dict]:
        source = self.ingredients[ingredient_id]
        a = [math.log1p(source["per_100g"][k]) for k in NUTRIENTS]
        a = [x / max(1, max(a)) for x in a]
        out = []
        for other_id, other in self.ingredients.items():
            if other_id == ingredient_id or self.frequency[other_id] <= self.frequency[ingredient_id]:
                continue
            b = [math.log1p(other["per_100g"][k]) for k in NUTRIENTS]
            b = [x / max(1, max(b)) for x in b]
            text_a, text_b = tokens(source["name"]), tokens(other["name"])
            name_sim = len(text_a & text_b) / len(text_a | text_b) if text_a | text_b else 0
            category_sim = 1.0 if source.get("category") and source.get("category") == other.get("category") else 0.0
            score = 0.55 * cosine(a, b) + 0.30 * category_sim + 0.15 * name_sim
            out.append({"id": other_id, "name": other["name"], "score": round(score, 3), "frequency": self.frequency[other_id]})
        return sorted(out, key=lambda x: (-x["score"], -x["frequency"]))[:limit]

    def compensated_neighbors(self, ingredient_id: str) -> list[dict]:
        """Transfer weak association evidence; never alter factual nutrient values."""
        observed = self.cooccur[ingredient_id]
        proposed = defaultdict(float)
        if self.is_tail(ingredient_id):
            for parent in self.similar_ingredients(ingredient_id):
                if parent["score"] < 0.65:
                    continue
                for neighbor, count in self.cooccur[parent["id"]].items():
                    if neighbor != ingredient_id and neighbor not in observed:
                        proposed[neighbor] = max(proposed[neighbor], parent["score"] * min(1, count / 3))
        result = [{"id": j, "name": self.ingredients[j]["name"], "score": round(v, 3), "source": "observed"} for j, v in observed.items()]
        result += [{"id": j, "name": self.ingredients[j]["name"], "score": round(v, 3), "source": "inferred"} for j, v in proposed.items()]
        return sorted(result, key=lambda x: -x["score"])[:12]

    def nutrition(self, recipe: dict) -> dict:
        servings = recipe["servings"]
        return {key: round(sum(self.ingredients[p["id"]]["per_100g"][key] * p["grams"] / 100 for p in recipe["ingredients"]) / servings, 2) for key in NUTRIENTS}

    def summary(self) -> dict:
        tail = [i for i in self.ingredients if self.is_tail(i)]
        title = self.data.get("metadata", {}).get("title", "未命名数据集")
        return {"ingredient_count": len(self.ingredients), "recipe_count": len(self.recipes), "tail_count": len(tail), "tail_threshold": self.tail_threshold, "edge_count": sum(len(x) for x in self.cooccur.values()), "nutrients": LABELS, "dataset_title": title, "is_demo": title == "功能演示数据"}

    def ingredient_rows(self) -> list[dict]:
        return sorted(({"id": key, "name": value["name"], "category": value.get("category", ""), "frequency": self.frequency[key], "tail": self.is_tail(key)} for key, value in self.ingredients.items()), key=lambda x: (x["frequency"], x["name"]))

    def recommend(self, targets: dict, likes: list[str], dislikes: list[str], limit: int = 10) -> list[dict]:
        likes = [x for x in likes if x in self.ingredients]
        dislikes = set(x for x in dislikes if x in self.ingredients)
        out = []
        for recipe in self.recipes:
            ids = {p["id"] for p in recipe["ingredients"]}
            if ids & dislikes:
                continue
            nutrition = self.nutrition(recipe)
            deviations = []
            for key, target in targets.items():
                if key not in NUTRIENTS or not isinstance(target, (int, float)) or target <= 0:
                    continue
                if key == "sodium_mg":
                    deviations.append(max(0, nutrition[key] - target) / target)
                elif key == "fiber_g":
                    deviations.append(max(0, target - nutrition[key]) / target)
                else:
                    deviations.append(abs(nutrition[key] - target) / target)
            nutrition_score = max(0, 1 - sum(deviations) / len(deviations)) if deviations else 0.5
            direct = len(ids & set(likes)) / len(likes) if likes else 0
            inferred = []
            for like in likes:
                if like in ids or not self.is_tail(like):
                    continue
                links = {x["id"]: x for x in self.compensated_neighbors(like) if x["source"] == "inferred"}
                matches = [links[x] for x in ids & links.keys()]
                if matches:
                    best = max(matches, key=lambda x: x["score"])
                    inferred.append({"requested": self.ingredients[like]["name"], "matched": best["name"], "score": best["score"]})
            preference_score = min(1, direct + 0.35 * sum(x["score"] for x in inferred) / max(1, len(likes)))
            score = 0.7 * nutrition_score + 0.3 * preference_score
            out.append({"id": recipe["id"], "name": recipe["name"], "score": round(score, 3), "nutrition_score": round(nutrition_score, 3), "preference_score": round(preference_score, 3), "nutrition": nutrition, "ingredients": [{"name": self.ingredients[p["id"]]["name"], "grams": p["grams"]} for p in recipe["ingredients"]], "servings": recipe["servings"], "tail_ingredients": [self.ingredients[x]["name"] for x in ids if self.is_tail(x)], "inferred_links": inferred, "deviation": round(sum(deviations) / len(deviations), 3) if deviations else None})
        return sorted(out, key=lambda x: (-x["score"], x["id"]))[:limit]
