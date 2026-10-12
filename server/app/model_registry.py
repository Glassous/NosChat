"""模型清单注册表：从 config/models.json 加载，供 /api/models 与聊天路由使用。

设计要点：
- 上游统一为 OpenAI 兼容接口（一个 base url + 一个 key + 多个 model）；
- 每个条目除上游模型名（model）外，还包含前端所需的全部展示字段（介绍、发布日期、标签等）；
- 字段缺失时使用兜底值，避免前端读取 （如 latency[0]）时报错。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)

# 前端所需字段的兜底值
_DEFAULTS: dict[str, Any] = {
    "model": "",
    "name": "",
    "provider": "",
    "icon": "🤖",
    "badge": "",
    "color": "#667eea",
    "desc": "",
    "tags": [],
    "context": "—",
    "released": "",
    "speed": 3,
    "intelligence": 3,
    "temp": 0.7,
    "reasoning": False,
    "latency": [600, 1400],
}


def _clamp_int(value: Any, default: int, low: int = 1, high: int = 5) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _latency(value: Any) -> list[int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            low = max(50, int(value[0]))
            high = max(low, int(value[1]))
            return [low, high]
        except (TypeError, ValueError):
            pass
    return list(_DEFAULTS["latency"])


def _tags(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """补齐缺失字段并做类型收敛。"""
    entry: dict[str, Any] = dict(_DEFAULTS)
    for key, value in raw.items():
        if value is not None:
            entry[key] = value

    entry["id"] = str(raw.get("id") or raw.get("model") or "").strip()
    entry["model"] = str(entry.get("model") or entry["id"]).strip()
    entry["name"] = str(entry.get("name") or entry["id"])
    entry["provider"] = str(entry.get("provider") or "")
    entry["icon"] = str(entry.get("icon") or _DEFAULTS["icon"])
    entry["badge"] = str(entry.get("badge") or "")
    entry["color"] = str(entry.get("color") or _DEFAULTS["color"])
    entry["desc"] = str(entry.get("desc") or "")
    entry["context"] = str(entry.get("context") or _DEFAULTS["context"])
    entry["released"] = str(entry.get("released") or "")
    entry["tags"] = _tags(entry.get("tags"))
    entry["speed"] = _clamp_int(entry.get("speed"), _DEFAULTS["speed"])
    entry["intelligence"] = _clamp_int(entry.get("intelligence"), _DEFAULTS["intelligence"])
    try:
        entry["temp"] = float(entry.get("temp", _DEFAULTS["temp"]))
    except (TypeError, ValueError):
        entry["temp"] = _DEFAULTS["temp"]
    entry["temp"] = max(0.0, min(2.0, entry["temp"]))
    entry["reasoning"] = bool(entry.get("reasoning"))
    entry["latency"] = _latency(entry.get("latency"))
    # 可选：单模型覆盖全局 base url
    base_url = str(raw.get("base_url") or "").strip()
    if base_url:
        entry["base_url"] = base_url
    return entry


class ModelRegistry:
    """模型清单的单例持有者。"""

    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self._path = path or settings.models_config_file
        self._models: list[dict[str, Any]] = []
        self._index: dict[str, dict[str, Any]] = {}

    # ---- 生命周期 ----
    def load(self) -> list[dict[str, Any]]:
        """读取配置文件并建立索引；失败时记录日志并保持空清单。"""
        path = self._path
        if not path.exists():
            logger.error("模型清单文件不存在：%s", path)
            self._models, self._index = [], {}
            return self._models

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("模型清单解析失败（%s）：%s", path, exc)
            self._models, self._index = [], {}
            return self._models

        items = raw.get("models", []) if isinstance(raw, dict) else raw
        models: list[dict[str, Any]] = []
        index: dict[str, dict[str, Any]] = {}
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            entry = normalize(item)
            if not entry["id"]:
                logger.warning("忽略缺少 id 的模型条目：%s", item)
                continue
            if entry["id"] in index:
                logger.warning("模型 id 重复，后者被忽略：%s", entry["id"])
                continue
            models.append(entry)
            index[entry["id"]] = entry

        self._models, self._index = models, index
        logger.info("已加载模型清单：%s（共 %d 个模型）", path, len(models))
        return self._models

    # ---- 查询 ----
    @property
    def models(self) -> list[dict[str, Any]]:
        return self._models

    def get(self, model_id: str | None) -> dict[str, Any] | None:
        if not model_id:
            return None
        return self._index.get(model_id)

    def first(self) -> dict[str, Any] | None:
        return self._models[0] if self._models else None

    def resolve(self, model_id: str | None) -> dict[str, Any] | None:
        """按 id 取模型，取不到则回退到首个模型。"""
        return self.get(model_id) or self.first()

    def public_models(self) -> list[dict[str, Any]]:
        """对外暴露的模型字段（不含 base_url 等内部信息）。"""
        keys = tuple(_DEFAULTS.keys()) + ("id",)
        return [{key: model[key] for key in keys if key in model} for model in self._models]


registry = ModelRegistry()
