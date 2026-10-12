"""把 config/models.json 导出为 .env 中的 MODEL_* 配置行。

用途：模型清单既可以用 `server/config/models.json` 维护，也可以直接写在 `.env` 里。
本脚本用于把 JSON 里的清单转换成 .env 写法（可直接粘贴到 `.env` / `.env.example`）。

用法：
    cd server
    python scripts/export_models_env.py                 # 打印到终端
    python scripts/export_models_env.py -o models.env   # 写入文件
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = BASE_DIR / "config" / "models.json"

# 输出顺序与字段名（与 config/models.json 一致）
FIELD_ORDER = (
    "id",
    "model",
    "name",
    "provider",
    "icon",
    "badge",
    "color",
    "desc",
    "tags",
    "context",
    "released",
    "speed",
    "intelligence",
    "temp",
    "reasoning",
    "latency",
    "base_url",
)


def _render_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            return f"{value[0]}-{value[1]}"
        return ",".join(str(item) for item in value)
    return str(value)


def export(config_path: Path) -> list[str]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    models = raw.get("models", raw) if isinstance(raw, dict) else raw

    lines: list[str] = []
    for index, model in enumerate(models, start=1):
        if not isinstance(model, dict):
            continue
        parts = [
            f"{field}={_render_value(model[field])}"
            for field in FIELD_ORDER
            if field in model and model[field] not in (None, "")
        ]
        lines.append(f"MODEL_{index}=" + ";".join(parts))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 MODEL_* 环境变量写法")
    parser.add_argument("-c", "--config", default=str(DEFAULT_CONFIG), help="models.json 路径")
    parser.add_argument("-o", "--output", default="", help="输出文件（缺省打印到终端）")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在：{config_path}", file=sys.stderr)
        raise SystemExit(1)

    lines = export(config_path)
    text = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"已写入 {args.output}（共 {len(lines)} 个模型）")
    else:
        print(text)


if __name__ == "__main__":
    main()
