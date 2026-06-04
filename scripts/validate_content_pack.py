#!/usr/bin/env python3
"""Validate a Life Restart World content pack.

This is a diagnostic helper, not a game engine. It checks for pack integrity
problems that would quietly break state-led hosting, such as duplicate event
IDs, missing age-pool references, or malformed evidence holders.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = [
    "version",
    "id",
    "title",
    "compatible_realms",
    "compatible_world_tags",
    "attributes",
    "talents",
    "events",
    "age_pools",
]

LIST_KEYS = [
    "tags",
    "choices",
    "set_flags",
    "clear_flags",
    "open_threads",
    "close_threads",
]

NUMERIC_EVENT_KEYS = {"weight", "life_cap"}
STRING_EVENT_KEYS = {"realm", "existence_state", "realm_transition", "terminal_reason", "narrative_seed", "age_advance"}
BOOLEAN_EVENT_KEYS = {"repeatable", "terminal", "clear_terminal"}
EVIDENCE_RISKS = {"low", "medium", "high", "critical"}
AGE_POOL_RE = re.compile(r"^\d+(?:-\d+)?$")


def load_pack(value: str) -> dict[str, Any]:
    if value == "-":
        return json.loads(sys.stdin.read())
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return json.loads(value)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def duplicate_values(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


def check_unique_objects(items: Any, label: str, errors: list[str], warnings: list[str]) -> set[str]:
    ids: set[str] = set()
    seen: set[str] = set()
    singular = label[:-1] if label.endswith("s") else label
    if not isinstance(items, list):
        errors.append(f"{label} must be a list")
        return ids
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] must be an object")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            errors.append(f"{label}[{index}].id must be a nonempty string")
            continue
        ids.add(item_id)
        if item_id in seen:
            errors.append(f"duplicate {singular} id: {item_id}")
        seen.add(item_id)
    return ids


def check_string_list(value: Any, path: str, errors: list[str], warnings: list[str], required: bool = False) -> None:
    if value is None:
        if required:
            errors.append(f"{path} must be a list")
        return
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return
    duplicates = duplicate_values(value)
    if duplicates:
        warnings.append(f"{path} contains duplicate values: {duplicates}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{index}] must be a nonempty string")


def check_age(event: dict[str, Any], path: str, warnings: list[str], errors: list[str]) -> None:
    if "age" not in event and "age_range" not in event:
        return
    if "age" in event:
        age = event["age"]
        if age is not None and not is_number(age):
            errors.append(f"{path}.age must be numeric or null")
        elif is_number(age) and age < 0:
            errors.append(f"{path}.age must be nonnegative")
    if "age_range" in event:
        value = event["age_range"]
        if not isinstance(value, list) or len(value) != 2 or not all(is_number(part) for part in value):
            errors.append(f"{path}.age_range must be [start, end]")
        elif value[0] < 0 or value[1] < 0 or value[0] > value[1]:
            errors.append(f"{path}.age_range must be nonnegative and ordered")


def check_effects(value: Any, path: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for key, delta in value.items():
        if not isinstance(key, str) or not key:
            errors.append(f"{path} keys must be nonempty strings")
        if not is_number(delta):
            errors.append(f"{path}.{key} must be numeric")


def check_relationships(value: Any, path: str, errors: list[str], warnings: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for rel_id, update in value.items():
        item_path = f"{path}.{rel_id}"
        if not isinstance(update, dict):
            errors.append(f"{item_path} must be an object")
            continue
        if "delta" in update and not is_number(update["delta"]):
            errors.append(f"{item_path}.delta must be numeric")
        if "score" in update and not is_number(update["score"]):
            errors.append(f"{item_path}.score must be numeric")
        if "delta" not in update and "score" not in update:
            warnings.append(f"{item_path} should include delta or score")
        if "note" in update and not isinstance(update["note"], str):
            errors.append(f"{item_path}.note must be a string when present")


def check_pressure_clocks(value: Any, path: str, errors: list[str], warnings: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for clock_id, update in value.items():
        item_path = f"{path}.{clock_id}"
        if not isinstance(update, dict):
            errors.append(f"{item_path} must be an object")
            continue
        if update.get("close") is not None and not isinstance(update["close"], bool):
            errors.append(f"{item_path}.close must be boolean when present")
        for key in ["delta", "set_stage", "limit"]:
            if key in update and not is_number(update[key]):
                errors.append(f"{item_path}.{key} must be numeric")
        if is_number(update.get("limit")) and update["limit"] <= 0:
            errors.append(f"{item_path}.limit must be positive")
        if any(key in update for key in ["delta", "set_stage", "limit"]) and not update.get("meaning"):
            warnings.append(f"{item_path}.meaning is empty")
        if "meaning" in update and not isinstance(update["meaning"], str):
            errors.append(f"{item_path}.meaning must be a string when present")


def check_evidence(value: Any, path: str, errors: list[str], warnings: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for evidence_id, update in value.items():
        item_path = f"{path}.{evidence_id}"
        if not isinstance(update, dict):
            errors.append(f"{item_path} must be an object")
            continue
        if not update.get("claim") and not update.get("status"):
            warnings.append(f"{item_path} should include claim or status")
        holders = update.get("holders")
        if holders is None:
            warnings.append(f"{item_path}.holders is missing")
        elif not isinstance(holders, list):
            errors.append(f"{item_path}.holders must be a list when present")
        else:
            check_string_list(holders, f"{item_path}.holders", errors, warnings)
            if not holders:
                warnings.append(f"{item_path}.holders is empty")
        if update.get("risk") and str(update["risk"]) not in EVIDENCE_RISKS:
            warnings.append(f"{item_path}.risk is unusual: {update['risk']}")


def check_event(event: dict[str, Any], path: str, errors: list[str], warnings: list[str]) -> None:
    for key in ["id", "title"]:
        if not isinstance(event.get(key), str) or not event.get(key, "").strip():
            errors.append(f"{path}.{key} must be a nonempty string")
    check_age(event, path, warnings, errors)
    for key in LIST_KEYS:
        check_string_list(event.get(key), f"{path}.{key}", errors, warnings, required=(key == "tags"))
    choices = event.get("choices")
    if choices is None:
        warnings.append(f"{path}.choices is missing; the Game Master must generate affordances")
    elif isinstance(choices, list) and (len(choices) < 2 or len(choices) > 4):
        warnings.append(f"{path}.choices has {len(choices)} entries; hosted turns should usually offer 2-4 affordances")
    if not event.get("narrative_seed"):
        warnings.append(f"{path}.narrative_seed is empty")
    for key in NUMERIC_EVENT_KEYS:
        if key in event:
            if not is_number(event[key]):
                errors.append(f"{path}.{key} must be numeric")
            elif key == "weight" and event[key] <= 0:
                warnings.append(f"{path}.weight should be positive")
            elif key == "life_cap" and event[key] <= 0:
                errors.append(f"{path}.life_cap must be positive")
    for key in STRING_EVENT_KEYS:
        if key in event and not isinstance(event[key], str):
            errors.append(f"{path}.{key} must be a string when present")
    for key in BOOLEAN_EVENT_KEYS:
        if key in event and not isinstance(event[key], bool):
            errors.append(f"{path}.{key} must be boolean when present")
    if event.get("terminal") is True and not event.get("terminal_reason"):
        warnings.append(f"{path} is terminal but terminal_reason is empty")
    check_effects(event.get("effects"), f"{path}.effects", errors)
    check_relationships(event.get("relationships"), f"{path}.relationships", errors, warnings)
    check_pressure_clocks(event.get("pressure_clocks"), f"{path}.pressure_clocks", errors, warnings)
    check_evidence(event.get("evidence"), f"{path}.evidence", errors, warnings)
    if "branches" in event and not isinstance(event["branches"], list):
        errors.append(f"{path}.branches must be a list when present")


def check_talent(talent: dict[str, Any], path: str, errors: list[str], warnings: list[str]) -> None:
    for key in ["id", "name", "description"]:
        if key in talent and not isinstance(talent[key], str):
            errors.append(f"{path}.{key} must be a string when present")
    if "grade" in talent and not is_number(talent["grade"]):
        errors.append(f"{path}.grade must be numeric when present")
    check_effects(talent.get("effects"), f"{path}.effects", errors)
    check_string_list(talent.get("tags"), f"{path}.tags", errors, warnings)
    check_string_list(talent.get("exclude"), f"{path}.exclude", errors, warnings)
    if not talent.get("name"):
        warnings.append(f"{path}.name is empty")
    if not talent.get("description"):
        warnings.append(f"{path}.description is empty")


def check_age_pools(value: Any, event_ids: set[str], errors: list[str], warnings: list[str]) -> set[str]:
    referenced: set[str] = set()
    if not isinstance(value, dict):
        errors.append("age_pools must be an object")
        return referenced
    for pool_id, entries in value.items():
        path = f"age_pools.{pool_id}"
        if not isinstance(pool_id, str) or not AGE_POOL_RE.match(pool_id):
            warnings.append(f"{path} is an unusual age key; prefer an age or age range such as 12 or 80-120")
        if not isinstance(entries, list):
            errors.append(f"{path} must be a list")
            continue
        pool_event_ids: list[Any] = []
        for index, entry in enumerate(entries):
            item_path = f"{path}[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{item_path} must be an object")
                continue
            event_id = entry.get("event_id")
            if not isinstance(event_id, str) or not event_id.strip():
                errors.append(f"{item_path}.event_id must be a nonempty string")
                continue
            pool_event_ids.append(event_id)
            referenced.add(event_id)
            if event_id not in event_ids:
                errors.append(f"{item_path}.event_id references missing event: {event_id}")
            if "weight" in entry:
                if not is_number(entry["weight"]):
                    errors.append(f"{item_path}.weight must be numeric")
                elif entry["weight"] <= 0:
                    warnings.append(f"{item_path}.weight should be positive")
        duplicates = duplicate_values(pool_event_ids)
        if duplicates:
            warnings.append(f"{path} contains duplicate event references: {duplicates}")
    return referenced


def validate(pack: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(pack, dict):
        return {"ok": False, "errors": ["content pack must be a JSON object"], "warnings": []}

    for key in REQUIRED_TOP_LEVEL:
        if key not in pack:
            errors.append(f"missing required key: {key}")
    if "version" in pack and not is_number(pack["version"]):
        errors.append("version must be numeric")
    for key in ["id", "title"]:
        if key in pack and (not isinstance(pack[key], str) or not pack[key].strip()):
            errors.append(f"{key} must be a nonempty string")
    for key in ["compatible_realms", "compatible_world_tags"]:
        check_string_list(pack.get(key), key, errors, warnings, required=True)
    if not isinstance(pack.get("attributes"), dict):
        errors.append("attributes must be an object")

    talent_ids = check_unique_objects(pack.get("talents"), "talents", errors, warnings)
    event_ids = check_unique_objects(pack.get("events"), "events", errors, warnings)

    if isinstance(pack.get("talents"), list):
        for index, talent in enumerate(pack["talents"]):
            if isinstance(talent, dict):
                check_talent(talent, f"talents[{index}]", errors, warnings)

    events = pack.get("events")
    if isinstance(events, list):
        for index, event in enumerate(events):
            if isinstance(event, dict):
                check_event(event, f"events[{index}]", errors, warnings)

    referenced_event_ids = check_age_pools(pack.get("age_pools"), event_ids, errors, warnings)
    unreferenced = sorted(event_ids - referenced_event_ids)
    for event_id in unreferenced:
        event = next((item for item in events if isinstance(item, dict) and item.get("id") == event_id), None) if isinstance(events, list) else None
        if event and ("age" in event or "age_range" in event):
            warnings.append(f"events.{event_id} has age data but is not referenced by age_pools")
        elif event:
            warnings.append(f"events.{event_id} has neither age data nor age_pool reference")

    if "achievements" in pack:
        if isinstance(pack.get("achievements"), list):
            check_unique_objects(pack["achievements"], "achievements", errors, warnings)
        else:
            errors.append("achievements must be a list when present")
    if "characters" in pack:
        if isinstance(pack.get("characters"), list):
            check_unique_objects(pack["characters"], "characters", errors, warnings)
        else:
            errors.append("characters must be a list when present")
    if isinstance(pack.get("characters"), list):
        for character in pack["characters"]:
            if isinstance(character, dict):
                talents = character.get("talents", [])
                check_string_list(talents, f"characters.{character.get('id')}.talents", errors, warnings)
                if isinstance(talents, list):
                    for talent_id in talents:
                        if talent_id not in talent_ids:
                            warnings.append(f"characters.{character.get('id')}.talents references unknown talent: {talent_id}")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_content_pack.py PACK_JSON_PATH_OR_INLINE_OR_-", file=sys.stderr)
        return 2
    try:
        pack = load_pack(argv[1])
    except Exception as exc:  # noqa: BLE001 - this is a CLI diagnostic helper.
        print(json.dumps({"ok": False, "errors": [f"could not load content pack: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        return 1
    result = validate(pack)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
