#!/usr/bin/env python3
"""Validate a Life Restart World LifeState v1 object.

This is a diagnostic helper, not a game engine. It checks the compact state
surface used by Live Play.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_KEYS = [
    "version",
    "age",
    "attrs",
    "talents",
    "flags",
    "event_history",
    "special_candidates",
    "terminal",
]

CORE_ATTRS = ["CHR", "INT", "STR", "MNY", "SPR", "LUK"]
STRING_LIST_KEYS = ["flags", "event_history", "special_candidates"]
LEGACY_STATE_KEYS = [
    "attributes",
    "relationships",
    "pressure_clocks",
    "evidence",
    "phase_summaries",
    "open_threads",
    "timeline",
    "life_cap",
    "existence_state",
    "realm",
    "terminal_reason",
]
LONG_LIFE_HINTS = (
    "cultivator",
    "immortal",
    "ascend",
    "ascension",
    "resurrected",
    "post_human",
    "long_life",
    "life_extended",
    "longevity",
    "飞升",
    "修仙",
    "复活",
    "长生",
    "不死",
)


def load_state(value: str) -> dict[str, Any]:
    if value == "-":
        return json.loads(sys.stdin.read())
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return json.loads(value)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def is_int_like(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def duplicate_values(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def check_string_list(value: Any, path: str, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return
    duplicates = duplicate_values(value)
    if duplicates:
        warnings.append(f"{path} contains duplicate values: {duplicates}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{index}] must be a nonempty string")


def talent_ids(talents: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(talents, list):
        return ids
    for talent in talents:
        if isinstance(talent, str):
            ids.add(talent)
        elif isinstance(talent, dict):
            for key in ["id", "name"]:
                if isinstance(talent.get(key), str) and talent[key].strip():
                    ids.add(talent[key])
                    break
    return ids


def has_long_life_explanation(state: dict[str, Any]) -> bool:
    surface = " ".join(
        [
            json.dumps(state.get("flags", []), ensure_ascii=False),
            json.dumps(state.get("event_history", []), ensure_ascii=False),
            json.dumps(state.get("talents", []), ensure_ascii=False),
        ]
    ).lower()
    return any(hint.lower() in surface for hint in LONG_LIFE_HINTS)


def check_terminal(value: Any, errors: list[str], warnings: list[str]) -> None:
    if value is False:
        return
    if value is True:
        warnings.append("terminal=true is accepted, but an object with kind/reason is more resumable")
        return
    if not isinstance(value, dict):
        errors.append("terminal must be false, true, or an object")
        return
    if value.get("ended") is not None and not isinstance(value["ended"], bool):
        errors.append("terminal.ended must be boolean when present")
    if value.get("kind") is not None and not isinstance(value["kind"], str):
        errors.append("terminal.kind must be a string when present")
    if not value.get("reason"):
        warnings.append("terminal.reason is empty")
    elif not isinstance(value["reason"], str):
        errors.append("terminal.reason must be a string")
    if value.get("event_id") is not None and not isinstance(value["event_id"], str):
        errors.append("terminal.event_id must be a string when present")


def validate(state: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(state, dict):
        return {"ok": False, "errors": ["state must be a JSON object"], "warnings": []}

    for key in REQUIRED_KEYS:
        if key not in state:
            errors.append(f"missing required key: {key}")

    for key in LEGACY_STATE_KEYS:
        if key in state:
            warnings.append(f"{key} is a legacy ledger field and is not part of LifeState v1")

    if "version" in state and not is_int_like(state["version"]):
        errors.append("version must be numeric")
    elif is_int_like(state.get("version")) and int(state["version"]) != 1:
        warnings.append(f"version={state['version']} is unusual; LifeState v1 expects version 1")

    if "age" in state:
        if not is_int_like(state["age"]):
            errors.append("age must be numeric")
        elif int(state["age"]) < 0:
            errors.append("age must be nonnegative")
        elif int(state["age"]) > 100 and state.get("terminal") is False and not has_long_life_explanation(state):
            warnings.append("age exceeds 100 while terminal is false; add flags/event_history that explain long-life play")

    attrs = state.get("attrs")
    if not isinstance(attrs, dict):
        errors.append("attrs must be an object")
    else:
        for attr in CORE_ATTRS:
            if attr not in attrs:
                errors.append(f"attrs.{attr} is missing")
            elif not is_int_like(attrs[attr]):
                errors.append(f"attrs.{attr} must be numeric")
            else:
                value = int(attrs[attr])
                if value < 0:
                    warnings.append(f"attrs.{attr}={value} is below ordinary range")
                if value > 10 and not has_long_life_explanation(state):
                    warnings.append(f"attrs.{attr}={value} is high for ordinary play; explain it through talents, flags, or story")
        for attr in attrs:
            if attr not in CORE_ATTRS:
                warnings.append(f"attrs.{attr} is not a LifeState v1 core attribute")

    for key in STRING_LIST_KEYS:
        if key in state:
            check_string_list(state[key], key, errors, warnings)

    talents = state.get("talents")
    if isinstance(talents, list):
        for index, talent in enumerate(talents):
            if isinstance(talent, str):
                if not talent.strip():
                    errors.append(f"talents[{index}] must be nonempty")
            elif isinstance(talent, dict):
                if not isinstance(talent.get("id"), str) or not talent.get("id", "").strip():
                    warnings.append(f"talents[{index}].id is missing")
                effects = talent.get("effects")
                if effects is not None and not isinstance(effects, dict):
                    errors.append(f"talents[{index}].effects must be an object when present")
            else:
                errors.append(f"talents[{index}] must be a string or object")

    history = set(state.get("event_history", [])) if isinstance(state.get("event_history"), list) else set()
    special = set(state.get("special_candidates", [])) if isinstance(state.get("special_candidates"), list) else set()
    repeated = sorted(history & special)
    if repeated:
        warnings.append(f"special_candidates already resolved in event_history: {repeated}")

    if isinstance(state.get("terminal"), dict):
        event_id = state["terminal"].get("event_id")
        if isinstance(event_id, str) and history and event_id not in history:
            warnings.append(f"terminal.event_id {event_id} is not in event_history")
    if "terminal" in state:
        check_terminal(state["terminal"], errors, warnings)

    if "session_id" in state and not isinstance(state["session_id"], str):
        errors.append("session_id must be a string when present")
    if "turn" in state and not is_int_like(state["turn"]):
        errors.append("turn must be numeric when present")
    if "notes" in state and not isinstance(state["notes"], str):
        errors.append("notes must be a string when present")
    if "next_actions" in state:
        actions = state["next_actions"]
        if not isinstance(actions, list):
            errors.append("next_actions must be a list when present")
        elif len(actions) < 2 or len(actions) > 4:
            warnings.append(f"next_actions has {len(actions)} entries; offer 2-4 only when useful")

    _ = talent_ids(talents)
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str]) -> int:
    usage = "Usage: validate_state.py [--fail-on-warnings] STATE_JSON_PATH_OR_INLINE_OR_-"
    args = argv[1:]
    if len(args) == 1 and args[0] in {"-h", "--help"}:
        print(usage)
        return 0
    fail_on_warnings = "--fail-on-warnings" in args
    args = [arg for arg in args if arg != "--fail-on-warnings"]
    if len(args) != 1:
        print(usage, file=sys.stderr)
        return 2
    try:
        state = load_state(args[0])
    except Exception as exc:  # noqa: BLE001 - diagnostic CLI.
        print(json.dumps({"ok": False, "errors": [f"could not load state: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        return 1
    result = validate(state)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        return 1
    if fail_on_warnings and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
