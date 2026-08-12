#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网文整本 TXT 章节解析器。

目标：
- 原文只读；
- 识别“第X章”和“番外（N）”；
- 用内部 block_id 保证重复章号/缺号不丢正文；
- 输出可复现 manifest、SHA256 和异常报告。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

CHAPTER_RE = re.compile(r"^第\s*([零〇一二三四五六七八九十百千万两\d]+)\s*章(?:\s|$)(.*)$")
FANWAI_RE = re.compile(r"^番外(?:[（(]\s*(\d+)\s*[）)])?(?:\s|$)(.*)$")

CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNIT = {"十": 10, "百": 100, "千": 1000, "万": 10000}


def parse_cn_number(text: str) -> int | None:
    if text.isdigit():
        return int(text)
    total = section = digit = 0
    for ch in text:
        if ch in CN_DIGIT:
            digit = CN_DIGIT[ch]
        elif ch in CN_UNIT:
            unit = CN_UNIT[ch]
            if unit == 10000:
                section = (section + digit) or 1
                total += section * unit
                section = digit = 0
            else:
                section += (digit or 1) * unit
                digit = 0
        else:
            return None
    return total + section + digit


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_book(path: Path) -> tuple[dict, list[dict]]:
    raw_bytes = path.read_bytes()
    decoded = raw_bytes.decode("utf-8-sig")
    text = decoded.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.splitlines(keepends=True)
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line)

    headings = []
    for line_idx, raw_line in enumerate(lines):
        heading = raw_line.strip()
        cm = CHAPTER_RE.match(heading)
        fm = FANWAI_RE.match(heading)
        if cm:
            headings.append({
                "line_idx": line_idx,
                "heading": heading,
                "kind": "chapter",
                "chapter_num": parse_cn_number(cm.group(1)),
                "fanwai_num": None,
            })
        elif fm:
            headings.append({
                "line_idx": line_idx,
                "heading": heading,
                "kind": "fanwai",
                "chapter_num": None,
                "fanwai_num": int(fm.group(1)) if fm.group(1) else None,
            })

    if not headings:
        raise RuntimeError("未识别到章节标题")

    blocks = []
    for idx, h in enumerate(headings):
        start = offsets[h["line_idx"]]
        end = offsets[headings[idx + 1]["line_idx"]] if idx + 1 < len(headings) else len(text)
        raw_block = text[start:end]
        first_newline = raw_block.find("\n")
        body = raw_block[first_newline + 1:] if first_newline >= 0 else ""
        blocks.append({
            "block_id": idx + 1,
            "kind": h["kind"],
            "chapter_num": h["chapter_num"],
            "fanwai_num": h["fanwai_num"],
            "heading": h["heading"],
            "start_char": start,
            "end_char": end,
            "raw_char_count": len(raw_block),
            "body_char_count": len(body.strip()),
            "sha256": sha256_bytes(raw_block.encode("utf-8")),
        })

    numbered = [b["chapter_num"] for b in blocks if b["chapter_num"] is not None]
    counts = Counter(numbered)
    duplicates = [{"chapter_num": n, "count": c} for n, c in sorted(counts.items()) if c > 1]
    missing = [n for n in range(min(numbered), max(numbered) + 1) if n not in counts]

    summary = {
        "parser_version": "V2-stage0-1",
        "source_file": path.name,
        "source_bytes": len(raw_bytes),
        "source_chars_normalized": len(text),
        "source_chars_raw_decoded": len(decoded),
        "source_sha256": sha256_bytes(raw_bytes),
        "preface_char_count": blocks[0]["start_char"],
        "detected_blocks": len(blocks),
        "numbered_chapters": len(numbered),
        "fanwai_blocks": sum(1 for b in blocks if b["kind"] == "fanwai"),
        "numbered_range": [min(numbered), max(numbered)],
        "duplicate_chapter_numbers": duplicates,
        "missing_chapter_numbers": missing,
        "body_char_total": sum(b["body_char_count"] for b in blocks),
        "status": "CHAPTER_PARSED",
        "warnings": [
            *[f"重复章号：第{x['chapter_num']}章 × {x['count']}" for x in duplicates],
            *[f"章号缺失：第{n}章（仅记录编号异常，不据此判定正文缺失）" for n in missing],
        ],
    }
    return summary, blocks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out-dir", default="chapter_parse_output")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary, blocks = parse_book(Path(args.source))

    (out / "chapter_parse_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out / "chapter_manifest.jsonl").open("w", encoding="utf-8") as f:
        for row in blocks:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
