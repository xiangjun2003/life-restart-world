#!/usr/bin/env python3
"""Validate a Life Restart World playtest transcript.

This is a diagnostic harness, not a game engine. It checks whether a recorded
playtest contains enough evidence to prove that natural-language turns updated
the protagonist ledger instead of only producing prose.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_state  # noqa: E402


VALID_KINDS = {"life_restart_world_playtest", "life_restart_playtest"}
INTENT_SOURCES = {"entry", "modified_entry", "freeform", "implicit_default"}
CUSTOM_INTENT_SOURCES = {"modified_entry", "freeform"}
NO_PACK_PLACEHOLDERS = {"", "none", "no-pack", "no_pack", "custom", "manual"}
NON_ADJUDICATING_PACK_POLICY_MODES = {"none", "reference"}
VISIBLE_SNAPSHOT_KEYS = {
    "age",
    "time",
    "realm",
    "existence_state",
    "attributes",
    "relationships",
    "pressure",
    "pressure_clocks",
    "threads",
    "open_threads",
    "evidence",
    "terminal",
    "summary",
    "current",
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


def is_real_content_pack(world: Any) -> bool:
    if not isinstance(world, dict):
        return False
    content_pack = world.get("content_pack")
    if not isinstance(content_pack, str):
        return False
    return content_pack.strip().lower() not in NO_PACK_PLACEHOLDERS


def pack_policy_mode(world: Any) -> str | None:
    if not isinstance(world, dict):
        return None
    policy = world.get("pack_policy")
    if not isinstance(policy, dict):
        return None
    mode = policy.get("mode")
    return mode if isinstance(mode, str) else None


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def split_event_id(value: Any) -> set[str]:
    event_ids: set[str] = set()
    for item in as_list(value):
        for part in str(item).split("+"):
            event_id = part.strip()
            if event_id:
                event_ids.add(event_id)
    return event_ids


def event_ids_from_state(state: Any) -> set[str]:
    if not isinstance(state, dict):
        return set()
    event_ids: set[str] = set()
    history = state.get("event_history")
    if isinstance(history, list):
        event_ids.update(str(item) for item in history if isinstance(item, str))
    timeline = state.get("timeline")
    if isinstance(timeline, list):
        for item in timeline:
            if isinstance(item, dict):
                event_ids.update(split_event_id(item.get("event_id")))
    return event_ids


def event_ids_from_turn(turn: dict[str, Any]) -> set[str]:
    event_ids: set[str] = set()
    for key in ["event_id", "event_ids", "event_material"]:
        event_ids.update(split_event_id(turn.get(key)))
    delta = turn.get("delta")
    if isinstance(delta, dict):
        event_ids.update(split_event_id(delta.get("event_material")))
        item = delta.get("timeline_item")
        if isinstance(item, dict):
            event_ids.update(split_event_id(item.get("event_id")))
    timeline_item = turn.get("timeline_item")
    if isinstance(timeline_item, dict):
        event_ids.update(split_event_id(timeline_item.get("event_id")))
    return event_ids


def state_objects(transcript: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    states: list[tuple[str, dict[str, Any]]] = []
    for key in ["initial_state", "mid_state", "final_state"]:
        value = transcript.get(key)
        if isinstance(value, dict):
            states.append((key, value))
    turns = transcript.get("turns")
    if isinstance(turns, list):
        for index, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue
            for key in ["state", "post_state"]:
                value = turn.get(key)
                if isinstance(value, dict):
                    states.append((f"turns[{index}].{key}", value))
    return states


def state_has_affordances(state: dict[str, Any]) -> bool:
    affordances = state.get("next_affordances")
    return isinstance(affordances, list) and bool(affordances)


def turn_has_affordances(turn: dict[str, Any]) -> bool:
    affordances = turn.get("next_affordances")
    if isinstance(affordances, list) and affordances:
        return True
    for key in ["state", "post_state"]:
        state = turn.get(key)
        if isinstance(state, dict) and state_has_affordances(state):
            return True
    return False


def turn_visible_snapshot(turn: dict[str, Any]) -> Any:
    for key in ["visible_snapshot", "current_snapshot", "player_snapshot", "snapshot"]:
        value = turn.get(key)
        if value is not None:
            return value
    return None


def has_visible_snapshot(turn: dict[str, Any]) -> bool:
    snapshot = turn_visible_snapshot(turn)
    if isinstance(snapshot, str):
        return bool(snapshot.strip())
    if isinstance(snapshot, dict):
        return any(value not in (None, "", [], {}) for value in snapshot.values())
    return False


def visible_snapshot_board_keys(turn: dict[str, Any]) -> set[str]:
    snapshot = turn_visible_snapshot(turn)
    if not isinstance(snapshot, dict):
        return set()
    return {
        key
        for key in snapshot
        if key in VISIBLE_SNAPSHOT_KEYS and snapshot.get(key) not in (None, "", [], {})
    }


def check_visible_snapshot(turn: dict[str, Any], index: int, warnings: list[str]) -> None:
    snapshot = turn_visible_snapshot(turn)
    if snapshot is None:
        return
    if isinstance(snapshot, str):
        if not snapshot.strip():
            warnings.append(f"turns[{index}].visible_snapshot is empty")
        return
    if not isinstance(snapshot, dict):
        warnings.append(f"turns[{index}].visible_snapshot should be a string or object")
        return
    if not snapshot:
        warnings.append(f"turns[{index}].visible_snapshot is empty")
        return
    if not visible_snapshot_board_keys(turn):
        warnings.append(f"turns[{index}].visible_snapshot has no recognizable board fields")


def raw_state_exposed(turn: dict[str, Any]) -> bool:
    return turn.get("raw_state_exposed") is True or turn.get("raw_json_exposed") is True


def raw_state_exposure_allowed(turn: dict[str, Any], transcript: dict[str, Any]) -> bool:
    return (
        transcript.get("debug") is True
        or transcript.get("raw_state_requested") is True
        or turn.get("debug") is True
        or turn.get("raw_state_requested") is True
    )


def turn_intent_source(turn: dict[str, Any]) -> str | None:
    value = turn.get("intent_source")
    if isinstance(value, str):
        return value
    intent = turn.get("intent")
    if isinstance(intent, dict) and isinstance(intent.get("source"), str):
        return intent["source"]
    for key in ["state", "post_state"]:
        state = turn.get(key)
        if isinstance(state, dict):
            last_intent = state.get("last_intent")
            if isinstance(last_intent, dict) and isinstance(last_intent.get("source"), str):
                return last_intent["source"]
    return None


def turn_has_delta(turn: dict[str, Any]) -> bool:
    if isinstance(turn.get("delta"), dict):
        return True
    for key in ["state", "post_state"]:
        state = turn.get(key)
        if isinstance(state, dict) and isinstance(state.get("last_delta"), dict):
            return True
    return False


def turn_deltas(turn: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    deltas: list[tuple[str, dict[str, Any]]] = []
    delta = turn.get("delta")
    if isinstance(delta, dict):
        deltas.append(("delta", delta))
    for key in ["state", "post_state"]:
        state = turn.get(key)
        if isinstance(state, dict) and isinstance(state.get("last_delta"), dict):
            deltas.append((f"{key}.last_delta", state["last_delta"]))
    return deltas


def known_hooks_from_turn(turn: dict[str, Any]) -> set[str]:
    hooks: set[str] = set()
    for key in ["state", "post_state"]:
        state = turn.get(key)
        if isinstance(state, dict):
            hooks.update(validate_state.collect_known_hooks(state))
    for _, delta in turn_deltas(turn):
        hooks.update(validate_state.collect_delta_hooks(delta))
    return hooks


def nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value)


def check_turn_intent_trace(turn: dict[str, Any], source: str, index: int, errors: list[str], warnings: list[str]) -> None:
    traces: list[tuple[str, Any]] = []
    for path, delta in turn_deltas(turn):
        if "intent_trace" in delta:
            traces.append((path, delta.get("intent_trace")))
    if not traces:
        warnings.append(f"turns[{index}] uses {source} but has no last_delta.intent_trace")
        return

    complete_traces = 0
    known_hooks = known_hooks_from_turn(turn)
    for path, trace in traces:
        trace_path = f"turns[{index}].{path}.intent_trace"
        if not isinstance(trace, dict):
            errors.append(f"{trace_path} must be an object")
            continue
        trace_source = trace.get("source")
        if trace_source is not None and trace_source != source:
            warnings.append(f"{trace_path}.source={trace_source} does not match intent source {source}")
        if not nonempty_string_list(trace.get("preserved")):
            warnings.append(f"{trace_path}.preserved should name the custom action parts that survived resolution")
        state_hooks = trace.get("state_hooks")
        if not nonempty_string_list(state_hooks):
            warnings.append(f"{trace_path}.state_hooks should name ledger hooks touched by the custom action")
        elif known_hooks:
            unknown_hooks = [str(hook) for hook in state_hooks if str(hook) not in known_hooks]
            if unknown_hooks:
                warnings.append(f"{trace_path}.state_hooks do not reference known or changed ledger hooks: {unknown_hooks}")
        if not (isinstance(trace.get("outcome"), str) and trace["outcome"].strip()) and not (isinstance(trace.get("adjudication"), str) and trace["adjudication"].strip()):
            warnings.append(f"{trace_path} should include outcome or adjudication")
        if (
            nonempty_string_list(trace.get("preserved"))
            and nonempty_string_list(trace.get("state_hooks"))
            and ((isinstance(trace.get("outcome"), str) and trace["outcome"].strip()) or (isinstance(trace.get("adjudication"), str) and trace["adjudication"].strip()))
        ):
            complete_traces += 1
    if not complete_traces:
        warnings.append(f"turns[{index}] uses {source} but has no complete intent_trace")


def has_phase_endpoint(transcript: dict[str, Any], states: list[tuple[str, dict[str, Any]]]) -> bool:
    if transcript.get("phase_endpoint") is True:
        return True
    for _, state in states:
        if state.get("terminal") is True:
            return True
        summaries = state.get("phase_summaries")
        if isinstance(summaries, list) and summaries:
            return True
    turns = transcript.get("turns")
    if isinstance(turns, list):
        for turn in turns:
            if isinstance(turn, dict) and turn.get("phase_endpoint") is True:
                return True
    return False


def state_time_label(state: dict[str, Any]) -> str | None:
    time_value = state.get("time")
    if isinstance(time_value, dict) and isinstance(time_value.get("label"), str) and time_value["label"].strip():
        return time_value["label"]
    if isinstance(time_value, str) and time_value.strip():
        return time_value
    return None


def state_age_point(path: str, state: Any) -> tuple[str, int, str | None] | None:
    if not isinstance(state, dict):
        return None
    age = validate_state.int_or_none(state.get("age"))
    if age is None:
        return None
    return path, age, state_time_label(state)


def turn_time_label(turn: dict[str, Any], key: str) -> str | None:
    candidates = [f"time_{key.removeprefix('age_')}", "time"]
    for candidate in candidates:
        value = turn.get(candidate)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict) and isinstance(value.get("label"), str) and value["label"].strip():
            return value["label"]
    return None


def turn_age_point(index: int, turn: dict[str, Any]) -> tuple[str, int, str | None] | None:
    point = state_age_point(f"turns[{index}].post_state", turn.get("post_state"))
    if point is not None:
        return point
    for key in ["age_after", "age"]:
        age = validate_state.int_or_none(turn.get(key))
        if age is not None:
            return f"turns[{index}].{key}", age, turn_time_label(turn, key)
    return None


def age_points_from_transcript(transcript: dict[str, Any]) -> list[tuple[str, int, str | None]]:
    points: list[tuple[str, int, str | None]] = []
    initial = state_age_point("initial_state", transcript.get("initial_state"))
    if initial is not None:
        points.append(initial)
    turns = transcript.get("turns")
    if isinstance(turns, list):
        for index, turn in enumerate(turns):
            if isinstance(turn, dict):
                point = turn_age_point(index, turn)
                if point is not None:
                    points.append(point)
    final = state_age_point("final_state", transcript.get("final_state"))
    if final is not None and (not points or points[-1][1] != final[1]):
        points.append(final)
    return points


def pacing_metrics(points: list[tuple[str, int, str | None]]) -> dict[str, Any]:
    if not points:
        return {
            "age_points": [],
            "age_start": None,
            "age_end": None,
            "age_span": None,
            "max_age_jump": None,
            "same_age_transitions": 0,
            "same_age_missing_time": [],
            "age_regressions": [],
        }
    jumps = [after[1] - before[1] for before, after in zip(points, points[1:])]
    regressions = [
        {"from": before[0], "to": after[0], "before": before[1], "after": after[1]}
        for before, after in zip(points, points[1:])
        if after[1] < before[1]
    ]
    same_age_missing_time = [
        {"from": before[0], "to": after[0], "age": after[1]}
        for before, after in zip(points, points[1:])
        if after[1] == before[1] and (not before[2] or not after[2])
    ]
    return {
        "age_points": [{"path": path, "age": age, "time": time_label} for path, age, time_label in points],
        "age_start": points[0][1],
        "age_end": points[-1][1],
        "age_span": points[-1][1] - points[0][1],
        "max_age_jump": max(jumps) if jumps else 0,
        "same_age_transitions": sum(1 for jump in jumps if jump == 0),
        "same_age_missing_time": same_age_missing_time,
        "age_regressions": regressions,
    }


def validate(
    transcript: dict[str, Any],
    *,
    min_turns: int = 0,
    min_freeform: int = 0,
    min_modified_entry: int = 0,
    max_age_jump: int | None = None,
    max_age_span: int | None = None,
    min_same_age_turns: int = 0,
    forbid_age_regression: bool = False,
    min_visible_snapshots: int = 0,
    forbid_raw_state: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    state_results: list[dict[str, Any]] = []

    kind = transcript.get("kind")
    if kind not in VALID_KINDS:
        errors.append(f"kind must be one of {sorted(VALID_KINDS)}")
    if transcript.get("version") != 1:
        errors.append("version must be 1")
    hosting = transcript.get("hosting")
    if hosting is not None and hosting not in {"manual", "script-assisted", "script-driven"}:
        errors.append("hosting must be manual, script-assisted, or script-driven when present")

    turns = transcript.get("turns")
    if not isinstance(turns, list):
        errors.append("turns must be a list")
        turns = []
    if len(turns) < min_turns:
        warnings.append(f"turns has {len(turns)} entries; expected at least {min_turns}")

    custom_action_turns = 0
    freeform_turns = 0
    modified_entry_turns = 0
    turns_with_delta = 0
    turns_with_affordances = 0
    per_turn_state_snapshots = 0
    turns_with_visible_snapshot = 0
    structured_visible_snapshots = 0
    raw_state_exposed_turns = 0
    disallowed_raw_state_exposed_turns = 0
    transcript_event_ids: set[str] = set()

    for index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            errors.append(f"turns[{index}] must be an object")
            continue
        if not isinstance(turn.get("user_action"), str) or not turn["user_action"].strip():
            warnings.append(f"turns[{index}].user_action is missing or empty")
        source = turn_intent_source(turn)
        if source is None:
            warnings.append(f"turns[{index}] has no intent source")
        elif source not in INTENT_SOURCES:
            errors.append(f"turns[{index}].intent_source is invalid: {source}")
        elif source in CUSTOM_INTENT_SOURCES:
            custom_action_turns += 1
            if source == "freeform":
                freeform_turns += 1
            elif source == "modified_entry":
                modified_entry_turns += 1
            check_turn_intent_trace(turn, source, index, errors, warnings)
        if turn_has_delta(turn):
            turns_with_delta += 1
        else:
            warnings.append(f"turns[{index}] has no delta or post-state last_delta")
        if turn_has_affordances(turn):
            turns_with_affordances += 1
        else:
            warnings.append(f"turns[{index}] has no next_affordances evidence")
        if has_visible_snapshot(turn):
            turns_with_visible_snapshot += 1
            if visible_snapshot_board_keys(turn):
                structured_visible_snapshots += 1
        check_visible_snapshot(turn, index, warnings)
        if raw_state_exposed(turn):
            raw_state_exposed_turns += 1
            if forbid_raw_state and not raw_state_exposure_allowed(turn, transcript):
                disallowed_raw_state_exposed_turns += 1
                warnings.append(f"turns[{index}] exposes raw state during ordinary play; use visible_snapshot unless raw state was requested/debug")
        if isinstance(turn.get("state"), dict) or isinstance(turn.get("post_state"), dict):
            per_turn_state_snapshots += 1
        transcript_event_ids.update(event_ids_from_turn(turn))

    if not custom_action_turns:
        warnings.append("playtest has no freeform or modified_entry turns")
    if freeform_turns < min_freeform:
        warnings.append(f"playtest has {freeform_turns} freeform turns; expected at least {min_freeform}")
    if modified_entry_turns < min_modified_entry:
        warnings.append(f"playtest has {modified_entry_turns} modified_entry turns; expected at least {min_modified_entry}")
    if turns and not per_turn_state_snapshots:
        warnings.append("playtest has no per-turn state snapshots")
    if turns and not turns_with_affordances:
        warnings.append("playtest has no recorded next_affordances")
    if turns_with_visible_snapshot < min_visible_snapshots:
        warnings.append(f"playtest has {turns_with_visible_snapshot} visible snapshots; expected at least {min_visible_snapshots}")
    if forbid_raw_state and disallowed_raw_state_exposed_turns:
        warnings.append(f"raw state was exposed on {disallowed_raw_state_exposed_turns} turns without debug/raw_state_requested")

    states = state_objects(transcript)
    named_state_snapshots = sum(1 for key in ["initial_state", "mid_state", "final_state"] if isinstance(transcript.get(key), dict))
    if not states:
        warnings.append("playtest has no state object to validate")
    for path, state in states:
        result = validate_state.validate(state)
        state_results.append({"path": path, "ok": result["ok"], "warnings": result["warnings"], "errors": result["errors"]})
        if not result["ok"]:
            errors.append(f"{path} failed state validation")
        for warning in result["warnings"]:
            warnings.append(f"{path}: {warning}")
        transcript_event_ids.update(event_ids_from_state(state))

    if not isinstance(transcript.get("final_state"), dict):
        warnings.append("playtest.final_state is missing; endpoint state is harder to verify")

    pacing = pacing_metrics(age_points_from_transcript(transcript))
    pacing_gate_active = max_age_jump is not None or max_age_span is not None or min_same_age_turns > 0 or forbid_age_regression
    if pacing_gate_active and len(pacing["age_points"]) < 2:
        warnings.append("pacing gates need at least two age points; include initial_state/final_state, per-turn post_state, or age_after")
    if pacing_gate_active and pacing["same_age_missing_time"]:
        warnings.append(f"same-age pacing points are missing time labels: {pacing['same_age_missing_time']}")
    if forbid_age_regression and pacing["age_regressions"]:
        warnings.append(f"age decreases across transcript points: {pacing['age_regressions']}")
    if max_age_jump is not None and pacing["max_age_jump"] is not None and pacing["max_age_jump"] > max_age_jump:
        warnings.append(f"max age jump is {pacing['max_age_jump']}; expected at most {max_age_jump}")
    if max_age_span is not None and pacing["age_span"] is not None and pacing["age_span"] > max_age_span:
        warnings.append(f"age span is {pacing['age_span']}; expected at most {max_age_span}")
    if pacing["same_age_transitions"] < min_same_age_turns:
        warnings.append(f"playtest has {pacing['same_age_transitions']} same-age transitions; expected at least {min_same_age_turns}")

    worlds = [(f"{path}.world", state.get("world")) for path, state in states if isinstance(state.get("world"), dict)]
    top_world = transcript.get("world")
    if isinstance(top_world, dict):
        worlds.append(("world", top_world))
    for world_path, world in worlds:
        mode = pack_policy_mode(world)
        if mode in NON_ADJUDICATING_PACK_POLICY_MODES:
            if is_real_content_pack(world):
                warnings.append(f"{world_path}.pack_policy.mode={mode} should omit content_pack; list inspected packs in evaluated_packs unless they adjudicate events")
            non_manual_ids = sorted(event_id for event_id in transcript_event_ids if not event_id.startswith("manual_"))
            if non_manual_ids:
                warnings.append(f"{world_path}.pack_policy.mode={mode} but transcript includes non-manual event ids: {non_manual_ids}")

    metrics = {
        "turns": len(turns),
        "custom_action_turns": custom_action_turns,
        "freeform_turns": freeform_turns,
        "modified_entry_turns": modified_entry_turns,
        "turns_with_delta": turns_with_delta,
        "turns_with_affordances": turns_with_affordances,
        "turns_with_visible_snapshot": turns_with_visible_snapshot,
        "structured_visible_snapshots": structured_visible_snapshots,
        "raw_state_exposed_turns": raw_state_exposed_turns,
        "disallowed_raw_state_exposed_turns": disallowed_raw_state_exposed_turns,
        "per_turn_state_snapshots": per_turn_state_snapshots,
        "named_state_snapshots": named_state_snapshots,
        "state_snapshots": len(states),
        "phase_endpoint": has_phase_endpoint(transcript, states),
        "pacing": pacing,
    }
    return {"ok": not errors, "errors": errors, "warnings": warnings, "metrics": metrics, "state_results": state_results}


def main(argv: list[str]) -> int:
    usage = "Usage: validate_playtest.py [--fail-on-warnings] [--min-turns N] [--min-freeform N] [--min-modified-entry N] [--min-visible-snapshots N] [--max-age-jump N] [--max-age-span N] [--min-same-age-turns N] [--forbid-age-regression] [--forbid-raw-state] PLAYTEST_JSON_PATH_OR_INLINE_OR_-"
    args = argv[1:]
    if len(args) == 1 and args[0] in {"-h", "--help"}:
        print(usage)
        return 0
    fail_on_warnings = "--fail-on-warnings" in args
    args = [arg for arg in args if arg != "--fail-on-warnings"]
    forbid_age_regression = "--forbid-age-regression" in args
    args = [arg for arg in args if arg != "--forbid-age-regression"]
    forbid_raw_state = "--forbid-raw-state" in args
    args = [arg for arg in args if arg != "--forbid-raw-state"]
    min_turns = 0
    min_freeform = 0
    min_modified_entry = 0
    min_visible_snapshots = 0
    max_age_jump: int | None = None
    max_age_span: int | None = None
    min_same_age_turns = 0
    for option, target in [
        ("--min-turns", "min_turns"),
        ("--min-freeform", "min_freeform"),
        ("--min-modified-entry", "min_modified_entry"),
        ("--min-visible-snapshots", "min_visible_snapshots"),
        ("--max-age-jump", "max_age_jump"),
        ("--max-age-span", "max_age_span"),
        ("--min-same-age-turns", "min_same_age_turns"),
    ]:
        if option not in args:
            continue
        index = args.index(option)
        try:
            value = int(args[index + 1])
        except (IndexError, ValueError):
            print(usage, file=sys.stderr)
            return 2
        if target == "min_turns":
            min_turns = value
        elif target == "min_freeform":
            min_freeform = value
        elif target == "min_modified_entry":
            min_modified_entry = value
        elif target == "min_visible_snapshots":
            min_visible_snapshots = value
        elif target == "max_age_jump":
            max_age_jump = value
        elif target == "max_age_span":
            max_age_span = value
        elif target == "min_same_age_turns":
            min_same_age_turns = value
        args = args[:index] + args[index + 2 :]
    if len(args) != 1:
        print(usage, file=sys.stderr)
        return 2
    try:
        transcript = load_transcript(args[0])
    except Exception as exc:  # noqa: BLE001 - this is a CLI diagnostic helper.
        print(json.dumps({"ok": False, "errors": [f"could not load playtest: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        return 1
    result = validate(
        transcript,
        min_turns=min_turns,
        min_freeform=min_freeform,
        min_modified_entry=min_modified_entry,
        max_age_jump=max_age_jump,
        max_age_span=max_age_span,
        min_same_age_turns=min_same_age_turns,
        forbid_age_regression=forbid_age_regression,
        min_visible_snapshots=min_visible_snapshots,
        forbid_raw_state=forbid_raw_state,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        return 1
    if fail_on_warnings and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
