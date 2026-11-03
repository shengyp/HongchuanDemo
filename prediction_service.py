"""Evidence-backed, deterministic link candidate tasks for uploaded knowledge graphs."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import kg_service

METHOD = "共享邻居相似度与已观察关系置信度排序"


def _tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS prediction_tasks (
            id INTEGER PRIMARY KEY,
            dataset_id INTEGER NOT NULL REFERENCES datasets(id),
            name TEXT NOT NULL,
            target_name TEXT NOT NULL,
            target_type TEXT NOT NULL,
            relation TEXT NOT NULL,
            method TEXT NOT NULL,
            created_at TEXT NOT NULL,
            candidate_count INTEGER NOT NULL,
            result_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_prediction_tasks_dataset ON prediction_tasks(dataset_id, id);
    """)


def entities(dataset_id=None, q="", relation="", limit=30):
    if not isinstance(q, str) or len(q) > 200:
        raise ValueError("检索词过长")
    if not isinstance(relation, str) or len(relation) > 200:
        raise ValueError("关系类型无效")
    with kg_service.connect() as db:
        _, selected = kg_service._selected(db, dataset_id)
        if selected is None:
            return []
        sql = "SELECT head AS name, head_type AS type, COUNT(*) AS degree FROM triples WHERE dataset_id=?"
        params = [selected]
        if relation.strip():
            sql += " AND relation=?"
            params.append(relation.strip())
        if q.strip():
            sql += " AND head LIKE ? ESCAPE '\\'"
            params.append("%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        sql += " GROUP BY head,head_type ORDER BY degree DESC,name LIMIT ?"
        params.append(limit)
        return [dict(row) for row in db.execute(sql, params)]


def _predict(db, dataset_id, target_name, target_type, relation, max_candidates):
    existing = {
        (row["tail"], row["tail_type"])
        for row in db.execute(
            "SELECT tail,tail_type FROM triples WHERE dataset_id=? AND head=? AND head_type=? AND relation=?",
            (dataset_id, target_name, target_type, relation),
        )
    }
    target_features = {
        (row["relation"], row["tail"], row["tail_type"])
        for row in db.execute(
            "SELECT relation,tail,tail_type FROM triples WHERE dataset_id=? AND head=? AND head_type=? AND relation<>?",
            (dataset_id, target_name, target_type, relation),
        )
    }
    if not target_features:
        return [], "目标实体缺少其他关系，无法找到有共享邻居的相似实体。"
    reference_rows = [dict(row) for row in db.execute(
        """SELECT id,head,head_type,relation,tail,tail_type,confidence,evidence,source
           FROM triples WHERE dataset_id=? AND relation=? AND head_type=? AND head<>?
           ORDER BY confidence DESC,id DESC LIMIT 4000""",
        (dataset_id, relation, target_type, target_name),
    )]
    similar_heads = list(dict.fromkeys(row["head"] for row in reference_rows))[:300]
    if not similar_heads:
        return [], "没有其他同类型实体的该类真实关系可供参考。"
    placeholders = ",".join("?" for _ in similar_heads)
    related_features: dict[str, set[tuple[str, str, str]]] = {head: set() for head in similar_heads}
    for row in db.execute(
        f"SELECT head,relation,tail,tail_type FROM triples WHERE dataset_id=? AND relation<>? AND head IN ({placeholders})",
        (dataset_id, relation, *similar_heads),
    ):
        related_features[row["head"]].add((row["relation"], row["tail"], row["tail_type"]))
    candidates: dict[tuple[str, str], dict] = {}
    seen_support: dict[tuple[str, str], set[str]] = {}
    for row in reference_rows:
        if row["head"] not in related_features:
            continue
        key = (row["tail"], row["tail_type"])
        if key in existing or key == (target_name, target_type):
            continue
        features = related_features[row["head"]]
        shared = target_features & features
        if not shared:
            continue
        similarity = len(shared) / len(target_features | features)
        score = round(0.75 * similarity + 0.25 * row["confidence"], 4)
        if not math.isfinite(score):
            continue
        shared_examples = [
            {"relation": item[0], "entity": item[1], "entity_type": item[2]}
            for item in sorted(shared)[:4]
        ]
        support = {
            "reference_id": row["id"],
            "similar_entity": row["head"],
            "shared_neighbors": shared_examples,
            "similarity": round(similarity, 4),
            "observed_confidence": row["confidence"],
            "source": row["source"],
            "evidence": row["evidence"],
        }
        item = candidates.setdefault(key, {
            "tail": row["tail"], "tail_type": row["tail_type"],
            "score": 0.0, "support_count": 0, "references": [],
            "status": "待核查",
        })
        if row["head"] not in seen_support.setdefault(key, set()):
            seen_support[key].add(row["head"])
            item["support_count"] += 1
        item["score"] = max(item["score"], score)
        if len(item["references"]) < 5:
            item["references"].append(support)
    ranked = sorted(candidates.values(), key=lambda item: (-item["score"], -item["support_count"], item["tail"]))
    for index, item in enumerate(ranked[:max_candidates], 1):
        item["rank"] = index
        item["references"].sort(key=lambda ref: (-ref["similarity"], -ref["observed_confidence"]))
    result = ranked[:max_candidates]
    return result, ("已找到有共享邻居支持的候选关系。" if result else "未找到满足共享邻居条件的候选关系。")


def create_task(payload):
    if not isinstance(payload, dict):
        raise ValueError("任务内容格式错误")
    name = payload.get("name")
    target_name = payload.get("target_name")
    target_type = payload.get("target_type")
    relation = payload.get("relation")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError("任务名称须为 1–100 个字符")
    for field_name, value in (("目标实体", target_name), ("实体类型", target_type), ("关系类型", relation)):
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 200:
            raise ValueError(f"{field_name}无效")
    try:
        dataset_id = int(payload.get("dataset_id"))
        max_candidates = int(payload.get("max_candidates", 10))
    except (TypeError, ValueError) as exc:
        raise ValueError("数据集或候选数量无效") from exc
    if not 1 <= max_candidates <= 30:
        raise ValueError("候选数量须在 1–30 之间")
    with kg_service.connect() as db:
        _tables(db)
        datasets, selected = kg_service._selected(db, dataset_id)
        if selected is None:
            raise ValueError("请先上传知识数据集")
        dataset = next(item for item in datasets if item["id"] == selected)
        if not db.execute(
            "SELECT 1 FROM triples WHERE dataset_id=? AND head=? AND head_type=? LIMIT 1",
            (selected, target_name.strip(), target_type.strip()),
        ).fetchone():
            raise ValueError("目标实体不在所选数据集中")
        if not db.execute(
            "SELECT 1 FROM triples WHERE dataset_id=? AND relation=? LIMIT 1",
            (selected, relation.strip()),
        ).fetchone():
            raise ValueError("关系类型不在所选数据集中")
        candidates, note = _predict(
            db, selected, target_name.strip(), target_type.strip(), relation.strip(), max_candidates
        )
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = {
            "dataset": dataset, "target_name": target_name.strip(), "target_type": target_type.strip(),
            "relation": relation.strip(), "method": METHOD, "note": note,
            "existing_count": db.execute(
                "SELECT COUNT(*) FROM triples WHERE dataset_id=? AND head=? AND head_type=? AND relation=?",
                (selected, target_name.strip(), target_type.strip(), relation.strip()),
            ).fetchone()[0],
            "candidates": candidates,
        }
        cursor = db.execute(
            """INSERT INTO prediction_tasks(dataset_id,name,target_name,target_type,relation,method,created_at,candidate_count,result_json)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (selected, name.strip(), target_name.strip(), target_type.strip(), relation.strip(),
             METHOD, created_at, len(candidates), json.dumps(result, ensure_ascii=False)),
        )
        result.update({"id": cursor.lastrowid, "name": name.strip(), "created_at": created_at})
        return result


def list_tasks(dataset_id=None):
    with kg_service.connect() as db:
        _tables(db)
        sql = """SELECT t.id,t.dataset_id,d.name AS dataset_name,t.name,t.target_name,t.target_type,
                        t.relation,t.method,t.created_at,t.candidate_count
                 FROM prediction_tasks AS t JOIN datasets AS d ON d.id=t.dataset_id"""
        params = []
        if dataset_id not in (None, ""):
            try:
                selected = int(dataset_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("数据集编号无效") from exc
            sql += " WHERE t.dataset_id=?"
            params.append(selected)
        sql += " ORDER BY t.id DESC LIMIT 50"
        return [dict(row) for row in db.execute(sql, params)]


def get_task(task_id):
    try:
        task_id = int(task_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("任务编号无效") from exc
    with kg_service.connect() as db:
        _tables(db)
        row = db.execute("SELECT * FROM prediction_tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            return None
        result = json.loads(row["result_json"])
        result.update({"id": row["id"], "name": row["name"], "created_at": row["created_at"]})
        return result
