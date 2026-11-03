import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import foodcom_service


class FoodcomGraphTests(unittest.TestCase):
    def test_graph_uses_observed_recipe_ingredient_edges_without_confidence(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder) / "foodcom.sqlite"
            db = sqlite3.connect(db_path)
            db.executescript("""
                CREATE TABLE recipes(id INTEGER PRIMARY KEY,name TEXT,minutes INTEGER,ingredient_count INTEGER);
                CREATE TABLE ingredients(id INTEGER PRIMARY KEY,name TEXT,frequency INTEGER);
                CREATE TABLE recipe_ingredients(recipe_id INTEGER,ingredient_id INTEGER,PRIMARY KEY(recipe_id,ingredient_id));
                INSERT INTO recipes VALUES(1,'tofu bowl',20,2),(2,'rice bowl',15,1);
                INSERT INTO ingredients VALUES(1,'tofu',1),(2,'rice',2);
                INSERT INTO recipe_ingredients VALUES(1,1),(1,2),(2,2);
            """)
            db.commit()
            db.close()
            with patch.object(foodcom_service, "DB_PATH", db_path):
                stats = foodcom_service.graph_statistics()
                self.assertEqual(stats["node_count"], 4)
                self.assertEqual(stats["edge_count"], 3)
                self.assertEqual(sum(item["count"] for item in stats["frequency_bins"]), 2)
                graph = foodcom_service.graph_explore("tofu", depth=2)
                self.assertEqual(graph["focus"]["label"], "tofu")
                self.assertEqual(len(graph["edges"]), 2)
                self.assertTrue(all(edge["confidence"] is None for edge in graph["edges"]))
                self.assertEqual({edge["relation"] for edge in graph["edges"]}, {"包含食材"})
                page = foodcom_service.graph_triples("tofu", 1)
                self.assertEqual(page["total"], 2)
                self.assertEqual(page["items"][0]["recipe_name"], "tofu bowl")


if __name__ == "__main__":
    unittest.main()
