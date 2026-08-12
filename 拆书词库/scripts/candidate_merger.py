#!/usr/bin/env python3
"""Deterministically merge V2 vocabulary candidate JSONL files.

This script does not discover words and does not clean/reject candidates. It only
merges already-reviewed discovery outputs, preserves first-seen order, validates
word uniqueness, and checks that every record carries evidence containing the
recorded word string.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: record must be an object")
            rows.append(row)
    return rows


def validate_record(row: dict, origin: str) -> None:
    word = row.get("word")
    evidence = row.get("evidence")
    if not isinstance(word, str) or not word:
        raise ValueError(f"{origin}: missing/invalid word")
    if not isinstance(evidence, str) or not evidence:
        raise ValueError(f"{origin}: {word!r} missing evidence")
    if word not in evidence:
        raise ValueError(f"{origin}: {word!r} not found in evidence")


def merge_sources(sources: Iterable[tuple[str, list[dict]]]) -> tuple[list[dict], list[dict]]:
    merged: list[dict] = []
    seen: dict[str, str] = {}
    overlaps: list[dict] = []

    for source_name, rows in sources:
        for idx, row in enumerate(rows, 1):
            validate_record(row, f"{source_name}:{idx}")
            word = row["word"]
            if word in seen:
                overlaps.append({
                    "word": word,
                    "first_source": seen[word],
                    "duplicate_source": source_name,
                })
                continue
            seen[word] = source_name
            merged.append(row)

    return merged, overlaps


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--rescan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    sources: list[tuple[str, list[dict]]] = [("base", load_jsonl(args.base))]
    if args.coverage:
        sources.append(("coverage", load_jsonl(args.coverage)))
    if args.rescan:
        sources.append(("rescan", load_jsonl(args.rescan)))

    merged, overlaps = merge_sources(sources)
    write_jsonl(args.output, merged)

    report = {
        "source_counts": {name: len(rows) for name, rows in sources},
        "merged_unique_count": len(merged),
        "overlap_count": len(overlaps),
        "overlaps": overlaps,
        "output_sha256": sha256_file(args.output),
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
