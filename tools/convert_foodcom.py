"""Index user-provided Food.com recipe ingredient lists without inventing grams."""

from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import sqlite3
import sys
import zipfile
from collections import Counter
from pathlib import Path


def convert(source: Path, destination: Path) -> dict:
    sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    db = sqlite3.connect(destination)
    try:
        db.executescript("""
            CREATE TABLE recipes(id INTEGER PRIMARY KEY, name TEXT NOT NULL, minutes INTEGER, ingredient_count INTEGER NOT NULL);
            CREATE TABLE ingredients(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, frequency INTEGER NOT NULL);
            CREATE TABLE recipe_ingredients(recipe_id INTEGER NOT NULL, ingredient_id INTEGER NOT NULL, PRIMARY KEY(recipe_id, ingredient_id));
            CREATE INDEX idx_recipe_ingredients_ingredient ON recipe_ingredients(ingredient_id, recipe_id);
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        count = 0
        skipped = 0
        frequencies = Counter()
        ids = {}
        with zipfile.ZipFile(source) as archive:
            if "RAW_recipes.csv" not in archive.namelist():
                raise ValueError("压缩包缺少 RAW_recipes.csv")
            reader = csv.DictReader(io.TextIOWrapper(archive.open("RAW_recipes.csv"), encoding="utf-8-sig", newline=""))
            for row in reader:
                try:
                    recipe_id = int(row["id"])
                    names = ast.literal_eval(row["ingredients"])
                    if not isinstance(names, list) or not names or not all(isinstance(name, str) for name in names):
                        raise ValueError("invalid ingredient list")
                    minutes = int(row["minutes"])
                    names = list(dict.fromkeys(name.strip().lower() for name in names if name.strip()))
                    if not names:
                        raise ValueError("empty ingredients")
                except (ValueError, SyntaxError, TypeError, KeyError):
                    skipped += 1
                    continue
                db.execute("INSERT INTO recipes VALUES(?,?,?,?)", (recipe_id, row["name"].strip(), minutes, len(names)))
                for name in names:
                    if name not in ids:
                        ids[name] = len(ids) + 1
                    ingredient_id = ids[name]
                    db.execute("INSERT INTO recipe_ingredients VALUES(?,?)", (recipe_id, ingredient_id))
                    frequencies[ingredient_id] += 1
                count += 1
                if count % 10000 == 0:
                    db.commit()
                    print(f"Indexed {count} recipes", flush=True)
        db.executemany("INSERT INTO ingredients VALUES(?,?,?)", ((ingredient_id, name, frequencies[ingredient_id]) for name, ingredient_id in ids.items()))
        sorted_frequencies = sorted(frequencies.values())
        threshold = sorted_frequencies[max(0, (len(sorted_frequencies) + 3) // 4 - 1)] if sorted_frequencies else 0
        meta = {"source": "Food.com Recipes and Interactions / RAW_recipes.csv", "source_file": source.name,
                "sha256": sha256, "recipe_count": count, "ingredient_count": len(ids), "skipped_rows": skipped,
                "tail_threshold": threshold, "tail_count": sum(value <= threshold for value in frequencies.values()),
                "note": "原始食材清单没有逐项克数；此库仅用于长尾频次、共现和食谱检索，不用于营养验算。"}
        db.executemany("INSERT INTO metadata VALUES(?,?)", ((key, json.dumps(value, ensure_ascii=False)) for key, value in meta.items()))
        db.commit()
        return meta
    finally:
        db.close()


if __name__ == "__main__":
    result = convert(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, ensure_ascii=False, indent=2))
