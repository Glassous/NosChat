"""模型清单注册表：优先从环境变量（MODEL_*）加载，其次读 config/models.json。

设计要点：
- 上游统一为 OpenAI 兼容接口（一个 base url + 一个 key + 多个 model）；
- 每个条目除上游模型名（model）外，还包含前端所需的全部展示字段（介绍、发布日期、标签等）；
- 字段缺失时使用兜底值，避免前端读取 （如 latency[0]）时报错；
- 环境变量写法（每个模型一条，字段用 `;` 分隔、`key=value` 形式）：
  MODEL_1=id=deepseek-v3;model=deepseek-chat;name=DeepSeek-V3;provider=深度求索;desc=...;released=2024-12-27
  只要定义了任意 MODEL_*，就以环境变量为准（忽略 models.json）。
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:  # python-dotenv 由 pydantic-settings 间接安装
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - 极端情况下仍支持进程环境变量
    dotenv_values = None  # type: ignore[assignment]

from .config import get_settings

logger = logging.getLogger(__name__)

# 环境变量中的模型键名：MODEL_1、MODEL_2 ...
_MODEL_ENV_PATTERN = re.compile(r"^MODEL_(\d+)$", re.IGNORECASE)

# 字段别名（统一映射到内部字段名）
_ENV_FIELD_ALIASES: dict[str, str] = {
    "id": "id",
    "model": "model",
    "model_name": "model",
    "upstream": "model",
    "upstream_model": "model",
    "name": "name",
    "provider": "provider",
    "icon": "icon",
    "badge": "badge",
    "color": "color",
    "desc": "desc",
    "description": "desc",
    "intro": "desc",
    "tags": "tags",
    "context": "context",
    "released": "released",
    "release": "released",
    "date": "released",
    "speed": "speed",
    "intelligence": "intelligence",
    "temp": "temp",
    "temperature": "temp",
    "reasoning": "reasoning",
    "latency": "latency",
    "base_url": "base_url",
    "baseurl": "base_url",
}

_TRUE_WORDS = {"1", "true", "yes", "y", "on", "是", "推理", "支持"}


def _as_bool(value: str) -> bool:
    return value.strip().lower() in _TRUE_WORDS


def _as_latency(value: str) -> list[int]:
    parts = [item for item in re.split(r"[-~,，]", value) if item.strip()]
    if len(parts) != 2:
        raise ValueError("latency 需形如 600-1200")
    return [int(float(parts[0])), int(float(parts[1]))]


_ENV_FIELD_PARSERS: dict[str, Callable[[str], Any]] = {
    "speed": lambda value: int(float(value)),
    "intelligence": lambda value: int(float(value)),
    "temp": float,
    "reasoning": _as_bool,
    "latency": _as_latency,
    "tags": lambda value: [item.strip() for item in re.split(r"[,|、]", value) if item.strip()],
}


def parse_env_model(raw: str, source: str) -> dict[str, Any]:
    """解析 `id=xx;name=yy;desc=zz` 形式的模型定义。"""
    data: dict[str, Any] = {}
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, sep, value = chunk.partition("=")
        if not sep:
            raise ValueError(f"{source} 中片段缺少 '='：{chunk}")
        field = _ENV_FIELD_ALIASES.get(key.strip().lower())
        if field is None:
            logger.warning("%s 中存在未知字段「%s」，已忽略", source, key.strip())
            continue
        text = value.strip()
        parser = _ENV_FIELD_PARSERS.get(field)
        try:
            data[field] = parser(text) if parser else text
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{source} 字段「{field}」取值非法：{text}") from exc
    return data


def env_model_entries() -> list[tuple[str, dict[str, Any]]]:
    """收集 MODEL_* 定义，按编号排序；进程环境变量优先于 .env 文件。"""
    raw_values: dict[str, str] = {}
    env_file = get_settings().env_file_path
    if dotenv_values is not None and env_file.exists():
        try:
            for key, value in dotenv_values(env_file).items():
                if key and value:
                    raw_values[key] = value
        except OSError as exc:  # pragma: no cover
            logger.warning("读取环境变量文件失败（%s）：%s", env_file, exc)
    raw_values.update({key: value for key, value in os.environ.items() if value})

    found: list[tuple[int, str, dict[str, Any]]] = []
    for key, value in raw_values.items():
        match = _MODEL_ENV_PATTERN.match(key.strip())
        if not match:
            continue
        try:
            found.append((int(match.group(1)), key.strip(), parse_env_model(value, key.strip())))
        except ValueError as exc:
            logger.error("环境变量中的模型定义无效，已跳过：%s", exc)

    found.sort(key=lambda item: item[0])
    return [(key, data) for _, key, data in found]

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
    def _build(self, items: list[Any], source: str) -> list[dict[str, Any]]:
        """规范化条目并建立索引。"""
        models: list[dict[str, Any]] = []
        index: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = normalize(item)
            if not entry["id"]:
                logger.warning("忽略缺少 id 的模型条目（%s）：%s", source, item)
                continue
            if entry["id"] in index:
                logger.warning("模型 id 重复，后者被忽略：%s（%s）", entry["id"], source)
                continue
            models.append(entry)
            index[entry["id"]] = entry

        self._models, self._index = models, index
        logger.info("已加载模型清单：%s（共 %d 个模型）", source, len(models))
        return self._models

    def load(self) -> list[dict[str, Any]]:
        """加载模型清单：环境变量 MODEL_* 优先，其次读取配置文件。"""
        env_items = env_model_entries()
        if env_items:
            keys = ", ".join(key for key, _ in env_items)
            logger.info("检测到环境变量模型定义（%s），忽略配置文件 %s", keys, self._path)
            return self._build([data for _, data in env_items], f"环境变量（{keys}）")

        path = self._path
        if not path.exists():
            logger.error("未配置 MODEL_* 环境变量，且模型清单文件不存在：%s", path)
            self._models, self._index = [], {}
            return self._models

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("模型清单解析失败（%s）：%s", path, exc)
            self._models, self._index = [], {}
            return self._models

        items = raw.get("models", []) if isinstance(raw, dict) else raw
        return self._build(items if isinstance(items, list) else [], str(path))

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
