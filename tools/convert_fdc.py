"""Convert FoodData Central Foundation Foods into a provenance-aware catalog.

Incomplete nutrient profiles are excluded, never filled with invented zeroes.
"""

import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


NUTRIENT_IDS = {"protein_g": "1003", "fat_g": "1004", "carbs_g": "1005", "fiber_g": "1079", "sodium_mg": "1093"}
ENERGY_PRIORITY = ("2048", "1008", "2047")


def convert(source: Path) -> dict:
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    with zipfile.ZipFile(source) as archive:
        prefix = next((name.removesuffix("food.csv") for name in archive.namelist() if name.endswith("/food.csv")), None)
        if prefix is None or not all(prefix + name in archive.namelist() for name in ("food_nutrient.csv", "nutrient.csv")):
            raise ValueError("压缩包缺少 FoodData Central 的核心 CSV 表")

        def rows(name):
            return csv.DictReader(io.TextIOWrapper(archive.open(prefix + name), encoding="utf-8-sig"))

        foods = {row["fdc_id"]: row for row in rows("food.csv") if row["data_type"] == "foundation_food"}
        values = defaultdict(dict)
        wanted = set(NUTRIENT_IDS.values()) | set(ENERGY_PRIORITY)
        for row in rows("food_nutrient.csv"):
            if row["fdc_id"] not in foods or row["nutrient_id"] not in wanted:
                continue
            try:
                amount = float(row["amount"])
            except (TypeError, ValueError):
                continue
            if math.isfinite(amount) and amount >= 0:
                values[row["fdc_id"]][row["nutrient_id"]] = amount
        records = []
        for fdc_id, food in foods.items():
            profile = values[fdc_id]
            if not all(code in profile for code in NUTRIENT_IDS.values()):
                continue
            energy_id = next((code for code in ENERGY_PRIORITY if code in profile), None)
            if energy_id is None:
                continue
            nutrients = {field: profile[code] for field, code in NUTRIENT_IDS.items()}
            nutrients["energy_kcal"] = profile[energy_id]
            records.append({"fdc_id": fdc_id, "name": food["description"], "publication_date": food["publication_date"], "per_100g": nutrients, "energy_nutrient_id": energy_id})
    return {"source": "USDA FoodData Central / Foundation Foods", "source_file": source.name, "sha256": sha,
            "selection": "仅保留六项营养齐全的 Foundation Foods 主食物记录；不填补缺失值。能量优先 2048，其次 1008、2047。",
            "foundation_count": len(foods), "complete_count": len(records), "records": sorted(records, key=lambda r: int(r["fdc_id"]))}


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    catalog = convert(src)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {catalog['complete_count']} of {catalog['foundation_count']} Foundation Foods to {dest}")
    if len(sys.argv) > 3:
        csv_dest = Path(sys.argv[3])
        csv_dest.parent.mkdir(parents=True, exist_ok=True)
        with csv_dest.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(("id", "name", "category", "energy_kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", "sodium_mg"))
            for record in catalog["records"]:
                n = record["per_100g"]
                writer.writerow((f"fdc_{record['fdc_id']}", record["name"], "USDA Foundation Foods", n["energy_kcal"], n["protein_g"], n["fat_g"], n["carbs_g"], n["fiber_g"], n["sodium_mg"]))
        print(f"Wrote importable ingredient CSV to {csv_dest}")
