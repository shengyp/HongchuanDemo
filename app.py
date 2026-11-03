"""Local HTTP interface for the long-tail nutrition recipe system."""

from __future__ import annotations

import json
import math
import os
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import auth
from assistant_service import answer, model_catalog, model_status
from core import Engine, NUTRIENTS
from csv_import import parse_csv_dataset
from generator import generate
import foodcom_service
import kg_service
import prediction_service
import diy_confidence

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "current.json"
DEMO_FILE = ROOT / "data" / "demo.json"
FDC_CATALOG = ROOT / "data" / "fdc_foundation_complete.json"
DEMO_ENGINE = Engine(json.loads(DEMO_FILE.read_text(encoding="utf-8")))
ENGINE = Engine(json.loads(DATA_FILE.read_text(encoding="utf-8"))) if DATA_FILE.exists() else DEMO_ENGINE


def nutrition_engine(value=None):
    if value in (None, "", "current"):
        return ENGINE
    if value == "demo":
        return DEMO_ENGINE
    raise ValueError("营养数据集无效")


def nutrition_datasets():
    result = [{"id": "demo", "name": DEMO_ENGINE.summary()["dataset_title"], "is_demo": True}]
    if DATA_FILE.exists():
        current = ENGINE.summary()
        result.insert(0, {"id": "current", "name": current["dataset_title"], "is_demo": current["is_demo"]})
    return result


