"""Grounded nutrition Q&A with an optional local Ollama model."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from core import Engine

OLLAMA_URL = os.environ.get("NUTRI_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("NUTRI_OLLAMA_MODEL", "").strip()


def _remote_models() -> list[dict]:
    """Read model metadata only; API keys never leave the backend."""
    try:
        entries = json.loads(os.environ.get("NUTRI_LLM_PROVIDERS", "[]"))
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []
    result = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        name, endpoint, key_env = item.get("model"), item.get("base_url"), item.get("api_key_env")
        if not all(isinstance(value, str) and value.strip() for value in (name, endpoint, key_env)):
            continue
        if not endpoint.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            continue
        result.append({"id": f"remote:{len(result)}", "label": str(item.get("label", name))[:80],
                       "provider": str(item.get("provider", "兼容接口"))[:40],
                       "available": bool(os.environ.get(key_env)), "model": name,
                       "base_url": endpoint.rstrip("/"), "api_key_env": key_env})
    return result


def model_catalog() -> dict:
    models = [{"id": "knowledge", "label": "知识检索", "provider": "系统内置", "available": True,
               "message": "根据当前食谱库返回可追溯的检索结果"}]
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=2) as response:
            data = json.load(response)
        names = sorted({item.get("name") for item in data.get("models", []) if isinstance(item, dict) and isinstance(item.get("name"), str)})
        for name in names:
            models.append({"id": f"ollama:{name}", "label": name, "provider": "Ollama 本地模型",
                           "available": True, "message": "本地模型已就绪"})
        if OLLAMA_MODEL and OLLAMA_MODEL not in names:
            models.append({"id": f"ollama:{OLLAMA_MODEL}", "label": OLLAMA_MODEL, "provider": "Ollama 本地模型",
                           "available": False, "message": "配置的模型尚未安装"})
    except (OSError, ValueError, urllib.error.URLError):
        if OLLAMA_MODEL:
            models.append({"id": f"ollama:{OLLAMA_MODEL}", "label": OLLAMA_MODEL, "provider": "Ollama 本地模型",
                           "available": False, "message": "无法连接 Ollama"})
    for item in _remote_models():
        models.append({key: item[key] for key in ("id", "label", "provider", "available")} |
                      {"message": "已配置密钥；调用时验证连接" if item["available"] else "尚未配置密钥"})
    return {"default": "knowledge", "models": models}


def model_status() -> dict:
    """Legacy endpoint response for older frontend bundles."""
    catalog = model_catalog()
    available = next((m for m in catalog["models"] if m["id"] != "knowledge" and m["available"]), None)
    return {"configured": len(catalog["models"]) > 1, "available": available is not None,
            "model": available["label"] if available else None,
            "message": "大模型已就绪" if available else "当前可使用知识检索回答"}


def parse_request(question: str, engine: Engine) -> tuple[dict, list[str], list[str]]:
    specs = {
        "energy_kcal": r"(?:能量|热量)\D{0,8}(\d+(?:\.\d+)?)\s*(?:千卡|kcal)?",
        "protein_g": r"蛋白质\D{0,8}(\d+(?:\.\d+)?)\s*(?:克|g)?",
        "fat_g": r"脂肪\D{0,8}(\d+(?:\.\d+)?)\s*(?:克|g)?",
        "carbs_g": r"(?:碳水|碳水化合物)\D{0,8}(\d+(?:\.\d+)?)\s*(?:克|g)?",
        "fiber_g": r"(?:纤维|膳食纤维)\D{0,8}(\d+(?:\.\d+)?)\s*(?:克|g)?",
        "sodium_mg": r"钠\D{0,8}(\d+(?:\.\d+)?)\s*(?:毫克|mg)?",
    }
    targets = {}
    for key, pattern in specs.items():
        match = re.search(pattern, question, re.I)
        if match:
            value = float(match.group(1))
            if value > 0:
                targets[key] = value
    likes, dislikes = [], []
    for item in engine.ingredients.values():
        name = item["name"]
        if name not in question:
            continue
        prefix = question[max(0, question.find(name) - 6) : question.find(name)]
        (dislikes if re.search(r"不吃|不要|避免|过敏|禁用|排除", prefix) else likes).append(item["id"])
    return targets, likes, dislikes


def answer(question: str, engine: Engine, history: list[dict] | None = None,
           model_id: str = "knowledge") -> tuple[str, str, list[dict]]:
    catalog = model_catalog()
    selected = next((item for item in catalog["models"] if item["id"] == model_id), None)
    if selected is None:
        raise ValueError("所选模型不存在，请刷新模型列表")
    if not selected["available"]:
        raise ValueError(f"模型 {selected['label']} 当前不可用：{selected['message']}")
    targets, likes, dislikes = parse_request(question, engine)
    recipes = engine.recommend(targets, likes, dislikes, limit=3)
    context = [{"name": x["name"], "per_serving": x["nutrition"], "score": x["score"],
                "ingredients": x["ingredients"]} for x in recipes]
    if model_id == "knowledge":
        if "长尾" in question or "知识补偿" in question:
            count = len([key for key in engine.ingredients if engine.is_tail(key)])
            return (f"在当前数据集中，长尾食材指在食谱中出现次数较少的食材。系统以出现频次的第 25 百分位为阈值，目前识别出 {count} 种长尾食材。知识补偿会参考较常见且特征相近的食材，提出候选关联；这些关联会单独标记为推断，不会改变营养数值。",
                    model_id, context)
        if not recipes:
            return "当前食谱库中没有符合排除条件的候选食谱。可以调整偏好，或导入更多食谱数据。", model_id, context
        lines = ["根据当前食谱库，找到以下候选（每份营养值由程序计算）："]
        for index, recipe in enumerate(recipes, 1):
            n = recipe["nutrition"]
            lines.append(f"{index}. {recipe['name']}：约 {n['energy_kcal']} kcal，蛋白质 {n['protein_g']} g，膳食纤维 {n['fiber_g']} g，钠 {n['sodium_mg']} mg。")
        lines.append("这些是算法排序结果；候选关联需要核查。")
        return "\n".join(lines), model_id, context

    prompt = ("你是营养食谱研究助手。只能根据提供的食谱和营养数值回答；不要编造营养数据或医学结论。若不能满足目标，请明确说明。"
              "回答用简体中文，简洁列出推荐依据。推断关联不能作为真实食谱事实。\n用户问题：" + question +
              "\n约束解析：" + json.dumps({"targets": targets, "likes": likes, "dislikes": dislikes}, ensure_ascii=False) +
              "\n候选食谱：" + json.dumps(context, ensure_ascii=False))
    messages = [{"role": "system", "content": "你是基于本地食谱知识库的研究助手。营养值来自程序计算，不可篡改。"}]
    for item in (history or [])[-8:]:
        if item.get("role") in ("user", "assistant"):
            messages.append({"role": item["role"], "content": item.get("content", "")[:2000]})
    messages.append({"role": "user", "content": prompt})
    remote = None
    if model_id.startswith("ollama:"):
        model_name = model_id.removeprefix("ollama:")
        payload = json.dumps({"model": model_name, "messages": messages, "stream": False}, ensure_ascii=False).encode()
        request = urllib.request.Request(OLLAMA_URL + "/api/chat", payload,
                                         {"Content-Type": "application/json"}, method="POST")
    else:
        remote = next((item for item in _remote_models() if item["id"] == model_id), None)
        if remote is None or not remote["available"]:
            raise ValueError("所选模型配置已变更，请刷新模型列表")
        payload = json.dumps({"model": remote["model"], "messages": messages, "stream": False},
                             ensure_ascii=False).encode()
        request = urllib.request.Request(
            remote["base_url"] + "/chat/completions", payload,
            {"Content-Type": "application/json",
             "Authorization": "Bearer " + os.environ[remote["api_key_env"]]}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
        content = (result.get("message", {}).get("content", "") if model_id.startswith("ollama:")
                   else result.get("choices", [{}])[0].get("message", {}).get("content", ""))
        if not isinstance(content, str) or not content.strip():
            raise ValueError("模型返回了空回答")
        saved_model = model_id if remote is None else f"{remote["provider"]} · {remote["label"]} ({remote["model"]})"
        return content.strip(), saved_model, context
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ValueError(f"模型调用失败：{error}") from error
