"""Import explicit nutrient-density and recipe-part CSV tables."""

from __future__ import annotations

import csv
import io

from core import NUTRIENTS, validated_data


def _rows(content: str, required: set[str], label: str) -> list[dict]:
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"请上传 {label} CSV")
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff"), newline=""))
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError(f"{label} 缺少列：{', '.join(sorted(required - set(reader.fieldnames or [])))}")
    rows = list(reader)
    if not rows or any(None in row for row in rows):
        raise ValueError(f"{label} 为空或列数不一致")
    return rows


def parse_csv_dataset(ingredient_csv: str, recipe_csv: str, source: str = "用户提供的 CSV") -> dict:
    if not isinstance(source, str):
        raise ValueError("数据来源必须是文字")
    ingredient_rows = _rows(ingredient_csv, {"id", "name", *NUTRIENTS}, "食材表")
    recipe_rows = _rows(recipe_csv, {"recipe_id", "recipe_name", "servings", "ingredient_id", "grams"}, "食谱组成表")
    ingredients = []
    for line, row in enumerate(ingredient_rows, 2):
        try:
            nutrient = {key: float(row[key]) for key in NUTRIENTS}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"食材表第 {line} 行营养值无效") from exc
        ingredients.append({"id": row["id"].strip(), "name": row["name"].strip(), "category": (row.get("category") or "").strip(), "per_100g": nutrient})
    recipes = {}
    for line, row in enumerate(recipe_rows, 2):
        key = row["recipe_id"].strip()
        try:
            servings = int(row["servings"])
            grams = float(row["grams"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"食谱组成表第 {line} 行份数或克数无效") from exc
        name = row["recipe_name"].strip()
        item = recipes.setdefault(key, {"id": key, "name": name, "servings": servings, "ingredients": []})
        if item["name"] != name or item["servings"] != servings:
            raise ValueError(f"食谱 {key} 的名称或份数不一致")
        item["ingredients"].append({"id": row["ingredient_id"].strip(), "grams": grams})
    data = {"metadata": {"title": "导入的营养食谱数据", "source": source[:300], "notice": "营养计算取决于上传数据的准确性。"}, "ingredients": ingredients, "recipes": list(recipes.values())}
    return validated_data(data)
