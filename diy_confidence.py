"""Evidence support and nutrient checks for a user-supplied DIY recipe."""
from __future__ import annotations

import math
from itertools import combinations

import foodcom_service
from core import NUTRIENTS

ALIASES = {
    "chicken": "chicken breasts", "tofu": "tofu", "rice": "rice",
    "quinoa": "quinoa", "broccoli": "broccoli", "spinach": "spinach",
    "kale": "kale", "tomato": "tomatoes", "salmon": "salmon",
    "oil": "olive oil", "chickpea": "chickpeas", "mushroom": "mushrooms",
}


def _validate(engine, payload):
    parts = payload.get("parts")
    if not isinstance(parts, list) or not 1 <= len(parts) <= 20:
        raise ValueError("DIY 食谱须包含 1–20 种食材")
    try:
        servings = int(payload.get("servings"))
    except (TypeError, ValueError) as exc:
        raise ValueError("份数须为 1–100 的正整数") from exc
    if not 1 <= servings <= 100 or servings != payload.get("servings"):
        raise ValueError("份数须为 1–100 的正整数")
    clean_parts = []
    seen = set()
    for index, part in enumerate(parts, 1):
        if not isinstance(part, dict):
            raise ValueError(f"第 {index} 项食材格式错误")
        ingredient_id = part.get("id")
        if not isinstance(ingredient_id, str) or ingredient_id not in engine.ingredients:
            raise ValueError(f"第 {index} 项食材不存在")
        if ingredient_id in seen:
            raise ValueError("DIY 食谱中的食材不能重复")
        seen.add(ingredient_id)
        if isinstance(part.get("grams"), bool):
            raise ValueError(f"第 {index} 项克数无效")
        try:
            grams = float(part.get("grams"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {index} 项克数无效") from exc
        if not math.isfinite(grams) or not 0 < grams <= 5000:
            raise ValueError(f"第 {index} 项克数须在 0–5000 g 之间")
        clean_parts.append({"id": ingredient_id, "grams": grams})
    targets = payload.get("targets")
    if not isinstance(targets, dict):
        raise ValueError("请填写六项营养目标")
    clean_targets = {}
    for key in NUTRIENTS:
        value = targets.get(key)
        if isinstance(value, bool):
            raise ValueError(f"{key} 目标无效")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} 目标无效") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{key} 目标须大于 0")
        clean_targets[key] = number
    return clean_parts, servings, clean_targets


