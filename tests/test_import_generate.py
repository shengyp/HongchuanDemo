import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import Engine  # noqa: E402
from csv_import import parse_csv_dataset  # noqa: E402
from generator import generate  # noqa: E402


class ImportGenerateTest(unittest.TestCase):
    def test_csv_template_roundtrip(self):
        ingredients = (ROOT / "templates" / "ingredients.csv").read_text(encoding="utf-8")
        recipes = (ROOT / "templates" / "recipe_parts.csv").read_text(encoding="utf-8")
        engine = Engine(parse_csv_dataset(ingredients, recipes, "template"))
        self.assertEqual(engine.summary()["ingredient_count"], 2)
        self.assertEqual(engine.summary()["recipe_count"], 1)

    def test_missing_nutrient_rejected(self):
        ingredients = "id,name,energy_kcal\na,食材,10\n"
        recipes = (ROOT / "templates" / "recipe_parts.csv").read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "缺少列"):
            parse_csv_dataset(ingredients, recipes)

    def test_generator_verifies_displayed_grams(self):
        engine = Engine(json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8")))
        source = engine.recipes[0]
        result = generate(engine, source["id"], engine.nutrition(source))
        self.assertTrue(result["passed"])
        self.assertEqual(result["nutrition"], engine.nutrition({"servings": result["servings"], "ingredients": result["ingredients"]}))

    def test_generator_reports_infeasible_goal(self):
        engine = Engine(json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8")))
        result = generate(engine, "r1", {"fiber_g": 1000})
        self.assertFalse(result["passed"])
        self.assertGreater(result["max_deviation"], 0.05)


if __name__ == "__main__":
    unittest.main()
