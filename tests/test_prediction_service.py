import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kg_service
import prediction_service


class PredictionTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(kg_service, "DB_PATH", Path(self.temp.name) / "kg.sqlite")
        self.patch.start()
        self.dataset = kg_service.import_dataset({
            "filename": "research.csv", "dataset_name": "研究图谱",
            "content": (
                "head,relation,tail,confidence,evidence,source,head_type,tail_type\n"
                "菠菜,属于,绿叶蔬菜,0.95,分类记录,资料A,食材,类别\n"
                "羽衣甘蓝,属于,绿叶蔬菜,0.9,分类记录,资料A,食材,类别\n"
                "羽衣甘蓝,搭配,坚果,0.8,真实食谱1,Food.com,食材,食材\n"
                "菠菜,搭配,鸡蛋,0.7,真实食谱2,Food.com,食材,食材\n"
                "羽衣甘蓝,搭配,鸡蛋,0.6,真实食谱3,Food.com,食材,食材\n"
            ),
        })["dataset"]["id"]

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_task_candidates_keep_evidence_and_exclude_observed(self):
        result = prediction_service.create_task({
            "name": "菠菜搭配探索", "dataset_id": self.dataset,
            "target_name": "菠菜", "target_type": "食材", "relation": "搭配",
            "max_candidates": 10,
        })
        self.assertEqual(result["existing_count"], 1)
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["tail"], "坚果")
        self.assertEqual(candidate["status"], "待核查")
        self.assertEqual(candidate["references"][0]["evidence"], "真实食谱1")
        self.assertEqual(candidate["references"][0]["shared_neighbors"][0]["entity"], "绿叶蔬菜")
        self.assertEqual(prediction_service.get_task(result["id"])["candidates"][0]["tail"], "坚果")
        self.assertEqual(len(prediction_service.list_tasks(self.dataset)), 1)
        self.assertEqual(kg_service.summary(self.dataset)["edge_count"], 5)

    def test_entity_search_and_missing_evidence_case(self):
        found = prediction_service.entities(self.dataset, "菠菜", "搭配")
        self.assertEqual(found[0]["name"], "菠菜")
        result = prediction_service.create_task({
            "name": "排除已有关系", "dataset_id": self.dataset,
            "target_name": "菠菜", "target_type": "食材", "relation": "属于",
        })
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["existing_count"], 1)
        with self.assertRaisesRegex(ValueError, "目标实体"):
            prediction_service.create_task({
                "name": "无效", "dataset_id": self.dataset,
                "target_name": "不存在", "target_type": "食材", "relation": "搭配",
            })


if __name__ == "__main__":
    unittest.main()
