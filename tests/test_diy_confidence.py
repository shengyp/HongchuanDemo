import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import diy_confidence
import foodcom_service
from core import Engine, NUTRIENTS


class DiyConfidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "foodcom.sqlite"
        db = sqlite3.connect(self.db_path)
        db.executescript("""
            CREATE TABLE ingredients(id INTEGER PRIMARY KEY,name TEXT,frequency INTEGER);
            CREATE TABLE recipes(id INTEGER PRIMARY KEY,name TEXT,minutes INTEGER,ingredient_count INTEGER);
            CREATE TABLE recipe_ingredients(recipe_id INTEGER,ingredient_id INTEGER,PRIMARY KEY(recipe_id,ingredient_id));
            INSERT INTO ingredients VALUES(1,'tofu',2),(2,'spinach',1),(3,'rice',2);
            INSERT INTO recipes VALUES(10,'Tofu spinach rice',25,3),(11,'Tofu rice',15,2);
            INSERT INTO recipe_ingredients VALUES(10,1),(10,2),(10,3),(11,1),(11,3);
        """)
        db.commit()
        db.close()
        self.patch = patch.object(foodcom_service, "DB_PATH", self.db_path)
        self.patch.start()
        demo = json.loads((Path(__file__).resolve().parents[1] / "data" / "demo.json").read_text(encoding="utf-8"))
        self.engine = Engine(demo)

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_real_recipe_support_and_nutrition_are_separate(self):
        parts = [{"id": "tofu", "grams": 180}, {"id": "spinach", "grams": 130}, {"id": "rice", "grams": 180}]
        nutrition = self.engine.nutrition({"servings": 1, "ingredients": parts})
        result = diy_confidence.assess(self.engine, {
            "parts": parts, "servings": 1, "targets": nutrition,
        })
        self.assertEqual(result["nutrition_score"], 100)
        self.assertEqual(result["evidence"]["pair_total"], 3)
        self.assertEqual(result["evidence"]["pair_supported"], 3)
        self.assertEqual(result["evidence"]["related_recipes"][0]["id"], 10)
        self.assertGreater(result["evidence"]["support_score"], 0)
        self.assertTrue(result["is_demo_nutrition"])
        self.assertEqual(result["evidence"]["pairs"][0]["examples"][0]["name"], "Tofu spinach rice")

    def test_unmapped_pair_is_not_claimed_as_observed(self):
        result = diy_confidence.assess(self.engine, {
            "parts": [{"id": "chicken", "grams": 100}, {"id": "spinach", "grams": 100}],
            "servings": 1, "targets": {key: 1 for key in NUTRIENTS},
        })
        self.assertEqual(result["evidence"]["pair_supported"], 0)
        self.assertFalse(result["evidence"]["pairs"][0]["mapped"])
        self.assertIn("鸡胸肉", result["evidence"]["unmapped"])

    def test_missing_recipe_index_does_not_invent_evidence(self):
        with patch.object(foodcom_service, "DB_PATH", Path(self.temp.name) / "missing.sqlite"):
            result = diy_confidence.assess(self.engine, {
                "parts": [{"id": "tofu", "grams": 100}, {"id": "spinach", "grams": 100}],
                "servings": 1, "targets": {key: 1 for key in NUTRIENTS},
            })
        self.assertFalse(result["evidence"]["available"])
        self.assertIsNone(result["evidence"]["support_score"])
        self.assertEqual(result["evidence"]["related_recipes"], [])

    def test_invalid_recipe_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不能重复"):
            diy_confidence.assess(self.engine, {
                "parts": [{"id": "tofu", "grams": 100}, {"id": "tofu", "grams": 100}],
                "servings": 1, "targets": {key: 1 for key in NUTRIENTS},
            })


if __name__ == "__main__":
    unittest.main()
