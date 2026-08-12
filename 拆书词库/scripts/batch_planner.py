#!/usr/bin/env python3
"""V2 Stage 1 批次计划生成器。

输入：Stage 0 章节 manifest（JSON 数组或包含 blocks 字段的 JSON）。
输出：按内部 block_id 生成稳定批次；默认每批 20 块，最后一批允许不足 20 块。

关键原则：
- 批次主键只使用内部 block_id，不依赖章节号连续。
- 重复章节号、缺失章节号、番外不会改变批次切分。
- 每批保存首尾标题、块数、字符数和完整 block_id 列表，便于恢复与审计。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_blocks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    blocks = data.get("blocks", data) if isinstance(data, dict) else data
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("manifest 中没有可用 blocks")
    return blocks


def build_batches(blocks: list[dict[str, Any]], batch_size: int = 20) -> list[dict[str, Any]]:
    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(blocks), batch_size):
        chunk = blocks[offset : offset + batch_size]
        start = int(chunk[0]["block_id"])
        end = int(chunk[-1]["block_id"])
        batches.append(
            {
                "batch_no": len(batches) + 1,
                "batch_id": f"{start:03d}-{end:03d}",
                "block_start": start,
                "block_end": end,
                "block_count": len(chunk),
                "block_ids": [int(x["block_id"]) for x in chunk],
                "char_count": sum(int(x.get("char_count", 0)) for x in chunk),
                "first_title": chunk[0].get("title", ""),
                "last_title": chunk[-1].get("title", ""),
                "source_titles": [x.get("title", "") for x in chunk],
            }
        )
    return batches


def validate(blocks: list[dict[str, Any]], batches: list[dict[str, Any]]) -> None:
    expected = [int(x["block_id"]) for x in blocks]
    actual = [bid for batch in batches for bid in batch["block_ids"]]
    if actual != expected:
        raise ValueError("批次覆盖与原 manifest 不一致")
    if len(actual) != len(set(actual)):
        raise ValueError("批次中存在重复 block_id")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()

    blocks = load_blocks(args.manifest)
    batches = build_batches(blocks, args.batch_size)
    validate(blocks, batches)

    payload = {
        "rule_version": "V2-stage1-1",
        "batch_size": args.batch_size,
        "total_blocks": len(blocks),
        "total_batches": len(batches),
        "batches": batches,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