class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj, status=200, cookie=None):
        payload = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def session_token(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
            return jar["nutri_session"].value if "nutri_session" in jar else None
        except cookies.CookieError:
            return None

    def current_user(self):
        return auth.get_user(self.session_token())

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json({"error": "请先登录"}, 401)
        return user

    def read_body(self, max_size=10_000_000):
        size = int(self.headers.get("Content-Length", "0"))
        if size < 0 or size > max_size:
            raise ValueError(f"请求不能超过 {max_size // 1_000_000} MB")
        body = json.loads(self.rfile.read(size) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("请求内容必须是 JSON 对象")
        return body

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/me":
            user = self.current_user()
            if user:
                return self.send_json(user)
            user = auth.guest_user()
            token = auth.create_session(user["id"])
            return self.send_json(user, 200, f"nutri_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={auth.SESSION_SECONDS}")
        if route.startswith("/api/"):
            user = self.require_user()
            if not user:
                return
            if route == "/api/kg/summary":
                try:
                    dataset_id = parse_qs(urlparse(self.path).query).get("dataset_id", [None])[0]
                    return self.send_json(kg_service.summary(dataset_id))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if route == "/api/kg/explore":
                try:
                    query = parse_qs(urlparse(self.path).query)
                    return self.send_json(kg_service.explore(
                        query.get("dataset_id", [None])[0], query.get("q", [""])[0],
                        query.get("node_type", [""])[0], query.get("relation", [""])[0],
                        query.get("depth", [1])[0]))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if route == "/api/kg/entities":
                try:
                    query = parse_qs(urlparse(self.path).query)
                    return self.send_json(prediction_service.entities(
                        query.get("dataset_id", [None])[0], query.get("q", [""])[0],
                        query.get("relation", [""])[0]))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if route == "/api/kg/prediction-tasks":
                try:
                    dataset_id = parse_qs(urlparse(self.path).query).get("dataset_id", [None])[0]
                    return self.send_json(prediction_service.list_tasks(dataset_id))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if route.startswith("/api/kg/prediction-tasks/"):
                try:
                    item = prediction_service.get_task(route.rsplit("/", 1)[-1])
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
                return self.send_json(item if item else {"error": "任务不存在"}, 200 if item else 404)
            if route == "/api/kg/triples":
                try:
                    query = parse_qs(urlparse(self.path).query)
                    return self.send_json(kg_service.triples(
                        query.get("dataset_id", [None])[0], query.get("q", [""])[0],
                        query.get("page", [1])[0], query.get("page_size", [20])[0]))
                except ValueError as error:
                    return self.send_json({"error": str(error)}, 400)
            if route == "/api/models":
                return self.send_json(model_catalog())
            if route == "/api/model/status":
                return self.send_json(model_status())
            if route == "/api/conversations":
                return self.send_json(auth.list_conversations(user["id"]))
            if route.startswith("/api/conversations/"):
                try:
                    item = auth.get_conversation(user["id"], int(route.rsplit("/", 1)[-1]))
                except ValueError:
                    item = None
                return self.send_json(item if item else {"error": "对话不存在"}, 200 if item else 404)
        if route == "/api/nutrition-datasets":
            return self.send_json(nutrition_datasets())
        if route == "/api/summary":
            try:
                source = parse_qs(urlparse(self.path).query).get("nutrition_dataset", [None])[0]
                return self.send_json(nutrition_engine(source).summary())
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if route == "/api/foodcom/summary":
            return self.send_json(foodcom_service.summary())
        if route == "/api/foodcom/graph-statistics":
            return self.send_json(foodcom_service.graph_statistics())
        if route == "/api/foodcom/graph-explore":
            try:
                query = parse_qs(urlparse(self.path).query)
                return self.send_json(foodcom_service.graph_explore(
                    query.get("q", [""])[0], query.get("node_type", [""])[0],
                    query.get("depth", [1])[0]))
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if route == "/api/foodcom/graph-triples":
            try:
                query = parse_qs(urlparse(self.path).query)
                return self.send_json(foodcom_service.graph_triples(
                    query.get("q", [""])[0], query.get("page", [1])[0]))
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if route == "/api/foodcom/search":
            try:
                query = parse_qs(urlparse(self.path).query).get("q", [""])[0]
                return self.send_json(foodcom_service.search(query))
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if route.startswith("/api/foodcom/ingredient/"):
            try:
                ingredient_id = int(route.rsplit("/", 1)[-1])
            except ValueError:
                return self.send_json({"error": "食材编号无效"}, 400)
            detail = foodcom_service.ingredient_detail(ingredient_id)
            return self.send_json(detail if detail else {"error": "食材不存在"}, 200 if detail else 404)
        if route == "/api/source-catalog":
            return self.send_json(json.loads(FDC_CATALOG.read_text(encoding="utf-8")) if FDC_CATALOG.exists() else {"source": None, "records": []})
        if route == "/api/ingredients":
            try:
                source = parse_qs(urlparse(self.path).query).get("nutrition_dataset", [None])[0]
                return self.send_json(nutrition_engine(source).ingredient_rows())
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if route == "/api/recipes":
            try:
                source = parse_qs(urlparse(self.path).query).get("nutrition_dataset", [None])[0]
                engine = nutrition_engine(source)
                return self.send_json([{"id": r["id"], "name": r["name"], "nutrition": engine.nutrition(r)} for r in engine.recipes])
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if route.startswith("/api/ingredient/"):
            try:
                source = parse_qs(urlparse(self.path).query).get("nutrition_dataset", [None])[0]
                engine = nutrition_engine(source)
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
            key = route.rsplit("/", 1)[-1]
            if key not in engine.ingredients:
                return self.send_json({"error": "食材不存在"}, 404)
            return self.send_json({"ingredient": engine.ingredients[key], "frequency": engine.frequency[key], "tail": engine.is_tail(key), "similar": engine.similar_ingredients(key), "neighbors": engine.compensated_neighbors(key)})
        assets = ROOT / "dist"
        path = assets / ("index.html" if route == "/" else route.lstrip("/"))
        if not path.resolve().is_relative_to(assets.resolve()) or not path.is_file():
            return self.send_json({"error": "路径不存在"}, 404)
        mime = {".html": "text/html", ".css": "text/css", ".js": "application/javascript", ".svg": "image/svg+xml"}.get(path.suffix, "application/octet-stream")
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        global ENGINE
        route = urlparse(self.path).path
        if route not in ("/api/register", "/api/login", "/api/logout", "/api/chat", "/api/recommend", "/api/generate", "/api/import", "/api/import-csv", "/api/reset", "/api/kg/import", "/api/kg/datasets/rename", "/api/kg/datasets/delete", "/api/kg/prediction-tasks", "/api/diy/assess"):
            return self.send_json({"error": "路径不存在"}, 404)
        try:
            body = self.read_body(30_000_000 if route == "/api/kg/import" else 10_000_000)
            if route == "/api/register":
                user = auth.register(body.get("username"), body.get("password"))
                token = auth.create_session(user["id"])
                return self.send_json(user, 201, f"nutri_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={auth.SESSION_SECONDS}")
            if route == "/api/login":
                user = auth.verify(body.get("username"), body.get("password"))
                if not user:
                    return self.send_json({"error": "账号或密码错误"}, 401)
                token = auth.create_session(user["id"])
                return self.send_json(user, 200, f"nutri_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={auth.SESSION_SECONDS}")
            if route == "/api/logout":
                auth.delete_session(self.session_token())
                return self.send_json({"ok": True}, 200, "nutri_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            user = self.require_user()
            if not user:
                return
            if route == "/api/kg/import":
                return self.send_json(kg_service.import_dataset(body), 201)
            if route == "/api/kg/datasets/rename":
                return self.send_json(kg_service.rename_dataset(body.get("dataset_id"), body.get("name")))
            if route == "/api/kg/datasets/delete":
                return self.send_json(kg_service.delete_dataset(body.get("dataset_id")))
            if route == "/api/kg/prediction-tasks":
                return self.send_json(prediction_service.create_task(body), 201)
            if route == "/api/diy/assess":
                return self.send_json(diy_confidence.assess(nutrition_engine(body.get('nutrition_dataset')), body))
            if route == "/api/chat":
                question = body.get("question")
                if not isinstance(question, str) or not question.strip() or len(question) > 3000:
                    raise ValueError("问题须为 1–3000 个字符")
                conversation_id = body.get("conversation_id")
                if conversation_id is not None and (not isinstance(conversation_id, int) or conversation_id < 1):
                    raise ValueError("对话编号无效")
                history = []
                if conversation_id is not None:
                    existing = auth.get_conversation(user["id"], conversation_id)
                    if not existing:
                        return self.send_json({"error": "对话不存在"}, 404)
                    history = existing["messages"]
                model_id = body.get("model_id", "knowledge")
                if not isinstance(model_id, str) or len(model_id) > 120:
                    raise ValueError("模型编号无效")
                response, mode, references = answer(question.strip(), nutrition_engine(body.get('nutrition_dataset')), history, model_id)
                saved = auth.save_exchange(user["id"], conversation_id, question.strip(), response, mode)
                saved["references"] = references
                return self.send_json(saved)
            if route == "/api/recommend":
                targets = {k: float(v) for k, v in body.get("targets", {}).items() if k in NUTRIENTS and v not in (None, "")}
                if any(not math.isfinite(v) or v <= 0 for v in targets.values()):
                    raise ValueError("营养目标必须是正数")
                likes = body.get("likes", [])
                dislikes = body.get("dislikes", [])
                if not isinstance(likes, list) or not isinstance(dislikes, list) or not all(isinstance(x, str) for x in likes + dislikes):
                    raise ValueError("食材偏好格式错误")
                return self.send_json(nutrition_engine(body.get('nutrition_dataset')).recommend(targets, likes, dislikes))
            if route == "/api/generate":
                return self.send_json(generate(nutrition_engine(body.get('nutrition_dataset')), body.get("recipe_id"), body.get("targets")))
            if route in ("/api/import", "/api/import-csv"):
                dataset = parse_csv_dataset(body.get("ingredient_csv"), body.get("recipe_csv"), body.get("source", "用户提供的 CSV")) if route == "/api/import-csv" else body
                candidate = Engine(dataset)
                DATA_FILE.parent.mkdir(exist_ok=True)
                temp = DATA_FILE.with_suffix(".tmp")
                temp.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
                temp.replace(DATA_FILE)
                ENGINE = candidate
                return self.send_json(ENGINE.summary())
            if DATA_FILE.exists():
                DATA_FILE.unlink()
            ENGINE = DEMO_ENGINE
            return self.send_json(ENGINE.summary())
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            return self.send_json({"error": str(error)}, 400)


def main():
    auth.init_db()
    host = os.environ.get("NUTRI_HOST", "127.0.0.1")
    port = int(os.environ.get("NUTRI_PORT", "8765"))
    print(f"长尾营养食谱系统: http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
