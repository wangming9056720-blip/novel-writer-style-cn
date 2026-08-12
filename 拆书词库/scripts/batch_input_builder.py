#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2 Stage 2 批次输入包生成器。

输入：
- 原始小说 TXT
- Stage 0 chapter_manifest.jsonl
- block 起止范围

输出：
- 批次正文输入包 TXT（仅 BODY 作为取词来源）
- 批次级 STATE JSON

原则：
- 原文只读；
- 用 block_id 恢复，不依赖章节号连续；
- 校验每个 block 的 SHA256，防止切片漂移；
- 标题/元数据与正文显式隔离，避免进入词库；
- 本脚本只准备输入，不执行取词。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        raise ValueError("manifest 为空")
    return rows


def normalize_source(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    decoded = raw.decode("utf-8-sig")
    text = decoded.replace("\r\n", "\n").replace("\r", "\n")
    return raw, text


def build_package(source: Path, manifest: Path, start: int, end: int, book: str) -> tuple[str, dict]:
    raw, text = normalize_source(source)
    rows = load_manifest(manifest)
    selected = [r for r in rows if start <= int(r["block_id"]) <= end]
    expected_ids = list(range(start, end + 1))
    actual_ids = [int(r["block_id"]) for r in selected]
    if actual_ids != expected_ids:
        raise ValueError(f"block_id 不连续或缺失：expected={expected_ids}, actual={actual_ids}")

    bodies = []
    for row in selected:
        raw_block = text[int(row["start_char"]): int(row["end_char"])]
        if sha256_bytes(raw_block.encode("utf-8")) != row["sha256"]:
            raise ValueError(f"block {row['block_id']} SHA256 校验失败")
        first_newline = raw_block.find("\n")
        body = raw_block[first_newline + 1:] if first_newline >= 0 else ""
        bodies.append((row, body.strip()))

    batch_id = f"{start:03d}-{end:03d}"
    total_body_chars = sum(len(body) for _, body in bodies)

    out = [
        f"《{book}》V2 批次输入包",
        f"batch_id: {batch_id}",
        "status: READY_FOR_EXTRACTION",
        "rule_version: V2-stage2-1",
        f"source_sha256: {sha256_bytes(raw)}",
        f"block_ids: {batch_id}",
        f"block_count: {len(bodies)}",
        f"body_char_count: {total_body_chars}",
        f"first_heading: {bodies[0][0]['heading']}",
        f"last_heading: {bodies[-1][0]['heading']}",
        "",
        "使用说明：",
        "1. 本文件只作为 vocabulary-extractor-agent 的原文输入，不代表已完成取词。",
        "2. 仅提取每个 <BODY> 内的正文；HEADER/标题/元数据不得作为词汇来源。",
        "3. block_id 是唯一恢复主键；chapter_num 仅作来源标记。",
        "4. 每个词必须能追溯到对应 block_id 的原文证据。",
        "",
    ]

    for row, body in bodies:
        out.extend([
            f"<<<BLOCK {int(row['block_id']):03d}>>>",
            f"HEADING: {row['heading']}",
            f"KIND: {row['kind']}",
            f"CHAPTER_NUM: {row['chapter_num'] if row['chapter_num'] is not None else ''}",
            f"BLOCK_SHA256: {row['sha256']}",
            "<BODY>",
            body,
            "</BODY>",
            f"<<<END BLOCK {int(row['block_id']):03d}>>>",
            "",
        ])

    package_text = "\n".join(out)
    state = {
        "rule_version": "V2-stage2-1",
        "book": book,
        "batch_id": batch_id,
        "status": "READY_FOR_EXTRACTION",
        "pipeline_state": "CHAPTER_PARSED",
        "source_sha256": sha256_bytes(raw),
        "block_start": start,
        "block_end": end,
        "block_count": len(bodies),
        "block_ids": actual_ids,
        "first_heading": bodies[0][0]["heading"],
        "last_heading": bodies[-1][0]["heading"],
        "body_char_count": total_body_chars,
        "extractor_agent": "拆书词库/agents/vocabulary-extractor-agent.md",
        "candidate_output": "PENDING",
        "coverage_output": "PENDING",
        "clean_output": "PENDING",
        "processed": False,
        "coverage_status": "PENDING",
        "next_action": "将本批输入包交给 vocabulary-extractor-agent；完成取词后立刻保存候选结果，再进入 Coverage 审计。",
        "warnings": [],
    }
    return package_text, state


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    package_text, state = build_package(
        args.source, args.manifest, args.start, args.end, args.book
    )
    batch_id = f"{args.start:03d}-{args.end:03d}"
    package_path = args.out_dir / f"batch_{batch_id}_input.txt"
    package_path.write_text(package_text, encoding="utf-8")
    state["input_package_file"] = package_path.name
    state["input_package_sha256"] = sha256_bytes(package_path.read_bytes())

    state_path = args.out_dir / f"batch_{batch_id}_STATE.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