def _foodcom_evidence(engine, ids):
    db = foodcom_service._connect()
    if db is None:
        return {
            "available": False, "mapped": [], "unmapped": [engine.ingredients[i]["name"] for i in ids],
            "related_recipes": [], "pairs": [], "pair_total": len(ids) * (len(ids) - 1) // 2,
            "pair_supported": 0, "support_score": None,
            "note": "Food.com 食谱索引尚不可用，无法计算真实食谱证据支持分。",
        }
    try:
        mapped = []
        unmapped = []
        for ingredient_id in ids:
            ingredient = engine.ingredients[ingredient_id]
            lookup = ALIASES.get(ingredient_id, ingredient["name"].strip().lower())
            row = db.execute(
                "SELECT id,name,frequency FROM ingredients WHERE lower(name)=? LIMIT 1", (lookup,)
            ).fetchone()
            if row:
                mapped.append({
                    "local_id": ingredient_id, "local_name": ingredient["name"],
                    "foodcom_id": row["id"], "foodcom_name": row["name"],
                    "frequency": row["frequency"],
                })
            else:
                unmapped.append(ingredient["name"])
        index_by_local = {item["local_id"]: item for item in mapped}
        food_ids = [item["foodcom_id"] for item in mapped]
        related = []
        if food_ids:
            marks = ",".join("?" for _ in food_ids)
            rows = db.execute(
                f"""SELECT r.id,r.name,r.ingredient_count,COUNT(DISTINCT ri.ingredient_id) AS overlap
                    FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id
                    WHERE ri.ingredient_id IN ({marks})
                    GROUP BY r.id
                    ORDER BY (1.0 * COUNT(DISTINCT ri.ingredient_id) /
                              (? + r.ingredient_count - COUNT(DISTINCT ri.ingredient_id))) DESC,
                             overlap DESC,r.id LIMIT 5""",
                (*food_ids, len(ids)),
            )
            for row in rows:
                overlap = row["overlap"]
                related.append({
                    "id": row["id"], "name": row["name"], "ingredient_count": row["ingredient_count"],
                    "overlap": overlap, "similarity": round(overlap / (len(ids) + row["ingredient_count"] - overlap), 4),
                })
        pair_total = len(ids) * (len(ids) - 1) // 2
        pair_supported = 0
        pairs = []
        for first_id, second_id in combinations(ids, 2):
            first = index_by_local.get(first_id)
            second = index_by_local.get(second_id)
            count = 0
            examples = []
            if first and second:
                a, b = first["foodcom_id"], second["foodcom_id"]
                count = db.execute(
                    """SELECT COUNT(*) FROM recipe_ingredients x
                       JOIN recipe_ingredients y ON y.recipe_id=x.recipe_id
                       WHERE x.ingredient_id=? AND y.ingredient_id=?""",
                    (a, b),
                ).fetchone()[0]
                if count:
                    examples = [dict(row) for row in db.execute(
                        """SELECT r.id,r.name FROM recipe_ingredients x
                           JOIN recipe_ingredients y ON y.recipe_id=x.recipe_id
                           JOIN recipes r ON r.id=x.recipe_id
                           WHERE x.ingredient_id=? AND y.ingredient_id=? ORDER BY r.id LIMIT 3""",
                        (a, b),
                    )]
            if count:
                pair_supported += 1
            pairs.append({
                "first": engine.ingredients[first_id]["name"],
                "second": engine.ingredients[second_id]["name"],
                "count": count,
                "mapped": bool(first and second),
                "examples": examples,
            })
        coverage = pair_supported / pair_total if pair_total else 0
        strength = (
            sum(min(1.0, math.log1p(pair["count"]) / math.log1p(5)) for pair in pairs) / pair_total
            if pair_total else 0
        )
        best_similarity = related[0]["similarity"] if related else 0
        support_score = round(
            100 * (0.45 * coverage + 0.35 * strength + 0.20 * best_similarity), 1
        ) if pair_total else None
        note = (
            "已有真实食谱搭配证据。" if pair_supported else
            "当前食材组合没有查到完整的真实共现证据。"
        )
        if unmapped:
            note += f" {len(unmapped)} 种食材未匹配到 Food.com 精确名称，相关搭配按未验证处理。"
        if pair_total == 0:
            note = "至少选择两种食材，才能评估搭配证据。"
        return {
            "available": True, "source": "Food.com 真实食谱索引",
            "mapped": mapped, "unmapped": unmapped,
            "related_recipes": related, "pairs": pairs,
            "pair_total": pair_total, "pair_supported": pair_supported,
            "pair_strength": round(strength, 4), "support_score": support_score, "note": note,
        }
    finally:
        db.close()


def assess(engine, payload):
    if not isinstance(payload, dict):
        raise ValueError("请求内容格式错误")
    parts, servings, targets = _validate(engine, payload)
    ids = [part["id"] for part in parts]
    nutrition = engine.nutrition({"servings": servings, "ingredients": parts})
    checks = []
    for key in NUTRIENTS:
        actual, target = nutrition[key], targets[key]
        if key == "sodium_mg":
            deviation = max(0, actual - target) / target
        elif key == "fiber_g":
            deviation = max(0, target - actual) / target
        else:
            deviation = abs(actual - target) / target
        checks.append({
            "key": key, "actual": actual, "target": target,
            "deviation": round(deviation, 4), "passed": deviation <= 0.05,
        })
    nutrition_score = round(100 * max(0, 1 - sum(item["deviation"] for item in checks) / len(checks)), 1)
    evidence = _foodcom_evidence(engine, ids)
    return {
        "dataset_title": engine.summary()["dataset_title"],
        "is_demo_nutrition": engine.summary()["is_demo"],
        "parts": [
            {"id": part["id"], "name": engine.ingredients[part["id"]]["name"], "grams": part["grams"]}
            for part in parts
        ],
        "servings": servings, "nutrition": nutrition,
        "nutrition_score": nutrition_score, "checks": checks,
        "nutrition_passed": all(item["passed"] for item in checks),
        "evidence": evidence,
    }
