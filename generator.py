"""Deterministic portion adjustment with explicit nutrient verification."""

from __future__ import annotations

import math

from core import NUTRIENTS, Engine


def generate(engine: Engine, recipe_id: str, targets: dict, tolerance: float = 0.05) -> dict:
    if not isinstance(recipe_id, str):
        raise ValueError("请选择基础食谱")
    source = next((r for r in engine.recipes if r["id"] == recipe_id), None)
    if source is None:
        raise ValueError("基础食谱不存在")
    if not isinstance(targets, dict) or not targets:
        raise ValueError("至少填写一项营养目标")
    clean = {}
    for key, value in targets.items():
        if key not in NUTRIENTS or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"营养目标 {key} 必须是正数")
        clean[key] = float(value)

    parts = source["ingredients"]
    original = [float(p["grams"]) for p in parts]
    vectors = [[engine.ingredients[p["id"]]["per_100g"][key] / (100 * source["servings"]) for key in NUTRIENTS] for p in parts]
    bounds = [(max(1.0, x * 0.2), min(600.0, max(50.0, x * 3))) for x in original]
    # Small additions such as oil remain bounded by the original quantity.
    if any(low > high for low, high in bounds):
        raise ValueError("基础食谱克数超出优化范围")

    def values(grams):
        return {key: sum(vectors[i][j] * grams[i] for i in range(len(parts))) for j, key in enumerate(NUTRIENTS)}

    def deviations(nutrients):
        result = {}
        for key, target in clean.items():
            value = nutrients[key]
            if key == "fiber_g":
                result[key] = max(0.0, (target - value) / target)
            elif key == "sodium_mg":
                result[key] = max(0.0, (value - target) / target)
            else:
                result[key] = abs(value - target) / target
        return result

    def objective(grams):
        d = deviations(values(grams))
        # A small regularizer favors a practical quantity adjustment if several solutions fit.
        return sum(x * x for x in d.values()) / len(d) + 0.001 * sum(((g - o) / max(o, 1)) ** 2 for g, o in zip(grams, original)) / len(grams)

    seeds = [original[:]]
    if "energy_kcal" in clean:
        current = values(original)["energy_kcal"]
        if current > 0:
            factor = clean["energy_kcal"] / current
            seeds.append([min(hi, max(lo, x * factor)) for x, (lo, hi) in zip(original, bounds)])
    best = min(seeds, key=objective)
    best_score = objective(best)
    steps = [0.5, 0.2, 0.1, 0.05, 0.02, 0.01]
    iterations = 0
    for step in steps:
        for _ in range(100):
            iterations += 1
            next_grams, next_score = best, best_score
            for i, amount in enumerate(best):
                for direction in (-1, 1):
                    candidate = best[:]
                    candidate[i] = min(bounds[i][1], max(bounds[i][0], amount + direction * max(original[i] * step, 0.25)))
                    score = objective(candidate)
                    if score + 1e-12 < next_score:
                        next_grams, next_score = candidate, score
            if next_grams is best:
                break
            best, best_score = next_grams, next_score
    # Displayed gram values are the values actually rechecked below.
    result_recipe = {"servings": source["servings"], "ingredients": [{"id": p["id"], "grams": round(g, 1)} for p, g in zip(parts, best)]}
    actual = engine.nutrition(result_recipe)
    d = deviations(actual)
    return {
        "source_id": recipe_id, "source_name": source["name"], "servings": source["servings"],
        "ingredients": [{"id": p["id"], "name": engine.ingredients[p["id"]]["name"], "grams": p["grams"]} for p in result_recipe["ingredients"]],
        "nutrition": actual, "targets": clean, "deviations": {key: round(value, 4) for key, value in d.items()},
        "max_deviation": round(max(d.values()), 4), "passed": all(value <= tolerance for value in d.values()),
        "tolerance": tolerance, "iterations": iterations,
        "method": "食谱模板克数优化；纤维按下限、钠按上限验算；其他指标按 ±5% 验算",
    }
