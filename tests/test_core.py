import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Engine, validated_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))
        self.engine = Engine(self.data)

    def test_nutrition_uses_grams_and_servings(self):
        one = self.engine.nutrition(self.data["recipes"][0])
        two_servings = dict(self.data["recipes"][0], servings=2)
        two = self.engine.nutrition(two_servings)
        self.assertAlmostEqual(one["protein_g"] / 2, two["protein_g"], places=2)

    def test_excluded_ingredient_is_hard_constraint(self):
        result = self.engine.recommend({}, [], ["chicken"])
        self.assertTrue(result)
        self.assertTrue(all("鸡胸肉" not in [x["name"] for x in r["ingredients"]] for r in result))

    def test_inferred_edges_are_labeled_and_do_not_change_nutrition(self):
        before = self.engine.nutrition(self.data["recipes"][0])
        tail = next(x for x in self.engine.ingredients if self.engine.is_tail(x))
        edges = self.engine.compensated_neighbors(tail)
        self.assertTrue(all(x["source"] in ("observed", "inferred") for x in edges))
        self.assertEqual(before, self.engine.nutrition(self.data["recipes"][0]))

    def test_rejects_unknown_ingredient(self):
        self.data["recipes"][0]["ingredients"][0]["id"] = "unknown"
        with self.assertRaises(ValueError):
            validated_data(self.data)


if __name__ == "__main__":
    unittest.main()
