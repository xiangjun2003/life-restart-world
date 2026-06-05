#!/usr/bin/env python3
"""Convert VickScarlet/lifeRestart XLSX data into a content pack.

No third-party dependencies are used. XLSX files are zip archives containing
XML, which is enough for the simple tabular sheets used by the upstream game.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}

EFFECT_KEYS = {"CHR", "INT", "STR", "MNY", "SPR", "LUK", "AGE", "LIF"}


def text_of(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext())


def normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        if re.fullmatch(r"-?\d+", value):
            return int(value)
        if re.fullmatch(r"-?\d+\.0+", value):
            return int(float(value))
        if re.fullmatch(r"-?\d+\.\d+", value):
            return float(value)
    return value


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for char in letters:
        value = value * 26 + (ord(char.upper()) - ord("A") + 1)
    return value - 1


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings = []
    for si in root.findall("main:si", NS):
        strings.append(text_of(si))
    return strings


def first_sheet_name(zf: zipfile.ZipFile) -> str:
    names = sorted(name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
    if not names:
        raise ValueError("No worksheet XML found in xlsx")
    return names[0]


def read_xlsx(path: Path) -> list[list[Any]]:
    with zipfile.ZipFile(path) as zf:
        shared = read_shared_strings(zf)
        sheet = ET.fromstring(zf.read(first_sheet_name(zf)))
    rows: list[list[Any]] = []
    for row in sheet.findall(".//main:sheetData/main:row", NS):
        values: dict[int, Any] = {}
        for cell in row.findall("main:c", NS):
            ref = cell.attrib.get("r", "")
            index = column_index(ref)
            cell_type = cell.attrib.get("t")
            if cell_type == "s":
                raw = text_of(cell.find("main:v", NS))
                value = shared[int(raw)] if raw else None
            elif cell_type == "inlineStr":
                value = text_of(cell.find("main:is", NS))
            else:
                value = text_of(cell.find("main:v", NS))
            values[index] = normalize(value)
        if not values:
            rows.append([])
            continue
        max_index = max(values)
        rows.append([values.get(i) for i in range(max_index + 1)])
    return rows


def row_records(rows: list[list[Any]]) -> tuple[list[str], list[list[Any]]]:
    if not rows:
        return [], []
    headers = [str(value) if value is not None else "" for value in rows[0]]
    return headers, rows[2:]


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None]
    return [value]


def split_weighted(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value)
    if "*" in text:
        event_id, weight = text.split("*", 1)
        return {"event_id": normalize(event_id), "weight": int(float(weight))}
    return {"event_id": normalize(text), "weight": 1}


def condition_branch(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value)
    if ":" not in text:
        return None
    condition, next_id = text.rsplit(":", 1)
    return {"if": condition, "next": normalize(next_id)}


def event_to_choice(text: Any) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    value = re.sub(r"[。.!！]+$", "", value)
    return value[:48]


def parse_effects(record: dict[str, list[Any]]) -> dict[str, int]:
    effects = {}
    for key, values in record.items():
        if not key.startswith("effect:"):
            continue
        prop = key.split(":", 1)[1]
        if prop not in EFFECT_KEYS:
            continue
        total = 0
        for value in values:
            if value is None:
                continue
            try:
                total += int(float(value))
            except (TypeError, ValueError):
                pass
        if total:
            effects[prop] = total
    return effects


def build_record(headers: list[str], row: list[Any]) -> dict[str, list[Any]]:
    record: dict[str, list[Any]] = {}
    for index, header in enumerate(headers):
        if not header:
            continue
        value = row[index] if index < len(row) else None
        if value is None:
            continue
        record.setdefault(header, []).append(value)
    return record


def first(record: dict[str, list[Any]], key: str, default: Any = None) -> Any:
    values = record.get(key, [])
    return values[0] if values else default


def parse_talents(path: Path) -> list[dict[str, Any]]:
    headers, rows = row_records(read_xlsx(path))
    talents = []
    for row in rows:
        record = build_record(headers, row)
        talent_id = first(record, "$id")
        if talent_id is None:
            continue
        effects = parse_effects(record)
        talent = {
            "id": str(talent_id),
            "name": str(first(record, "name", talent_id)),
            "description": str(first(record, "description", "")),
            "condition": first(record, "condition"),
            "grade": int(first(record, "grade", 0) or 0),
            "effects": effects,
            "status": first(record, "status"),
            "exclude": [str(v) for v in record.get("exclude[]", [])],
            "source": "VickScarlet/lifeRestart MIT",
        }
        talents.append({k: v for k, v in talent.items() if v not in (None, [], {})})
    return talents


def parse_events(path: Path) -> list[dict[str, Any]]:
    headers, rows = row_records(read_xlsx(path))
    events = []
    for row in rows:
        record = build_record(headers, row)
        event_id = first(record, "$id")
        if event_id is None:
            continue
        effects = parse_effects(record)
        terminal = effects.get("LIF", 0) < 0
        event = {
            "id": str(event_id),
            "title": str(first(record, "event", event_id)),
            "weight": max(1, int(first(record, "grade", 1) or 1)),
            "effects": effects,
            "include": first(record, "include"),
            "exclude": first(record, "exclude"),
            "terminal": terminal,
            "terminal_reason": "Life force fell below survival." if terminal else None,
            "tags": ["upstream_event"],
            "narrative_seed": str(first(record, "event", "")),
            "source": "VickScarlet/lifeRestart MIT",
        }
        events.append({k: v for k, v in event.items() if v not in (None, [], {})})
    return events


def parse_age_pools(path: Path) -> dict[str, list[dict[str, Any]]]:
    headers, rows = row_records(read_xlsx(path))
    pools: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        record = build_record(headers, row)
        age = first(record, "$age")
        if age is None:
            continue
        entries = []
        for value in record.get("event[]", []):
            item = split_weighted(value)
            if item:
                item["event_id"] = str(item["event_id"])
                entries.append(item)
        if entries:
            pools[str(age)] = entries
    return pools


def parse_achievements(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    headers, rows = row_records(read_xlsx(path))
    achievements = []
    for row in rows:
        record = build_record(headers, row)
        achievement_id = first(record, "$id")
        if achievement_id is None:
            continue
        achievements.append({
            "id": str(achievement_id),
            "name": str(first(record, "name", achievement_id)),
            "description": str(first(record, "description", "")),
            "grade": first(record, "grade"),
            "condition": first(record, "condition"),
            "opportunity": first(record, "opportunity"),
            "source": "VickScarlet/lifeRestart MIT",
        })
    return achievements


def parse_characters(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    headers, rows = row_records(read_xlsx(path))
    characters = []
    for row in rows:
        record = build_record(headers, row)
        character_id = first(record, "$id")
        if character_id is None:
            continue
        properties = {}
        for key, values in record.items():
            if key.startswith("property:") and values:
                properties[key.split(":", 1)[1]] = normalize(values[0])
        characters.append({
            "id": str(character_id),
            "name": str(first(record, "name", character_id)),
            "properties": properties,
            "talents": [str(v) for v in record.get("talent[]", [])],
            "source": "VickScarlet/lifeRestart MIT",
        })
    return characters


def build_pack(source: Path, locale: str) -> dict[str, Any]:
    locale_dir = source / locale if (source / locale).exists() else source
    talents_path = locale_dir / "talents.xlsx"
    events_path = locale_dir / "events.xlsx"
    age_path = locale_dir / "age.xlsx"
    missing = [str(path) for path in [talents_path, events_path, age_path] if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required upstream xlsx files: " + ", ".join(missing))
    return {
        "version": 1,
        "id": f"liferestart-{locale}",
        "title": f"Life Restart upstream converted pack ({locale})",
        "license": "MIT; preserve references/lifeRestart-LICENSE.md and upstream attribution.",
        "source_repository": "https://github.com/VickScarlet/lifeRestart",
        "compatible_world_tags": ["classic", "upstream", "life-restart"],
        "attributes": {
            "CHR": "颜值 / charm",
            "INT": "智力 / intelligence",
            "STR": "体质 / strength",
            "MNY": "家境 / money",
            "SPR": "快乐 / spirit",
            "LUK": "运气 / luck"
        },
        "talents": parse_talents(talents_path),
        "events": parse_events(events_path),
        "age_pools": parse_age_pools(age_path),
        "achievements": parse_achievements(locale_dir / "achievement.xlsx"),
        "characters": parse_characters(locale_dir / "character.xlsx"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import VickScarlet/lifeRestart XLSX data as a Life Restart World content pack")
    parser.add_argument("--source", required=True, help="Path to upstream data directory or locale directory")
    parser.add_argument("--locale", default="zh-cn", help="Locale directory name when --source is the upstream data root")
    parser.add_argument("--output", required=True, help="Output JSON content pack path")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    pack = build_pack(source, args.locale)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"talents={len(pack['talents'])} events={len(pack['events'])} age_pools={len(pack['age_pools'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
