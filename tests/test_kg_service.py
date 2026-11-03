import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kg_service


class KnowledgeDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(kg_service, "DB_PATH", Path(self.temp.name) / "kg.sqlite")
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_csv_upload_builds_real_summary_and_search(self):
        csv_text = (
            "head,relation,tail,confidence,evidence,source,head_type,tail_type\n"
            "菠菜,富含,铁,0.8,来源记录A,研究数据,食材,营养素\n"
            "菠菜,搭配,鸡蛋,0.6,来源记录B,研究数据,食材,食材\n"
        )
        result = kg_service.import_dataset({
            "filename": "sample.csv", "dataset_name": "测试图谱",
            "source": "上传批次", "content": csv_text
        })
        self.assertTrue(result["available"])
        self.assertEqual(result["edge_count"], 2)
        self.assertEqual(result["node_count"], 3)
        self.assertEqual(result["entity_type_count"], 2)
        self.assertEqual(result["relation_type_count"], 2)
        self.assertEqual(result["average_confidence"], 0.7)
        self.assertEqual(sum(item["count"] for item in result["confidence_bins"]), 2)
        page = kg_service.triples(result["dataset"]["id"], "鸡蛋")
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["evidence"], "来源记录B")
        self.assertEqual(page["items"][0]["source"], "研究数据")

    def test_explore_uses_selected_dataset_and_preserves_evidence(self):
        first = kg_service.import_dataset({
            "filename": "graph.csv",
            "content": "head,relation,tail,confidence,evidence,head_type,tail_type\n"
                       "菠菜,富含,铁,0.8,营养证据,食材,营养素\n"
                       "菠菜,搭配,鸡蛋,0.6,搭配证据,食材,食材\n"
                       "鸡蛋,包含,蛋白质,0.9,成分证据,食材,营养素\n",
        })
        second = kg_service.import_dataset({
            "filename": "other.json",
            "content": '[{"head":"A","relation":"R","tail":"B","confidence":1}]',
        })
        graph = kg_service.explore(first["dataset"]["id"], "菠菜", relation="富含")
        self.assertEqual(graph["focus"]["label"], "菠菜")
        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(graph["edges"][0]["evidence"], "营养证据")
        self.assertEqual({n["label"] for n in graph["nodes"]}, {"菠菜", "铁"})
        expanded = kg_service.explore(first["dataset"]["id"], "菠菜", depth=2)
        self.assertEqual(len(expanded["edges"]), 3)
        filtered = kg_service.explore(first["dataset"]["id"], relation="包含")
        self.assertEqual(len(filtered["edges"]), 1)
        self.assertEqual(filtered["edges"][0]["relation"], "包含")
        self.assertEqual(len(kg_service.explore(second["dataset"]["id"])["edges"]), 1)
        self.assertIsNone(kg_service.explore(first["dataset"]["id"], "不存在")["focus"])

    def test_invalid_row_does_not_create_dataset(self):
        with self.assertRaisesRegex(ValueError, "0–1"):
            kg_service.import_dataset({
                "filename": "bad.json", "content": '[{"head":"A","relation":"B","tail":"C","confidence":1.5}]'
            })
        self.assertFalse(kg_service.summary()["available"])

    def test_delete_removes_only_selected_dataset_and_its_tasks(self):
        first = kg_service.import_dataset({
            "filename": "one.json", "content": '[{"head":"A","relation":"R","tail":"B","confidence":0.3}]'
        })
        second = kg_service.import_dataset({
            "filename": "two.json", "content": '[{"head":"X","relation":"S","tail":"Y","confidence":1}]'
        })
        first_id, second_id = first["dataset"]["id"], second["dataset"]["id"]
        with kg_service.connect() as db:
            db.execute("""CREATE TABLE prediction_tasks(
                id INTEGER PRIMARY KEY, dataset_id INTEGER NOT NULL REFERENCES datasets(id),
                name TEXT NOT NULL)""")
            db.execute("INSERT INTO prediction_tasks(dataset_id,name) VALUES(?,?)", (first_id, "关联发现"))
            db.execute("INSERT INTO prediction_tasks(dataset_id,name) VALUES(?,?)", (second_id, "其他任务"))
        result = kg_service.delete_dataset(first_id)
        self.assertEqual([item["id"] for item in result["datasets"]], [second_id])
        self.assertEqual(kg_service.triples(second_id)["total"], 1)
        with kg_service.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM prediction_tasks").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM triples WHERE dataset_id=?", (first_id,)).fetchone()[0], 0)
        with self.assertRaisesRegex(ValueError, "Food.com"):
            kg_service.delete_dataset("foodcom")
        with self.assertRaisesRegex(ValueError, "不存在"):
            kg_service.delete_dataset(first_id)

    def test_json_datasets_are_isolated(self):
        first = kg_service.import_dataset({
            "filename": "one.json", "content": '[{"head":"A","relation":"R","tail":"B","confidence":0.3}]'
        })
        second = kg_service.import_dataset({
            "filename": "two.json", "content": '{"triples":[{"head":"X","relation":"S","tail":"Y","confidence":1}]}'
        })
        self.assertEqual(len(second["datasets"]), 2)
        self.assertEqual(kg_service.triples(first["dataset"]["id"])["items"][0]["head"], "A")
        self.assertEqual(kg_service.triples(second["dataset"]["id"])["items"][0]["head"], "X")


if __name__ == "__main__":
    unittest.main()
