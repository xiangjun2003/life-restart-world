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
LIST_KEYS = ["talents", "flags", "event_history", "open_threads", "timeline"]
EVIDENCE_RISKS = {"low", "medium", "high", "critical"}
PRESSURE_STATUSES = {"active", "filled", "resolved", "closed"}
PROLOGUE_EXCEPTION_FLAGS = {"amnesia", "missing_records", "artificial_creation", "newly_created", "memory_erased", "unknown_past"}


def has_attribute_note(state: dict[str, Any], attr: str) -> bool:
    notes = state.get("attribute_notes")
    if not isinstance(notes, dict):
        return False
    note = notes.get(attr)
    if isinstance(note, str):
        return bool(note.strip())
    if isinstance(note, dict):
        return bool(note.get("note") or note.get("reason") or note.get("future_delta_policy"))
    return False


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


def int_or_none(value: Any) -> int | None:
    if not is_int_like(value):
        return None
    return int(value)


def check_list(state: dict[str, Any], key: str, errors: list[str]) -> None:
    if not isinstance(state.get(key), list):
        errors.append(f"{key} must be a list")


def duplicate_values(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def parse_timeline_event_ids(value: Any) -> set[str]:
    if isinstance(value, list):
        values = value
    elif value:
        values = [value]
    else:
        values = []
    ids: set[str] = set()
    for item in values:
        for part in str(item).split("+"):
            event_id = part.strip()
            if event_id:
                ids.add(event_id)
    return ids


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
        if clock.get("status") and str(clock["status"]) not in PRESSURE_STATUSES:
            warnings.append(f"pressure_clocks.{clock_id}.status is unusual: {clock['status']}")
        if not clock.get("meaning"):
            warnings.append(f"pressure_clocks.{clock_id}.meaning is empty")


def check_optional_extensions(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if "time" in state and not isinstance(state["time"], (str, dict)):
        errors.append("time must be a string or object when present")
    attribute_notes = state.get("attribute_notes")
    if attribute_notes is not None:
        if not isinstance(attribute_notes, dict):
            errors.append("attribute_notes must be an object when present")
        else:
            for attr, note in attribute_notes.items():
                if attr not in ATTRIBUTES:
                    warnings.append(f"attribute_notes.{attr} does not match a known attribute")
                if isinstance(note, str):
                    if not note.strip():
                        warnings.append(f"attribute_notes.{attr} is empty")
                elif isinstance(note, dict):
                    if not note.get("note") and not note.get("reason") and not note.get("future_delta_policy"):
                        warnings.append(f"attribute_notes.{attr} should include note, reason, or future_delta_policy")
                else:
                    errors.append(f"attribute_notes.{attr} must be a string or object")
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
                elif not holders:
                    warnings.append(f"evidence.{item_id}.holders is empty")
                if item.get("risk") and str(item["risk"]) not in EVIDENCE_RISKS:
                    warnings.append(f"evidence.{item_id}.risk is unusual: {item['risk']}")
    relationships = state.get("relationships")
    if isinstance(relationships, dict):
        for name, entry in relationships.items():
            if isinstance(entry, dict) and "tensions" in entry and not isinstance(entry["tensions"], list):
                errors.append(f"relationships.{name}.tensions must be a list when present")
    phase_summaries = state.get("phase_summaries")
    if phase_summaries is not None:
        if not isinstance(phase_summaries, list):
            errors.append("phase_summaries must be a list when present")
        else:
            for index, item in enumerate(phase_summaries):
                if not isinstance(item, dict):
                    errors.append(f"phase_summaries[{index}] must be an object")
                    continue
                if not item.get("summary") and not item.get("title"):
                    warnings.append(f"phase_summaries[{index}] should include summary or title")
                if "age" not in item and "time" not in item:
                    warnings.append(f"phase_summaries[{index}] should include age or time")
                for key in ["closed_threads", "carried_threads", "outcomes"]:
                    if key in item and not isinstance(item[key], list):
                        errors.append(f"phase_summaries[{index}].{key} must be a list when present")


def check_string_list_value(value: Any, path: str, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list when present")
        return
    duplicates = duplicate_values(value)
    if duplicates:
        warnings.append(f"{path} contains duplicate values: {duplicates}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{index}] must be a nonempty string")


def check_phase_summary_consistency(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    phase_summaries = state.get("phase_summaries")
    if not isinstance(phase_summaries, list):
        return
    open_threads = {str(item) for item in state.get("open_threads", [])} if isinstance(state.get("open_threads"), list) else set()
    seen_ids: set[str] = set()
    for index, item in enumerate(phase_summaries):
        if not isinstance(item, dict):
            continue
        summary_id = item.get("id")
        if summary_id is None:
            warnings.append(f"phase_summaries[{index}].id is missing")
        elif not isinstance(summary_id, str) or not summary_id.strip():
            errors.append(f"phase_summaries[{index}].id must be a nonempty string when present")
        elif summary_id in seen_ids:
            warnings.append(f"phase_summaries contains duplicate id: {summary_id}")
        elif summary_id:
            seen_ids.add(summary_id)

        for key in ["closed_threads", "carried_threads", "outcomes"]:
            if key in item and isinstance(item[key], list):
                check_string_list_value(item[key], f"phase_summaries[{index}].{key}", errors, warnings)

        closed = {str(thread) for thread in item.get("closed_threads", []) if isinstance(thread, str)}
        carried = {str(thread) for thread in item.get("carried_threads", []) if isinstance(thread, str)}
        overlap = sorted(closed & carried)
        if overlap:
            warnings.append(f"phase_summaries[{index}] closes and carries the same threads: {overlap}")
        still_open = sorted(closed & open_threads)
        if still_open:
            warnings.append(f"phase_summaries[{index}].closed_threads still appear in open_threads: {still_open}")
        if "next_phase" in item and not isinstance(item["next_phase"], str):
            errors.append(f"phase_summaries[{index}].next_phase must be a string when present")


def check_session_note_pressure_clocks(state: dict[str, Any], note: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    clocks = note.get("pressure_clocks")
    if clocks is None:
        return
    if not isinstance(clocks, dict):
        errors.append("world.session_note.pressure_clocks must be an object when present")
        return
    state_clocks = state.get("pressure_clocks")
    state_clock_ids = set(state_clocks) if isinstance(state_clocks, dict) else set()
    for clock_id, clock in clocks.items():
        path = f"world.session_note.pressure_clocks.{clock_id}"
        if not isinstance(clock, dict):
            errors.append(f"{path} must be an object")
            continue
        for key in ["stage", "limit"]:
            if key in clock and not is_int_like(clock[key]):
                errors.append(f"{path}.{key} must be numeric")
        if is_int_like(clock.get("limit")) and int(clock["limit"]) <= 0:
            errors.append(f"{path}.limit must be positive")
        if not clock.get("meaning"):
            warnings.append(f"{path}.meaning is empty")
        if "on_fill" in clock and not isinstance(clock["on_fill"], str):
            errors.append(f"{path}.on_fill must be a string when present")
        if clock_id not in state_clock_ids:
            warnings.append(f"{path} is not mirrored in state.pressure_clocks; active pressure belongs in the ledger")


def check_world(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    world = state.get("world")
    if not isinstance(world, dict):
        errors.append("world must be an object")
        return

    for key in ["style", "premise", "content_pack"]:
        if key in world and not isinstance(world[key], str):
            errors.append(f"world.{key} must be a string when present")
    if not world.get("premise"):
        warnings.append("world.premise is empty")

    session_note = world.get("session_note")
    if session_note is None:
        if not world.get("content_pack"):
            warnings.append("custom or no-pack world should include world.session_note")
        return
    if not isinstance(session_note, dict):
        errors.append("world.session_note must be an object when present")
        return

    for key in ["premise", "tone", "scale"]:
        if key in session_note and not isinstance(session_note[key], str):
            errors.append(f"world.session_note.{key} must be a string when present")

    for key in ["boundaries", "state_axes", "evidence_tracks", "event_seeds", "likely_choices", "terminal_paths"]:
        if key in session_note:
            check_string_list_value(session_note[key], f"world.session_note.{key}", errors, warnings)

    factions = session_note.get("factions")
    if factions is not None:
        if not isinstance(factions, dict):
            errors.append("world.session_note.factions must be an object when present")
        else:
            for faction_id, faction in factions.items():
                if not isinstance(faction_id, str) or not faction_id.strip():
                    errors.append("world.session_note.factions keys must be nonempty strings")
                if not isinstance(faction, (str, dict)):
                    errors.append(f"world.session_note.factions.{faction_id} must be a string or object")

    check_session_note_pressure_clocks(state, session_note, errors, warnings)

    if not world.get("content_pack"):
        if not session_note.get("state_axes"):
            warnings.append("custom or no-pack world.session_note.state_axes is empty")
        if not session_note.get("factions"):
            warnings.append("custom or no-pack world.session_note.factions is empty")


def check_timeline_and_history(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    timeline = state.get("timeline")
    history = state.get("event_history")
    if not isinstance(timeline, list) or not isinstance(history, list):
        return
    turn = int_or_none(state.get("turn")) or 0
    age = int_or_none(state.get("age")) or 0
    flags = {str(item) for item in state.get("flags", [])} if isinstance(state.get("flags"), list) else set()
    if age > 0 and not timeline and not flags.intersection(PROLOGUE_EXCEPTION_FLAGS):
        warnings.append("later-age state has empty timeline; add a compressed prologue or an explicit missing-records flag")
    if turn > 0 and not timeline:
        warnings.append("timeline is empty after play has advanced")
    if turn > 0 and not history:
        warnings.append("event_history is empty after play has advanced")

    timeline_ids: set[str] = set()
    playable_same_age_turns: dict[int, int] = {}
    same_age_missing_time: dict[int, list[int]] = {}
    for index, item in enumerate(timeline):
        if not isinstance(item, dict):
            errors.append(f"timeline[{index}] must be an object")
            continue
        turn_value = item.get("turn")
        event_ids = parse_timeline_event_ids(item.get("event_id"))
        if not event_ids:
            warnings.append(f"timeline[{index}].event_id is empty")
        else:
            timeline_ids.update(event_ids)
        if not item.get("summary") and not item.get("title") and not item.get("action"):
            warnings.append(f"timeline[{index}] should include summary, title, or action")
        if "age" not in item and "time" not in item:
            warnings.append(f"timeline[{index}] should include age or time")
        if isinstance(turn_value, int) and is_int_like(item.get("age")):
            age = int(item["age"])
            playable_same_age_turns[age] = playable_same_age_turns.get(age, 0) + 1
            if "time" not in item:
                same_age_missing_time.setdefault(age, []).append(index)

    history_ids = {str(item) for item in history}
    for event_id in sorted(history_ids - timeline_ids):
        warnings.append(f"event_history.{event_id} has no matching timeline item")
    for event_id in sorted(timeline_ids - history_ids):
        warnings.append(f"timeline event {event_id} is missing from event_history")

    for age, count in sorted(playable_same_age_turns.items()):
        if count > 1 and "time" not in state:
            warnings.append(f"multiple playable turns share age {age}; add state.time to preserve sequence")
        missing = same_age_missing_time.get(age, [])
        if count > 1 and missing:
            warnings.append(f"timeline items for repeated age {age} should include time: indexes {missing}")

    manual_ids = [event_id for event_id in history_ids if event_id.startswith("manual_")]
    for event_id in manual_ids:
        if event_id not in timeline_ids:
            warnings.append(f"manual event {event_id} should have a timeline item")


def check_ledger_density(state: dict[str, Any], warnings: list[str]) -> None:
    for key in ["flags", "open_threads"]:
        values = state.get(key)
        if isinstance(values, list):
            duplicates = duplicate_values(values)
            if duplicates:
                warnings.append(f"{key} contains duplicate values: {duplicates}")
    open_threads = state.get("open_threads")
    if isinstance(open_threads, list) and len(open_threads) > 8:
        warnings.append(f"open_threads has more than 8 items ({len(open_threads)}): {open_threads}; close stale threads or summarize them")
    relationships = state.get("relationships")
    if isinstance(relationships, dict) and len(relationships) > 8:
        warnings.append(f"relationships has more than 8 entries ({len(relationships)}): {sorted(relationships)}; keep only active relationships in the snapshot")
    if state.get("terminal") is True and isinstance(open_threads, list) and len(open_threads) > 3:
        warnings.append(f"terminal state still has many open_threads ({len(open_threads)}): {open_threads}; close or summarize resolved threads")


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

    existence_state = str(state.get("existence_state", "mortal"))
    attrs = state.get("attributes")
    if not isinstance(attrs, dict):
        errors.append("attributes must be an object")
    else:
        for attr in ATTRIBUTES:
            if attr not in attrs:
                errors.append(f"attributes.{attr} is missing")
            elif not is_int_like(attrs[attr]):
                errors.append(f"attributes.{attr} must be numeric")
            else:
                value = int(attrs[attr])
                if existence_state in {"mortal", "resurrected"} and (value < 0 or value > 12) and not has_attribute_note(state, attr):
                    warnings.append(f"attributes.{attr}={value} is outside the ordinary human range; explain it or clamp future deltas")

    check_world(state, errors, warnings)
    for key in LIST_KEYS:
        check_list(state, key, errors)

    check_relationships(state, errors, warnings)
    check_pressure_clocks(state, errors, warnings)
    check_optional_extensions(state, errors, warnings)
    check_phase_summary_consistency(state, errors, warnings)
    check_timeline_and_history(state, errors, warnings)
    check_ledger_density(state, warnings)

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
