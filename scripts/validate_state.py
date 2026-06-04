#!/usr/bin/env python3
"""Validate a Life Restart World state ledger.

This is a diagnostic helper, not a game engine. It checks that a hosted state is
structured enough for the next turn to continue without reconstructing facts
from prose.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_KEYS = [
    "version",
    "session_id",
    "turn",
    "pace",
    "age",
    "life_cap",
    "existence_state",
    "realm",
    "world",
    "attributes",
    "talents",
    "relationships",
    "pressure_clocks",
    "flags",
    "event_history",
    "open_threads",
    "timeline",
    "terminal",
    "terminal_reason",
]

ATTRIBUTES = ["CHR", "INT", "STR", "MNY", "SPR", "LUK", "WIL"]


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


def check_list(state: dict[str, Any], key: str, errors: list[str]) -> None:
    if not isinstance(state.get(key), list):
        errors.append(f"{key} must be a list")


def check_relationships(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    relationships = state.get("relationships")
    if not isinstance(relationships, dict):
        errors.append("relationships must be an object")
        return
    for name, entry in relationships.items():
        if isinstance(entry, dict):
            score = entry.get("score")
            if score is None:
                errors.append(f"relationships.{name}.score is missing")
                continue
            note = entry.get("note")
        else:
            score = entry
            note = None
        if not is_int_like(score):
            errors.append(f"relationships.{name}.score must be numeric")
            continue
        value = int(score)
        if value < -5 or value > 5:
            errors.append(f"relationships.{name}.score must be between -5 and 5")
        if isinstance(entry, dict) and not note:
            warnings.append(f"relationships.{name}.note is empty")


def check_pressure_clocks(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    clocks = state.get("pressure_clocks")
    if not isinstance(clocks, dict):
        errors.append("pressure_clocks must be an object")
        return
    for clock_id, clock in clocks.items():
        if not isinstance(clock, dict):
            errors.append(f"pressure_clocks.{clock_id} must be an object")
            continue
        if not is_int_like(clock.get("stage")):
            errors.append(f"pressure_clocks.{clock_id}.stage must be numeric")
            continue
        stage = int(clock["stage"])
        limit = clock.get("limit")
        if limit is not None and not is_int_like(limit):
            errors.append(f"pressure_clocks.{clock_id}.limit must be numeric")
            continue
        if limit is not None:
            limit_value = int(limit)
            if limit_value <= 0:
                errors.append(f"pressure_clocks.{clock_id}.limit must be positive")
            if stage < 0 or stage > limit_value:
                errors.append(f"pressure_clocks.{clock_id}.stage must be between 0 and limit")
            if stage == limit_value and not clock.get("last_consequence") and clock.get("status") not in {"filled", "resolved"}:
                warnings.append(f"pressure_clocks.{clock_id} is filled; record a consequence, status, or resolve it")
        elif stage < 0:
            errors.append(f"pressure_clocks.{clock_id}.stage must be nonnegative")
        if not clock.get("meaning"):
            warnings.append(f"pressure_clocks.{clock_id}.meaning is empty")


def check_optional_extensions(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if "time" in state and not isinstance(state["time"], (str, dict)):
        errors.append("time must be a string or object when present")
    evidence = state.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, dict):
            errors.append("evidence must be an object when present")
        else:
            for item_id, item in evidence.items():
                if not isinstance(item, dict):
                    errors.append(f"evidence.{item_id} must be an object")
                    continue
                if not item.get("claim") and not item.get("status"):
                    warnings.append(f"evidence.{item_id} should include claim or status")
                holders = item.get("holders")
                if holders is not None and not isinstance(holders, list):
                    errors.append(f"evidence.{item_id}.holders must be a list when present")
    relationships = state.get("relationships")
    if isinstance(relationships, dict):
        for name, entry in relationships.items():
            if isinstance(entry, dict) and "tensions" in entry and not isinstance(entry["tensions"], list):
                errors.append(f"relationships.{name}.tensions must be a list when present")


def validate(state: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_KEYS:
        if key not in state:
            errors.append(f"missing required key: {key}")

    for key in ["turn", "age", "life_cap"]:
        if key in state and not is_int_like(state.get(key)):
            errors.append(f"{key} must be numeric")

    if isinstance(state.get("age"), int) and state["age"] < 0:
        errors.append("age must be nonnegative")
    if isinstance(state.get("life_cap"), int) and state["life_cap"] <= 0:
        errors.append("life_cap must be positive")
    if "terminal" in state and not isinstance(state.get("terminal"), bool):
        errors.append("terminal must be a boolean")

    attrs = state.get("attributes")
    if not isinstance(attrs, dict):
        errors.append("attributes must be an object")
    else:
        for attr in ATTRIBUTES:
            if attr not in attrs:
                errors.append(f"attributes.{attr} is missing")
            elif not is_int_like(attrs[attr]):
                errors.append(f"attributes.{attr} must be numeric")

    if not isinstance(state.get("world"), dict):
        errors.append("world must be an object")
    for key in ["talents", "flags", "event_history", "open_threads", "timeline"]:
        check_list(state, key, errors)

    check_relationships(state, errors, warnings)
    check_pressure_clocks(state, errors, warnings)
    check_optional_extensions(state, errors, warnings)

    if state.get("terminal") is False and state.get("terminal_reason"):
        warnings.append("terminal_reason is set while terminal is false")
    if state.get("terminal") is True and not state.get("terminal_reason"):
        warnings.append("terminal is true but terminal_reason is empty")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_state.py STATE_JSON_PATH_OR_INLINE_OR_-", file=sys.stderr)
        return 2
    try:
        state = load_state(argv[1])
    except Exception as exc:  # noqa: BLE001 - this is a CLI diagnostic helper.
        print(json.dumps({"ok": False, "errors": [f"could not load state: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        return 1
    result = validate(state)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
