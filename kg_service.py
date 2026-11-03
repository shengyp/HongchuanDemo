"""Local storage and validation for uploaded uncertain knowledge triples."""
from __future__ import annotations

import csv
from contextlib import contextmanager
import io
import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("NUTRI_KG_DB", Path(__file__).resolve().parent / "data" / "kg.sqlite"))
FIELDS = ("head", "relation", "tail", "confidence", "evidence", "source", "head_type", "tail_type")
REQUIRED = ("head", "relation", "tail", "confidence")
MAX_ROWS = 100_000


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, filename TEXT NOT NULL,
            source TEXT NOT NULL, imported_at TEXT NOT NULL, triple_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS triples (
            id INTEGER PRIMARY KEY, dataset_id INTEGER NOT NULL REFERENCES datasets(id),
            head TEXT NOT NULL, relation TEXT NOT NULL, tail TEXT NOT NULL,
            confidence REAL NOT NULL, evidence TEXT NOT NULL, source TEXT NOT NULL,
            head_type TEXT NOT NULL, tail_type TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_triples_dataset ON triples(dataset_id);
        CREATE INDEX IF NOT EXISTS idx_triples_relation ON triples(dataset_id, relation);
    """)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def parse_dataset(filename, content, default_source):
    if not isinstance(filename, str) or not filename.lower().endswith((".csv", ".json")):
        raise ValueError("请选择 CSV 或 JSON 数据集")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("文件内容不能为空")
    if len(content.encode("utf-8")) > 20_000_000:
        raise ValueError("文件不能超过 20 MB")
    clean = content.lstrip("\ufeff")
    if filename.lower().endswith(".csv"):
        reader = csv.DictReader(io.StringIO(clean))
        columns = set(reader.fieldnames or [])
        if not set(REQUIRED).issubset(columns):
            raise ValueError("CSV 必须包含 head、relation、tail、confidence 四列")
        rows = list(reader)
    else:
        try:
            value = json.loads(clean)
        except json.JSONDecodeError as exc:
            raise ValueError("JSON 格式错误") from exc
        rows = value.get("triples") if isinstance(value, dict) else value
        if not isinstance(rows, list):
            raise ValueError("JSON 应为三元组数组或含 triples 数组的对象")
    if not rows:
        raise ValueError("数据集至少需要一条三元组")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"单次最多上传 {MAX_ROWS} 条三元组")
    result = []
    for index, raw in enumerate(rows, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"第 {index} 条记录必须是对象")
        values = {key: raw.get(key, "") for key in FIELDS}
        for key in REQUIRED:
            if values[key] is None or str(values[key]).strip() == "":
                raise ValueError(f"第 {index} 条缺少 {key}")
        try:
            confidence = float(values["confidence"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {index} 条 confidence 不是数字") from exc
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError(f"第 {index} 条 confidence 必须在 0–1 之间")
        def clean_field(key, limit=1000):
            value = values[key]
            if value is None:
                return ""
            if not isinstance(value, (str, int, float)):
                raise ValueError(f"第 {index} 条 {key} 格式错误")
            text = str(value).strip()
            if len(text) > limit:
                raise ValueError(f"第 {index} 条 {key} 过长")
            return text
        head = clean_field("head", 200)
        relation = clean_field("relation", 200)
        tail = clean_field("tail", 200)
        evidence = clean_field("evidence", 2000)
        source = clean_field("source", 300) or default_source
        head_type = clean_field("head_type", 100) or "未分类"
        tail_type = clean_field("tail_type", 100) or "未分类"
        result.append((head, relation, tail, confidence, evidence, source, head_type, tail_type))
    return result


def import_dataset(payload):
    filename = payload.get("filename")
    name = payload.get("dataset_name") or (Path(filename).stem if isinstance(filename, str) else "")
    source = payload.get("source") or "用户上传"
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("数据集名称须为 1–100 个字符")
    if not isinstance(source, str) or len(source.strip()) > 300:
        raise ValueError("来源说明不能超过 300 个字符")
    if not isinstance(filename, str) or len(filename) > 255:
        raise ValueError("文件名无效")
    rows = parse_dataset(filename, payload.get("content"), source.strip() or "用户上传")
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO datasets(name,filename,source,imported_at,triple_count) VALUES(?,?,?,?,?)",
            (name.strip(), Path(filename).name, source.strip() or "用户上传",
             datetime.now(timezone.utc).isoformat(timespec="seconds"), len(rows)),
        )
        dataset_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO triples(dataset_id,head,relation,tail,confidence,evidence,source,head_type,tail_type) VALUES(?,?,?,?,?,?,?,?,?)",
            ((dataset_id, *row) for row in rows),
        )
    return summary(dataset_id)



def rename_dataset(dataset_id, name):
    if not isinstance(dataset_id, int) or isinstance(dataset_id, bool) or dataset_id < 1:
        raise ValueError("数据集编号无效")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError("数据集名称须为 1–100 个字符")
    clean_name = name.strip()
    with connect() as db:
        if not db.execute("SELECT 1 FROM datasets WHERE id=?", (dataset_id,)).fetchone():
            raise ValueError("数据集不存在")
        if db.execute("SELECT 1 FROM datasets WHERE name=? AND id<>?", (clean_name, dataset_id)).fetchone():
            raise ValueError("已有同名数据集，请换一个名称")
        db.execute("UPDATE datasets SET name=? WHERE id=?", (clean_name, dataset_id))
    return summary(dataset_id)


def delete_dataset(dataset_id):
    if not isinstance(dataset_id, int) or isinstance(dataset_id, bool) or dataset_id < 1:
        raise ValueError("数据集编号无效；Food.com 默认数据集不可删除")
    with connect() as db:
        if not db.execute("SELECT 1 FROM datasets WHERE id=?", (dataset_id,)).fetchone():
            raise ValueError("数据集不存在")
        has_tasks = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prediction_tasks'"
        ).fetchone()
        if has_tasks:
            db.execute("DELETE FROM prediction_tasks WHERE dataset_id=?", (dataset_id,))
        db.execute("DELETE FROM triples WHERE dataset_id=?", (dataset_id,))
        db.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    return summary()

def _selected(db, dataset_id):
    datasets = [dict(row) for row in db.execute("SELECT * FROM datasets ORDER BY id DESC")]
    if not datasets:
        return datasets, None
    if dataset_id is None or dataset_id == "":
        return datasets, datasets[0]["id"]
    try:
        selected = int(dataset_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("数据集编号无效") from exc
    if selected not in {item["id"] for item in datasets}:
        raise ValueError("数据集不存在")
    return datasets, selected


def summary(dataset_id=None):
    with connect() as db:
        datasets, selected = _selected(db, dataset_id)
        if selected is None:
            return {"available": False, "datasets": [], "dataset": None}
        dataset = next(item for item in datasets if item["id"] == selected)
        nodes_cte = """WITH nodes AS (
            SELECT head AS name, head_type AS type FROM triples WHERE dataset_id=?
            UNION SELECT tail AS name, tail_type AS type FROM triples WHERE dataset_id=?
        )"""
        node_count = db.execute(nodes_cte + " SELECT COUNT(*) FROM nodes", (selected, selected)).fetchone()[0]
        node_types = [dict(row) for row in db.execute(
            nodes_cte + " SELECT type AS name, COUNT(*) AS count FROM nodes GROUP BY type ORDER BY count DESC, type",
            (selected, selected),
        )]
        relation_types = [dict(row) for row in db.execute(
            "SELECT relation AS name, COUNT(*) AS count FROM triples WHERE dataset_id=? GROUP BY relation ORDER BY count DESC, relation",
            (selected,),
        )]
        confidence_rows = db.execute(
            "SELECT confidence FROM triples WHERE dataset_id=?", (selected,)
        ).fetchall()
        bins = [{"label": label, "count": 0} for label in ("0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0")]
        for row in confidence_rows:
            bins[min(int(row["confidence"] * 5), 4)]["count"] += 1
        return {
            "available": True, "datasets": datasets, "dataset": dataset,
            "node_count": node_count, "edge_count": dataset["triple_count"],
            "entity_type_count": len(node_types), "relation_type_count": len(relation_types),
            "node_types": node_types, "relation_types": relation_types,
            "confidence_bins": bins,
            "average_confidence": round(sum(row["confidence"] for row in confidence_rows) / len(confidence_rows), 4),
        }


def triples(dataset_id=None, q="", page=1, page_size=20):
    if not isinstance(q, str) or len(q) > 200:
        raise ValueError("检索词过长")
    try:
        page, page_size = int(page), int(page_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("分页参数无效") from exc
    if page < 1 or not 1 <= page_size <= 100:
        raise ValueError("分页参数无效")
    with connect() as db:
        _, selected = _selected(db, dataset_id)
        if selected is None:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        condition = "dataset_id=?"
        params = [selected]
        if q.strip():
            condition += " AND (head LIKE ? OR relation LIKE ? OR tail LIKE ? OR evidence LIKE ?)"
            pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            condition = condition.replace(" LIKE ?", " LIKE ? ESCAPE '\\'")
            params.extend([pattern] * 4)
        total = db.execute(f"SELECT COUNT(*) FROM triples WHERE {condition}", params).fetchone()[0]
        items = [dict(row) for row in db.execute(
            f"SELECT * FROM triples WHERE {condition} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, page_size, (page - 1) * page_size),
        )]
        return {"items": items, "total": total, "page": page, "page_size": page_size}



def explore(dataset_id=None, q="", node_type="", relation="", depth=1):
    """Return a bounded ego graph from one uploaded dataset."""
    if not isinstance(q, str) or len(q) > 200:
        raise ValueError("实体检索词过长")
    if not isinstance(node_type, str) or len(node_type) > 100:
        raise ValueError("实体类型无效")
    if not isinstance(relation, str) or len(relation) > 200:
        raise ValueError("关系类型无效")
    try:
        depth = int(depth)
    except (TypeError, ValueError) as exc:
        raise ValueError("探索层级无效") from exc
    if depth not in (1, 2):
        raise ValueError("探索层级仅支持 1 或 2")
    with connect() as db:
        datasets, selected = _selected(db, dataset_id)
        if selected is None:
            return {"dataset": None, "focus": None, "nodes": [], "edges": [], "depth": depth}
        relation_where = " AND relation=?" if relation.strip() else ""
        node_sql = ("""WITH nodes AS (
            SELECT head AS name, head_type AS type FROM triples WHERE dataset_id=?""" + relation_where +
            """ UNION ALL
            SELECT tail AS name, tail_type AS type FROM triples WHERE dataset_id=?""" + relation_where +
            """) SELECT name, type, COUNT(*) AS degree FROM nodes WHERE 1=1""")
        params = ([selected, relation.strip(), selected, relation.strip()] if relation.strip()
                  else [selected, selected])
        if node_type.strip():
            node_sql += " AND type=?"
            params.append(node_type.strip())
        if q.strip():
            node_sql += " AND name LIKE ? ESCAPE '\\'"
            params.append("%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        node_sql += " GROUP BY name,type ORDER BY CASE WHEN name=? THEN 0 ELSE 1 END, degree DESC, name LIMIT 1"
        params.append(q.strip())
        center = db.execute(node_sql, params).fetchone()
        if center is None:
            return {"dataset": next(item for item in datasets if item["id"] == selected),
                    "focus": None, "nodes": [], "edges": [], "depth": depth}
        name, kind = center["name"], center["type"]
        relation_sql = " AND relation=?" if relation.strip() else ""
        relation_args = [relation.strip()] if relation.strip() else []
        first = [dict(row) for row in db.execute(
            "SELECT * FROM triples WHERE dataset_id=? AND "
            "((head=? AND head_type=?) OR (tail=? AND tail_type=?))"
            + relation_sql + " ORDER BY confidence DESC,id DESC LIMIT 60",
            (selected, name, kind, name, kind, *relation_args),
        )]
        edges = first[:]
        if depth == 2 and first:
            neighbors = set()
            for row in first:
                neighbors.add((row["head"], row["head_type"]))
                neighbors.add((row["tail"], row["tail_type"]))
            neighbors.discard((name, kind))
            extra_conditions = []
            extra_args = []
            for neighbor_name, neighbor_type in list(sorted(neighbors))[:24]:
                extra_conditions.append("(head=? AND head_type=?) OR (tail=? AND tail_type=?)")
                extra_args.extend((neighbor_name, neighbor_type, neighbor_name, neighbor_type))
            if extra_conditions:
                second = db.execute(
                    "SELECT * FROM triples WHERE dataset_id=? AND (" +
                    " OR ".join(extra_conditions) + ")" + relation_sql +
                    " ORDER BY confidence DESC,id DESC LIMIT 100",
                    (selected, *extra_args, *relation_args),
                )
                seen = {row["id"] for row in edges}
                for row in second:
                    if row["id"] not in seen:
                        edges.append(dict(row))
                        seen.add(row["id"])
                    if len(edges) >= 100:
                        break
        nodes = {(name, kind): {"id": kind + "::" + name, "label": name, "type": kind, "degree": center["degree"]}}
        for row in edges:
            for entity_name, entity_type in ((row["head"], row["head_type"]), (row["tail"], row["tail_type"])):
                key = (entity_name, entity_type)
                if key not in nodes:
                    nodes[key] = {"id": entity_type + "::" + entity_name, "label": entity_name, "type": entity_type, "degree": 0}
                nodes[key]["degree"] += 1
        return {
            "dataset": next(item for item in datasets if item["id"] == selected),
            "focus": {"id": kind + "::" + name, "label": name, "type": kind, "degree": center["degree"]},
            "nodes": list(nodes.values()),
            "edges": edges,
            "depth": depth,
        }
