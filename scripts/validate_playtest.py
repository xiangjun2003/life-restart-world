#!/usr/bin/env python3
"""Validate a lightweight Live Play playtest transcript.

This is a developer QA helper. It checks for story-first output, free-form
action coverage, state snapshots that conform to LifeState v1, and exposed
script/content-pack problems. It does not require a strict turn transcript.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import validate_state


ALIASES = {
    "story_scene": ["story_scene", "scene", "prose", "narrative"],
    "actions": ["actions", "action_openings", "visible_actions", "choices"],
    "state": ["state", "post_state", "life_state"],
}


def load_transcript(value: str) -> dict[str, Any]:
    if value == "-":
        return json.loads(sys.stdin.read())
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return json.loads(value)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def first_field(obj: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in obj:
            return obj[name]
    return None


def has_text(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_text(item) for item in value)
    if isinstance(value, dict):
        return any(has_text(item) for item in value.values())
    return value is not None


def event_ids(turn: dict[str, Any]) -> list[str]:
    raw = turn.get("event_ids", turn.get("event_id", turn.get("events", [])))
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if isinstance(item, (str, int))]
    return []


def is_freeform(turn: dict[str, Any]) -> bool:
    source = str(turn.get("intent_source", turn.get("action_source", ""))).lower()
    if source == "freeform":
        return True
    action = str(turn.get("user_action", "")).strip()
    return bool(action and not action.startswith(("选", "choose", "select")))


def is_modified_entry(turn: dict[str, Any]) -> bool:
    source = str(turn.get("intent_source", turn.get("action_source", ""))).lower()
    if source == "modified_entry":
        return True
    action = str(turn.get("user_action", ""))
    return action.startswith("选") and any(marker in action for marker in ["但", "同时", "不过", "改成"])


def check_actions(turn: dict[str, Any], index: int, warnings: list[str]) -> bool:
    actions = first_field(turn, ALIASES["actions"])
    if actions is None:
        return False
    if not isinstance(actions, list):
        warnings.append(f"turns[{index}].actions should be a list when present")
        return False
    if len(actions) < 2 or len(actions) > 4:
        warnings.append(f"turns[{index}].actions has {len(actions)} entries; expected 2-4 when actions are shown")
    for action_index, action in enumerate(actions):
        if isinstance(action, str):
            if not action.strip():
                warnings.append(f"turns[{index}].actions[{action_index}] is empty")
        elif isinstance(action, dict):
            label = action.get("label") or action.get("text")
            if not isinstance(label, str) or not label.strip():
                warnings.append(f"turns[{index}].actions[{action_index}] lacks a label")
            if any(key in action for key in ["state_hooks", "targets", "risk", "checks"]):
                warnings.append(f"turns[{index}].actions[{action_index}] exposes internal affordance metadata")
        else:
            warnings.append(f"turns[{index}].actions[{action_index}] should be a string or label object")
    return bool(actions)


def check_state_object(value: Any, path: str, errors: list[str], warnings: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        warnings.append(f"{path} should be an object when present")
        return
    result = validate_state.validate(value)
    for error in result["errors"]:
        errors.append(f"{path}: {error}")
    for warning in result["warnings"]:
        warnings.append(f"{path}: {warning}")


def validate(transcript: dict[str, Any], *, min_turns: int = 0, min_freeform: int = 0, min_modified_entry: int = 0, forbid_raw_state: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(transcript, dict):
        return {"ok": False, "errors": ["playtest transcript must be a JSON object"], "warnings": [], "summary": {}}

    turns = transcript.get("turns")
    if not isinstance(turns, list):
        errors.append("turns must be a list")
        turns = []

    check_state_object(transcript.get("initial_state"), "initial_state", errors, warnings)
    check_state_object(transcript.get("final_state"), "final_state", errors, warnings)

    story_turns = 0
    action_turns = 0
    freeform_turns = 0
    modified_turns = 0
    raw_state_turns = 0
    manual_turns = 0
    special_candidate_turns = 0

    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            errors.append(f"turns[{index}] must be an object")
            continue
        story = first_field(turn, ALIASES["story_scene"])
        if has_text(story):
            story_turns += 1
        else:
            warnings.append(f"turns[{index}] has no story_scene/prose")

        if check_actions(turn, index, warnings):
            action_turns += 1

        if is_freeform(turn):
            freeform_turns += 1
        if is_modified_entry(turn):
            modified_turns += 1

        ids = event_ids(turn)
        if any(event_id.startswith("manual_") for event_id in ids):
            manual_turns += 1
        if not ids:
            warnings.append(f"turns[{index}] has no event_id/event_ids/manual_* note")

        if turn.get("raw_state_exposed") is True:
            raw_state_turns += 1
            if forbid_raw_state and not turn.get("raw_state_requested"):
                warnings.append(f"turns[{index}] exposes raw state during ordinary play")

        state = first_field(turn, ALIASES["state"])
        check_state_object(state, f"turns[{index}].state", errors, warnings)

        before = turn.get("special_candidates_before")
        after = turn.get("special_candidates_after")
        if before is not None or after is not None:
            special_candidate_turns += 1
            if not isinstance(before, list) and before is not None:
                warnings.append(f"turns[{index}].special_candidates_before should be a list")
            if not isinstance(after, list) and after is not None:
                warnings.append(f"turns[{index}].special_candidates_after should be a list")

    if len(turns) < min_turns:
        warnings.append(f"playtest has {len(turns)} turns; expected at least {min_turns}")
    if freeform_turns < min_freeform:
        warnings.append(f"playtest has {freeform_turns} free-form turns; expected at least {min_freeform}")
    if modified_turns < min_modified_entry:
        warnings.append(f"playtest has {modified_turns} modified-entry turns; expected at least {min_modified_entry}")

    summary = {
        "turns": len(turns),
        "story_turns": story_turns,
        "action_turns": action_turns,
        "freeform_turns": freeform_turns,
        "modified_entry_turns": modified_turns,
        "manual_turns": manual_turns,
        "special_candidate_turns": special_candidate_turns,
        "raw_state_turns": raw_state_turns,
    }
    return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": summary}


def parse_args(argv: list[str]) -> tuple[dict[str, Any], bool, dict[str, int | bool]]:
    usage = (
        "Usage: validate_playtest.py [--fail-on-warnings] [--min-turns N] "
        "[--min-freeform N] [--min-modified-entry N] [--forbid-raw-state] "
        "PLAYTEST_JSON_PATH_OR_INLINE_OR_-"
    )
    args = argv[1:]
    if len(args) == 1 and args[0] in {"-h", "--help"}:
        print(usage)
        raise SystemExit(0)
    fail_on_warnings = "--fail-on-warnings" in args
    forbid_raw_state = "--forbid-raw-state" in args
    args = [arg for arg in args if arg not in {"--fail-on-warnings", "--forbid-raw-state"}]

    values: dict[str, int | bool] = {
        "min_turns": 0,
        "min_freeform": 0,
        "min_modified_entry": 0,
        "forbid_raw_state": forbid_raw_state,
    }
    ignored_with_value = {
        "--min-landed-deltas",
        "--min-visible-snapshots",
        "--min-story-scenes",
        "--min-visible-deltas",
        "--min-visible-actions",
        "--min-freeform-reminders",
        "--max-age-jump",
        "--max-age-span",
        "--min-same-age-turns",
    }
    index = 0
    remaining: list[str] = []
    while index < len(args):
        arg = args[index]
        if arg in {"--min-turns", "--min-freeform", "--min-modified-entry"}:
            if index + 1 >= len(args):
                print(usage, file=sys.stderr)
                raise SystemExit(2)
            try:
                value = int(args[index + 1])
            except ValueError:
                print(usage, file=sys.stderr)
                raise SystemExit(2)
            key = arg[2:].replace("-", "_")
            values[key] = value
            index += 2
            continue
        if arg in ignored_with_value:
            index += 2
            continue
        if arg == "--forbid-age-regression":
            index += 1
            continue
        remaining.append(arg)
        index += 1

    if len(remaining) != 1:
        print(usage, file=sys.stderr)
        raise SystemExit(2)
    try:
        transcript = load_transcript(remaining[0])
    except Exception as exc:  # noqa: BLE001 - diagnostic CLI.
        print(json.dumps({"ok": False, "errors": [f"could not load playtest: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    return transcript, fail_on_warnings, values


def main(argv: list[str]) -> int:
    transcript, fail_on_warnings, values = parse_args(argv)
    result = validate(
        transcript,
        min_turns=int(values["min_turns"]),
        min_freeform=int(values["min_freeform"]),
        min_modified_entry=int(values["min_modified_entry"]),
        forbid_raw_state=bool(values["forbid_raw_state"]),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        return 1
    if fail_on_warnings and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
