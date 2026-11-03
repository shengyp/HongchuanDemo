"""Read-only exploration of the user-provided Food.com ingredient graph."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "data" / "foodcom.sqlite"


def _connect():
    if not DB_PATH.exists():
        return None
    db = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def summary() -> dict:
    db = _connect()
    if db is None:
        return {"available": False}
    try:
        result = {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT key,value FROM metadata")}
        result["available"] = True
        result["link_count"] = db.execute("SELECT COUNT(*) FROM recipe_ingredients").fetchone()[0]
        result["top_ingredients"] = [dict(row) for row in db.execute("SELECT id,name,frequency FROM ingredients ORDER BY frequency DESC LIMIT 12")]
        result["tail_examples"] = [dict(row) for row in db.execute("SELECT id,name,frequency FROM ingredients WHERE frequency <= ? ORDER BY name LIMIT 12", (result["tail_threshold"],))]
        return result
    finally:
        db.close()


def search(query: str) -> dict:
    if not isinstance(query, str) or len(query) > 100:
        raise ValueError("搜索文字不能超过 100 字")
    db = _connect()
    if db is None:
        return {"ingredients": [], "recipes": []}
    try:
        q = query.strip()
        if not q:
            return {"ingredients": [], "recipes": []}
        pattern = "%" + q.replace("%", "\\%").replace("_", "\\_") + "%"
        ingredients = [dict(row) for row in db.execute("SELECT id,name,frequency FROM ingredients WHERE name LIKE ? ESCAPE '\\' ORDER BY frequency DESC LIMIT 20", (pattern,))]
        recipes = [dict(row) for row in db.execute("SELECT id,name,minutes,ingredient_count FROM recipes WHERE name LIKE ? ESCAPE '\\' ORDER BY id LIMIT 20", (pattern,))]
        if not recipes and ingredients:
            recipes = [dict(row) for row in db.execute("SELECT r.id,r.name,r.minutes,r.ingredient_count FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id WHERE ri.ingredient_id=? ORDER BY r.id LIMIT 20", (ingredients[0]["id"],))]
        return {"ingredients": ingredients, "recipes": recipes}
    finally:
        db.close()


def ingredient_detail(ingredient_id: int) -> dict | None:
    db = _connect()
    if db is None:
        return None
    try:
        row = db.execute("SELECT id,name,frequency FROM ingredients WHERE id=?", (ingredient_id,)).fetchone()
        if row is None:
            return None
        details = dict(row)
        meta = {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT key,value FROM metadata WHERE key='tail_threshold'")}
        details["tail"] = details["frequency"] <= meta["tail_threshold"]
        details["neighbors"] = [dict(r) for r in db.execute("""
            SELECT i.id,i.name,i.frequency,COUNT(*) AS cooccur
            FROM recipe_ingredients seed
            JOIN recipe_ingredients peer ON peer.recipe_id=seed.recipe_id AND peer.ingredient_id<>seed.ingredient_id
            JOIN ingredients i ON i.id=peer.ingredient_id
            WHERE seed.ingredient_id=? GROUP BY i.id ORDER BY cooccur DESC,i.name LIMIT 12
        """, (ingredient_id,))]
        details["recipes"] = [dict(r) for r in db.execute("""
            SELECT r.id,r.name FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id
            WHERE ri.ingredient_id=? ORDER BY r.id LIMIT 12
        """, (ingredient_id,))]
        return details
    finally:
        db.close()


def graph_statistics() -> dict:
    """Statistics for observed recipe–ingredient edges; no inferred confidence."""
    db = _connect()
    if db is None:
        return {"available": False}
    try:
        recipe_count = db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        ingredient_count = db.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]
        edge_count = db.execute("SELECT COUNT(*) FROM recipe_ingredients").fetchone()[0]
        bins = [
            {"label": "1", "count": 0}, {"label": "2", "count": 0},
            {"label": "3–5", "count": 0}, {"label": "6–20", "count": 0},
            {"label": "21+", "count": 0},
        ]
        for row in db.execute("""SELECT
            SUM(CASE WHEN frequency=1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN frequency=2 THEN 1 ELSE 0 END),
            SUM(CASE WHEN frequency BETWEEN 3 AND 5 THEN 1 ELSE 0 END),
            SUM(CASE WHEN frequency BETWEEN 6 AND 20 THEN 1 ELSE 0 END),
            SUM(CASE WHEN frequency>=21 THEN 1 ELSE 0 END)
            FROM ingredients"""):
            for item, count in zip(bins, row):
                item["count"] = count or 0
        return {
            "available": True, "node_count": recipe_count + ingredient_count,
            "edge_count": edge_count, "entity_type_count": 2, "relation_type_count": 1,
            "node_types": [{"name": "食谱", "count": recipe_count}, {"name": "食材", "count": ingredient_count}],
            "relation_types": [{"name": "包含食材", "count": edge_count}],
            "frequency_bins": bins,
        }
    finally:
        db.close()


def graph_triples(q="", page=1, page_size=20) -> dict:
    """Page observed recipe–ingredient edges as provenance-preserving triples."""
    if not isinstance(q, str) or len(q) > 200:
        raise ValueError("检索词过长")
    try:
        page, page_size = int(page), int(page_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("分页参数无效") from exc
    if page < 1 or not 1 <= page_size <= 100:
        raise ValueError("分页参数无效")
    db = _connect()
    if db is None:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    try:
        condition = ""
        params = []
        if q.strip():
            condition = "WHERE r.name LIKE ? ESCAPE '\\' OR i.name LIKE ? ESCAPE '\\'"
            pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            params = [pattern, pattern]
        join = """FROM recipe_ingredients ri
            JOIN recipes r ON r.id=ri.recipe_id
            JOIN ingredients i ON i.id=ri.ingredient_id """
        total = db.execute("SELECT COUNT(*) " + join + condition, params).fetchone()[0]
        items = [dict(row) for row in db.execute(
            """SELECT r.id AS recipe_id, r.name AS recipe_name,
                      i.id AS ingredient_id, i.name AS ingredient_name,
                      i.frequency AS ingredient_frequency """ + join + condition +
            " ORDER BY ri.recipe_id,ri.ingredient_id LIMIT ? OFFSET ?",
            (*params, page_size, (page - 1) * page_size),
        )]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        db.close()


def graph_explore(q="", node_type="", depth=1) -> dict:
    """Bounded local Food.com bipartite graph; all edges are observed recipe membership."""
    if not isinstance(q, str) or len(q) > 200:
        raise ValueError("实体检索词过长")
    if node_type not in ("", "食谱", "食材"):
        raise ValueError("实体类型无效")
    try:
        depth = int(depth)
    except (TypeError, ValueError) as exc:
        raise ValueError("探索层级无效") from exc
    if depth not in (1, 2):
        raise ValueError("探索层级仅支持 1 或 2")
    empty = {"dataset": {"id": 0, "name": "Food.com 食谱数据"},
             "focus": None, "nodes": [], "edges": [], "depth": depth}
    db = _connect()
    if db is None:
        return empty
    try:
        term = q.strip()
        escaped = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        focus = None
        if node_type != "食谱":
            if term:
                focus = db.execute(
                    "SELECT id,name,frequency FROM ingredients WHERE name LIKE ? ESCAPE '\\' "
                    "ORDER BY CASE WHEN name=? THEN 0 ELSE 1 END,frequency DESC LIMIT 1",
                    (escaped, term)).fetchone()
            else:
                focus = db.execute("SELECT id,name,frequency FROM ingredients ORDER BY frequency DESC LIMIT 1").fetchone()
        if focus is not None:
            kind, entity_id = "食材", focus["id"]
            rows = db.execute("""SELECT r.id AS recipe_id,r.name AS recipe_name,
                        i.id AS ingredient_id,i.name AS ingredient_name
                        FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id
                        JOIN ingredients i ON i.id=ri.ingredient_id
                        WHERE ri.ingredient_id=? ORDER BY r.id LIMIT 60""", (entity_id,)).fetchall()
        else:
            if node_type == "食材":
                return empty
            recipe = db.execute(
                "SELECT id,name,ingredient_count FROM recipes WHERE name LIKE ? ESCAPE '\\' "
                "ORDER BY CASE WHEN name=? THEN 0 ELSE 1 END,id LIMIT 1",
                (escaped, term)).fetchone() if term else None
            if recipe is None:
                return empty
            kind, entity_id, focus = "食谱", recipe["id"], recipe
            rows = db.execute("""SELECT r.id AS recipe_id,r.name AS recipe_name,
                        i.id AS ingredient_id,i.name AS ingredient_name
                        FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id
                        JOIN ingredients i ON i.id=ri.ingredient_id
                        WHERE ri.recipe_id=? ORDER BY i.name LIMIT 60""", (entity_id,)).fetchall()
        edges = [dict(row) for row in rows]
        if depth == 2 and edges:
            if kind == "食材":
                recipe_ids = [row["recipe_id"] for row in edges[:12]]
                placeholders = ",".join("?" for _ in recipe_ids)
                extra = db.execute(f"""SELECT r.id AS recipe_id,r.name AS recipe_name,
                    i.id AS ingredient_id,i.name AS ingredient_name
                    FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id
                    JOIN ingredients i ON i.id=ri.ingredient_id
                    WHERE ri.recipe_id IN ({placeholders})
                    ORDER BY r.id,i.name LIMIT 100""", recipe_ids)
            else:
                ingredient_ids = [row["ingredient_id"] for row in edges[:12]]
                placeholders = ",".join("?" for _ in ingredient_ids)
                extra = db.execute(f"""SELECT r.id AS recipe_id,r.name AS recipe_name,
                    i.id AS ingredient_id,i.name AS ingredient_name
                    FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id
                    JOIN ingredients i ON i.id=ri.ingredient_id
                    WHERE ri.ingredient_id IN ({placeholders})
                    ORDER BY r.id,i.name LIMIT 100""", ingredient_ids)
            seen = {(row["recipe_id"], row["ingredient_id"]) for row in edges}
            for row in extra:
                key = (row["recipe_id"], row["ingredient_id"])
                if key not in seen:
                    edges.append(dict(row))
                    seen.add(key)
                if len(edges) >= 100:
                    break
        nodes = {}
        graph_edges = []
        for row in edges:
            recipe_key = "食谱::" + str(row["recipe_id"])
            ingredient_key = "食材::" + str(row["ingredient_id"])
            for key, label, type_name in (
                (recipe_key, row["recipe_name"], "食谱"),
                (ingredient_key, row["ingredient_name"], "食材"),
            ):
                if key not in nodes:
                    nodes[key] = {"id": key, "label": label, "type": type_name, "degree": 0}
                nodes[key]["degree"] += 1
            graph_edges.append({
                "id": row["recipe_id"] * 100000 + row["ingredient_id"],
                "dataset_id": 0, "head": row["recipe_name"], "relation": "包含食材",
                "tail": row["ingredient_name"], "confidence": None,
                "evidence": "Food.com 原始食谱中的食材组成",
                "source": "Food.com", "head_type": "食谱", "tail_type": "食材",
                "head_id": recipe_key, "tail_id": ingredient_key,
            })
        focus_id = kind + "::" + str(entity_id)
        if focus_id not in nodes:
            nodes[focus_id] = {"id": focus_id, "label": focus["name"], "type": kind, "degree": 0}
        return {**empty, "focus": nodes[focus_id], "nodes": list(nodes.values()), "edges": graph_edges}
    finally:
        db.close()
