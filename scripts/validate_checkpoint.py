#!/usr/bin/env python3
"""Validate a Life Restart World checkpoint capsule.

This is a handoff diagnostic, not a game engine. It checks that a checkpoint is
structured enough for another agent to reconstruct the protagonist ledger
without replaying the life or guessing hidden state.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_KEYS = [
    "kind",
    "version",
    "session_id",
    "turn",
    "age",
    "life_cap",
    "realm",
    "existence_state",
    "terminal",
    "terminal_reason",
    "world",
    "attributes",
    "talents",
    "relationships",
    "pressure_clocks",
    "evidence",
    "flags",
    "open_threads",
    "phase_summaries",
    "recent_timeline",
    "next_affordances",
]

ATTRIBUTES = ["CHR", "INT", "STR", "MNY", "SPR", "LUK", "WIL"]
LIST_KEYS = ["talents", "flags", "open_threads", "phase_summaries", "recent_timeline"]
EVIDENCE_RISKS = {"low", "medium", "high", "critical"}
AFFORDANCE_RISKS = {"low", "medium", "high", "critical"}
INTENT_SOURCES = {"entry", "modified_entry", "freeform", "implicit_default"}
CUSTOM_INTENT_SOURCES = {"modified_entry", "freeform"}
INTENT_RISKS = {"none", "low", "medium", "high", "critical"}
NO_PACK_PLACEHOLDERS = {"", "none", "no-pack", "no_pack", "custom", "manual"}
INACTIVE_CLOCK_STATUSES = {"resolved", "closed", "archived", "inactive"}
INACTIVE_EVIDENCE_STATUSES = {"resolved", "closed", "archived", "inactive", "spent"}
PHASE_STRING_LIST_KEYS = [
    "closed_threads",
    "carried_threads",
    "outcomes",
    "closed_clocks",
    "resolved_clocks",
    "archived_clocks",
    "closed_evidence",
    "resolved_evidence",
    "archived_evidence",
    "spent_evidence",
]
ARCHIVE_KEYS_BY_KIND = {
    "pressure_clocks": {"closed_clocks", "resolved_clocks", "archived_clocks"},
    "evidence": {"closed_evidence", "resolved_evidence", "archived_evidence", "spent_evidence"},
}
KNOWN_EXISTENCE_STATES = {"mortal", "resurrected", "cultivator", "immortal", "ascended", "post_human"}
MORTAL_LIKE_STATES = {"mortal", "resurrected"}
TRANSCENDENT_REALM_HINTS = (
    "upper_realm",
    "higher_realm",
    "cloud_realm",
    "celestial",
    "immortal",
    "ascend",
    "heaven",
    "sky_registry",
    "cultivation",
    "xian",
    "上界",
    "天界",
    "仙",
    "灵界",
    "飞升",
)


def load_checkpoint(value: str) -> dict[str, Any]:
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


def looks_transcendent_realm(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(text) and any(hint in text for hint in TRANSCENDENT_REALM_HINTS)


def duplicate_values(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
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


def check_attributes(value: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("attributes must be an object")
        return
    for attr in ATTRIBUTES:
        if attr not in value:
            errors.append(f"attributes.{attr} is missing")
        elif not is_int_like(value[attr]):
            errors.append(f"attributes.{attr} must be numeric")
    for attr in value:
        if attr not in ATTRIBUTES:
            warnings.append(f"attributes.{attr} is not a standard attribute")


def has_attribute_note(checkpoint: dict[str, Any], attr: str) -> bool:
    notes = checkpoint.get("attribute_notes")
    if not isinstance(notes, dict):
        return False
    note = notes.get(attr)
    if isinstance(note, str):
        return bool(note.strip())
    if isinstance(note, dict):
        return bool(note.get("note") or note.get("reason") or note.get("future_delta_policy"))
    return False


def check_attribute_ranges(checkpoint: dict[str, Any], warnings: list[str]) -> None:
    attrs = checkpoint.get("attributes")
    if not isinstance(attrs, dict):
        return
    existence_state = str(checkpoint.get("existence_state", "mortal"))
    for attr, raw_value in attrs.items():
        if attr not in ATTRIBUTES or not is_int_like(raw_value):
            continue
        value = int(raw_value)
        if existence_state in {"mortal", "resurrected"} and (value < 0 or value > 12) and not has_attribute_note(checkpoint, attr):
            warnings.append(f"attributes.{attr}={value} is outside the ordinary human range; include attribute_notes or clamp future deltas")


def check_lifespan_transition(checkpoint: dict[str, Any], warnings: list[str]) -> None:
    existence_state = str(checkpoint.get("existence_state", "mortal"))
    if existence_state and existence_state not in KNOWN_EXISTENCE_STATES:
        warnings.append(f"existence_state is unusual: {existence_state}")
    if existence_state in MORTAL_LIKE_STATES and checkpoint.get("terminal") is not True and looks_transcendent_realm(checkpoint.get("realm")):
        warnings.append("realm looks transcendent while existence_state is mortal-like; confirm a mortal visitor premise or update existence_state")
    if not is_int_like(checkpoint.get("age")) or not is_int_like(checkpoint.get("life_cap")):
        return
    if checkpoint.get("terminal") is True:
        return

    age = int(checkpoint["age"])
    life_cap = int(checkpoint["life_cap"])
    if age < life_cap:
        return
    if existence_state in MORTAL_LIKE_STATES:
        warnings.append("age has reached or exceeded life_cap while terminal is false; mark an ending or record a concrete life extension/transformation")
    elif existence_state == "cultivator":
        warnings.append("cultivator age has reached or exceeded life_cap; extend life_cap, advance realm, or resolve the breakthrough/ending")


def has_real_content_pack(value: dict[str, Any]) -> bool:
    content_pack = value.get("content_pack")
    if not isinstance(content_pack, str):
        return False
    return content_pack.strip().lower() not in NO_PACK_PLACEHOLDERS


def check_world(value: Any, active_clocks: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("world must be an object")
        return
    for key in ["style", "premise", "content_pack"]:
        if key in value and not isinstance(value[key], str):
            errors.append(f"world.{key} must be a string when present")
    if isinstance(value.get("content_pack"), str) and not has_real_content_pack(value):
        warnings.append("world.content_pack looks like a no-pack placeholder; omit content_pack for custom/no-pack worlds")
    content_pack_present = has_real_content_pack(value)
    if not value.get("premise"):
        warnings.append("world.premise is empty")
    session_note = value.get("session_note")
    if session_note is None:
        if not content_pack_present:
            warnings.append("custom or no-pack checkpoint should include world.session_note")
        return
    if not isinstance(session_note, dict):
        errors.append("world.session_note must be an object when present")
        return
    if "state_axes" in session_note:
        check_string_list(session_note["state_axes"], "world.session_note.state_axes", errors, warnings)
    elif not content_pack_present:
        warnings.append("custom or no-pack world.session_note.state_axes is missing")
    factions = session_note.get("factions")
    if factions is None:
        if not content_pack_present:
            warnings.append("custom or no-pack world.session_note.factions is missing")
    elif not isinstance(factions, dict):
        errors.append("world.session_note.factions must be an object when present")
    note_clocks = session_note.get("pressure_clocks")
    if note_clocks is not None:
        if not isinstance(note_clocks, dict):
            errors.append("world.session_note.pressure_clocks must be an object when present")
        else:
            for clock_id in note_clocks:
                if clock_id not in active_clocks:
                    warnings.append(f"world.session_note.pressure_clocks.{clock_id} is not mirrored in pressure_clocks; active pressure belongs in the checkpoint ledger")
                    continue
                clock = active_clocks.get(clock_id)
                status = str(clock.get("status", "")).lower() if isinstance(clock, dict) else ""
                if status in INACTIVE_CLOCK_STATUSES:
                    warnings.append(f"world.session_note.pressure_clocks.{clock_id} mirrors a {status} clock; move resolved pressure to phase_summaries or remove it from the active session note")
                if isinstance(clock, dict):
                    note_clock = note_clocks[clock_id]
                    for key in ["stage", "limit"]:
                        if isinstance(note_clock, dict) and key in note_clock and key in clock and is_int_like(note_clock[key]) and is_int_like(clock[key]) and int(note_clock[key]) != int(clock[key]):
                            warnings.append(f"world.session_note.pressure_clocks.{clock_id}.{key}={note_clock[key]} differs from pressure_clocks.{clock_id}.{key}={clock[key]}; checkpoint ledger is the source of truth")


def relationship_score(entry: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get("score")
    return entry


def check_relationships(value: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("relationships must be an object")
        return
    if len(value) > 8:
        warnings.append(f"relationships has more than 8 entries ({len(value)}); archive inactive contacts before handoff")
    for name, entry in value.items():
        score = relationship_score(entry)
        if not is_int_like(score):
            errors.append(f"relationships.{name}.score must be numeric")
            continue
        score_value = int(score)
        if score_value < -5 or score_value > 5:
            errors.append(f"relationships.{name}.score must be between -5 and 5")
        if isinstance(entry, dict) and "note" in entry and not isinstance(entry["note"], str):
            errors.append(f"relationships.{name}.note must be a string when present")
        if isinstance(entry, dict) and "tensions" in entry and not isinstance(entry["tensions"], list):
            errors.append(f"relationships.{name}.tensions must be a list when present")


def check_pressure_clocks(value: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("pressure_clocks must be an object")
        return
    if len(value) > 5:
        warnings.append(f"pressure_clocks has more than 5 active items ({len(value)}); resolve, archive, or summarize stale clocks before handoff")
    for clock_id, clock in value.items():
        path = f"pressure_clocks.{clock_id}"
        if not isinstance(clock, dict):
            errors.append(f"{path} must be an object with stage, limit, and meaning; expand compact checkpoint notation before handoff")
            continue
        if not is_int_like(clock.get("stage")):
            errors.append(f"{path}.stage must be numeric")
            continue
        if not is_int_like(clock.get("limit")):
            errors.append(f"{path}.limit must be numeric")
            continue
        stage = int(clock["stage"])
        limit = int(clock["limit"])
        if limit <= 0:
            errors.append(f"{path}.limit must be positive")
        if stage < 0 or stage > limit:
            errors.append(f"{path}.stage must be between 0 and limit")
        if not clock.get("meaning"):
            warnings.append(f"{path}.meaning is empty")
        if "status" in clock and not isinstance(clock["status"], str):
            errors.append(f"{path}.status must be a string when present")
        elif str(clock.get("status", "")).lower() in INACTIVE_CLOCK_STATUSES:
            warnings.append(f"{path} has inactive status {clock['status']}; move the result into phase_summaries or remove it before handoff")


def check_evidence(value: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("evidence must be an object")
        return
    if len(value) > 8:
        warnings.append(f"evidence has more than 8 active items ({len(value)}); archive stale evidence before handoff")
    for evidence_id, item in value.items():
        path = f"evidence.{evidence_id}"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object; expand compact checkpoint notation before handoff")
            continue
        if not item.get("claim") and not item.get("status"):
            warnings.append(f"{path} should include claim or status")
        if str(item.get("status", "")).lower() in INACTIVE_EVIDENCE_STATUSES:
            warnings.append(f"{path} has inactive status {item['status']}; archive it before handoff")
        holders = item.get("holders")
        if holders is None:
            warnings.append(f"{path}.holders is missing")
        else:
            check_string_list(holders, f"{path}.holders", errors, warnings)
        if item.get("risk") and str(item["risk"]) not in EVIDENCE_RISKS:
            warnings.append(f"{path}.risk is unusual: {item['risk']}")


def check_phase_summaries(value: Any, open_threads: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("phase_summaries must be a list")
        return
    active = {str(item) for item in open_threads} if isinstance(open_threads, list) else set()
    seen_ids: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"phase_summaries[{index}] must be an object")
            continue
        summary_id = item.get("id")
        if not isinstance(summary_id, str) or not summary_id.strip():
            errors.append(f"phase_summaries[{index}].id must be a nonempty string")
        elif summary_id in seen_ids:
            warnings.append(f"phase_summaries contains duplicate id: {summary_id}")
        else:
            seen_ids.add(summary_id)
        if not item.get("summary") and not item.get("title"):
            warnings.append(f"phase_summaries[{index}] should include summary or title")
        if "age" not in item and "time" not in item:
            warnings.append(f"phase_summaries[{index}] should include age or time")
        for key in PHASE_STRING_LIST_KEYS:
            if key in item:
                check_string_list(item[key], f"phase_summaries[{index}].{key}", errors, warnings)
        closed = {str(thread) for thread in item.get("closed_threads", []) if isinstance(thread, str)}
        carried = {str(thread) for thread in item.get("carried_threads", []) if isinstance(thread, str)}
        overlap = sorted(closed & carried)
        if overlap:
            warnings.append(f"phase_summaries[{index}] closes and carries the same threads: {overlap}")
        still_open = sorted(closed & active)
        if still_open:
            warnings.append(f"phase_summaries[{index}].closed_threads still appear in open_threads: {still_open}")


def check_recent_timeline(value: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("recent_timeline must be a list")
        return
    if not value:
        warnings.append("recent_timeline is empty")
    if len(value) > 6:
        warnings.append(f"recent_timeline has more than 6 items ({len(value)}); keep checkpoint compact")
    for index, item in enumerate(value):
        if isinstance(item, str):
            if not item.strip():
                errors.append(f"recent_timeline[{index}] must be nonempty")
        elif isinstance(item, dict):
            if not item.get("summary") and not item.get("title") and not item.get("action"):
                warnings.append(f"recent_timeline[{index}] should include summary, title, or action")
            for key in PHASE_STRING_LIST_KEYS:
                if key in item:
                    check_string_list(item[key], f"recent_timeline[{index}].{key}", errors, warnings)
        else:
            errors.append(f"recent_timeline[{index}] must be a string or object")


def check_checkpoint_density(checkpoint: dict[str, Any], warnings: list[str]) -> None:
    open_threads = checkpoint.get("open_threads")
    if isinstance(open_threads, list) and len(open_threads) > 8:
        warnings.append(f"open_threads has more than 8 items ({len(open_threads)}); close stale threads or summarize them before handoff")
    if checkpoint.get("terminal") is True and isinstance(open_threads, list) and len(open_threads) > 3:
        warnings.append(f"terminal checkpoint still has many open_threads ({len(open_threads)}); close or summarize resolved threads")


def affordance_label(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("label", ""))
    return str(item)


def affordance_signature(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    hooks = item.get("state_hooks")
    targets = item.get("targets")
    if isinstance(hooks, list) and hooks:
        return json.dumps(sorted(str(hook) for hook in hooks), ensure_ascii=False)
    if isinstance(targets, list) and targets:
        return json.dumps(sorted(str(target) for target in targets), ensure_ascii=False)
    return ""


def collect_known_hooks(checkpoint: dict[str, Any]) -> set[str]:
    hooks = set(ATTRIBUTES)
    for key in ["relationships", "pressure_clocks", "evidence"]:
        value = checkpoint.get(key)
        if isinstance(value, dict):
            hooks.update(str(item) for item in value)
    for key in ["flags", "open_threads", "talents"]:
        value = checkpoint.get(key)
        if isinstance(value, list):
            hooks.update(str(item) for item in value if isinstance(item, str))
    phase_summaries = checkpoint.get("phase_summaries")
    if isinstance(phase_summaries, list):
        for item in phase_summaries:
            if isinstance(item, dict) and item.get("id"):
                hooks.add(str(item["id"]))
    world = checkpoint.get("world")
    session_note = world.get("session_note") if isinstance(world, dict) else None
    if isinstance(session_note, dict):
        for key in ["state_axes", "evidence_tracks", "likely_choices", "terminal_paths"]:
            value = session_note.get(key)
            if isinstance(value, list):
                hooks.update(str(item) for item in value if isinstance(item, str))
        factions = session_note.get("factions")
        if isinstance(factions, dict):
            hooks.update(str(item) for item in factions)
    return hooks


def check_next_affordances(value: Any, known_hooks: set[str], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("next_affordances must be a list")
        return
    if len(value) < 2 or len(value) > 4:
        warnings.append(f"next_affordances has {len(value)} entries; handoff should preserve 2-4 playable affordances")
    labels = [affordance_label(item).strip() for item in value]
    duplicates = duplicate_values(labels)
    if duplicates:
        warnings.append(f"next_affordances contains duplicate labels: {duplicates}")
    signatures: list[str] = []
    structured_count = 0
    for index, item in enumerate(value):
        path = f"next_affordances[{index}]"
        if isinstance(item, str):
            if not item.strip():
                errors.append(f"{path} must be nonempty")
            continue
        if not isinstance(item, dict):
            errors.append(f"{path} must be a string or object")
            continue
        structured_count += 1
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"{path}.label must be a nonempty string")
        for key in ["tags", "targets", "state_hooks"]:
            if key in item:
                check_string_list(item[key], f"{path}.{key}", errors, warnings)
        state_hooks = item.get("state_hooks")
        if not state_hooks:
            warnings.append(f"{path}.state_hooks is missing or empty; handoff affordances should point at ledger hooks")
        elif isinstance(state_hooks, list) and not any(str(hook) in known_hooks for hook in state_hooks):
            warnings.append(f"{path}.state_hooks do not reference known ledger hooks: {state_hooks}")
        if not any(item.get(key) for key in ["tags", "targets", "state_hooks"]):
            warnings.append(f"{path} should include tags, targets, or state_hooks for handoff fidelity")
        if item.get("risk") and str(item["risk"]) not in AFFORDANCE_RISKS:
            warnings.append(f"{path}.risk is unusual: {item['risk']}")
        signature = affordance_signature(item)
        if signature:
            signatures.append(signature)
    if structured_count >= 2 and len(set(signatures)) < 2:
        warnings.append("next_affordances do not expose at least two distinct state hook or target sets; avoid cosmetic variants")


def check_intent_list_field(intent: dict[str, Any], key: str, errors: list[str], warnings: list[str]) -> None:
    if key in intent:
        check_string_list(intent[key], f"last_intent.{key}", errors, warnings)


def check_last_intent(value: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("last_intent must be an object when present")
        return
    summary = value.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("last_intent.summary must be a nonempty string")
    source = value.get("source")
    if source not in INTENT_SOURCES:
        errors.append(f"last_intent.source must be one of {sorted(INTENT_SOURCES)}")
        return
    if "selected_entry" in value and not is_int_like(value["selected_entry"]):
        errors.append("last_intent.selected_entry must be numeric when present")
    if source in {"entry", "modified_entry"} and "selected_entry" not in value:
        warnings.append(f"last_intent.source={source} should include selected_entry")
    if source == "modified_entry" and not value.get("modifiers"):
        warnings.append("last_intent.source=modified_entry should include modifiers so the user change is preserved")
    if source == "freeform" and "selected_entry" in value:
        warnings.append("last_intent.source=freeform should not keep selected_entry; do not squeeze free action into a menu entry")
    if source == "freeform" and not (value.get("raw_action") or value.get("user_action")):
        warnings.append("last_intent.source=freeform should include raw_action or user_action for audit")
    if source == "implicit_default" and value.get("raw_action"):
        warnings.append("last_intent.source=implicit_default should not include raw_action")
    for key in ["modifiers", "targets", "tags", "checks"]:
        check_intent_list_field(value, key, errors, warnings)
    if value.get("risk") and str(value["risk"]) not in INTENT_RISKS:
        warnings.append(f"last_intent.risk is unusual: {value['risk']}")
    for key in ["raw_action", "user_action", "desired_outcome"]:
        if key in value and not isinstance(value[key], str):
            errors.append(f"last_intent.{key} must be a string when present")


def collect_delta_hooks(delta: dict[str, Any]) -> set[str]:
    hooks: set[str] = set()
    attrs = delta.get("attributes")
    if isinstance(attrs, dict):
        hooks.update(str(item) for item in attrs)
    for key in ["relationships", "pressure_clocks", "evidence"]:
        value = delta.get(key)
        if isinstance(value, dict):
            hooks.update(str(item) for item in value)
    for key in ["flags_added", "flags_removed", "threads_added", "threads_closed", "event_material", "event_ids"]:
        value = delta.get(key)
        if isinstance(value, list):
            hooks.update(str(item) for item in value if isinstance(item, str))
    phase_summary = delta.get("phase_summary")
    if isinstance(phase_summary, str):
        hooks.add(phase_summary)
    elif isinstance(phase_summary, dict) and phase_summary.get("id"):
        hooks.add(str(phase_summary["id"]))
    return hooks


def check_intent_trace(delta: Any, intent: Any, known_hooks: set[str], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(delta, dict) or not isinstance(intent, dict):
        return
    source = intent.get("source")
    trace = delta.get("intent_trace")
    if source in CUSTOM_INTENT_SOURCES and trace is None:
        warnings.append(f"last_delta.intent_trace is missing; {source} turns should show which custom intent parts reached state")
        return
    if trace is None:
        return
    if not isinstance(trace, dict):
        errors.append("last_delta.intent_trace must be an object when present")
        return
    trace_source = trace.get("source")
    if trace_source is not None and trace_source != source:
        warnings.append(f"last_delta.intent_trace.source={trace_source} does not match last_intent.source={source}")
    for key in ["preserved", "state_hooks"]:
        if key in trace:
            check_string_list(trace[key], f"last_delta.intent_trace.{key}", errors, warnings)
    if source == "modified_entry" and intent.get("modifiers") and not trace.get("preserved"):
        warnings.append("last_delta.intent_trace.preserved should name the user modifiers that survived resolution")
    if source == "freeform" and not trace.get("preserved"):
        warnings.append("last_delta.intent_trace.preserved should name the free-form action that was adjudicated")
    state_hooks = trace.get("state_hooks")
    if not state_hooks:
        warnings.append("last_delta.intent_trace.state_hooks is missing or empty; custom actions should point at ledger hooks")
    elif isinstance(state_hooks, list):
        valid_hooks = known_hooks | collect_delta_hooks(delta)
        unknown_hooks = [str(hook) for hook in state_hooks if str(hook) not in valid_hooks]
        if unknown_hooks:
            warnings.append(f"last_delta.intent_trace.state_hooks do not reference known or changed ledger hooks: {unknown_hooks}")
    if not trace.get("outcome") and not trace.get("adjudication") and not trace.get("preserved"):
        warnings.append("last_delta.intent_trace should include preserved, outcome, or adjudication")
    for key in ["outcome", "adjudication", "notes"]:
        if key in trace and not isinstance(trace[key], str):
            errors.append(f"last_delta.intent_trace.{key} must be a string when present")


def phase_thread_refs(checkpoint: dict[str, Any], key: str) -> set[str]:
    refs: set[str] = set()
    phase_summaries = checkpoint.get("phase_summaries")
    if not isinstance(phase_summaries, list):
        return refs
    for item in phase_summaries:
        if isinstance(item, dict) and isinstance(item.get(key), list):
            refs.update(str(thread) for thread in item[key] if isinstance(thread, str))
    return refs


def phase_summary_ids(checkpoint: dict[str, Any]) -> set[str]:
    phase_summaries = checkpoint.get("phase_summaries")
    if not isinstance(phase_summaries, list):
        return set()
    return {str(item.get("id")) for item in phase_summaries if isinstance(item, dict) and item.get("id")}


def archived_reference_text(checkpoint: dict[str, Any]) -> str:
    archive_surface = {
        "phase_summaries": checkpoint.get("phase_summaries"),
        "recent_timeline": checkpoint.get("recent_timeline"),
        "flags": checkpoint.get("flags"),
        "relationships": checkpoint.get("relationships"),
    }
    return json.dumps(archive_surface, ensure_ascii=False, sort_keys=True)


def list_contains_id(value: Any, item_id: str) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if isinstance(item, str) and item == item_id:
            return True
        if isinstance(item, dict) and str(item.get("id", "")) == item_id:
            return True
    return False


def structured_archive_mentions_item(checkpoint: dict[str, Any], item_id: str, checkpoint_key: str) -> bool:
    archive_keys = ARCHIVE_KEYS_BY_KIND.get(checkpoint_key, set())
    if not archive_keys:
        return False
    for surface_key in ["phase_summaries", "recent_timeline"]:
        surface = checkpoint.get(surface_key)
        if not isinstance(surface, list):
            continue
        for entry in surface:
            if isinstance(entry, dict) and any(list_contains_id(entry.get(key), item_id) for key in archive_keys):
                return True
    return False


def has_malformed_archive_field(checkpoint: dict[str, Any], item_id: str, checkpoint_key: str) -> bool:
    archive_keys = ARCHIVE_KEYS_BY_KIND.get(checkpoint_key, set())
    for surface_key in ["phase_summaries", "recent_timeline"]:
        surface = checkpoint.get(surface_key)
        if not isinstance(surface, list):
            continue
        for entry in surface:
            if not isinstance(entry, dict):
                continue
            for key in archive_keys:
                value = entry.get(key)
                if not isinstance(value, list) and str(item_id) in json.dumps(value, ensure_ascii=False):
                    return True
    return False


def loose_archive_mentions_item(checkpoint: dict[str, Any], item_id: str) -> bool:
    return str(item_id) in archived_reference_text(checkpoint)


def delta_item_status(value: Any) -> str:
    if isinstance(value, dict):
        if "status" in value:
            return str(value["status"]).lower()
        for key in ["after", "to", "new"]:
            nested = value.get(key)
            if isinstance(nested, dict) and "status" in nested:
                return str(nested["status"]).lower()
    if isinstance(value, list) and value:
        return delta_item_status(value[-1])
    return ""


def archive_field_suggestion(checkpoint_key: str) -> str:
    if checkpoint_key == "pressure_clocks":
        return "closed_clocks/resolved_clocks/archived_clocks"
    if checkpoint_key == "evidence":
        return "closed_evidence/resolved_evidence/archived_evidence/spent_evidence"
    return "structured archive fields"


def check_last_delta(value: Any, checkpoint: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("last_delta must be an object when present")
        return
    if not value.get("summary") and not value.get("timeline_item"):
        warnings.append("last_delta should include summary or timeline_item")

    event_material = value.get("event_material") or value.get("event_ids")
    if event_material is not None:
        check_string_list(event_material, "last_delta.event_material", errors, warnings)

    attrs = value.get("attributes")
    if attrs is not None:
        if not isinstance(attrs, dict):
            errors.append("last_delta.attributes must be an object when present")
        else:
            for attr, delta in attrs.items():
                if attr not in ATTRIBUTES:
                    warnings.append(f"last_delta.attributes.{attr} is not a standard attribute")
                if not is_int_like(delta):
                    errors.append(f"last_delta.attributes.{attr} must be numeric")

    for key, checkpoint_key in [("relationships", "relationships"), ("pressure_clocks", "pressure_clocks"), ("evidence", "evidence")]:
        touched = value.get(key)
        if touched is None:
            continue
        if not isinstance(touched, dict):
            errors.append(f"last_delta.{key} must be an object when present")
            continue
        ledger = checkpoint.get(checkpoint_key)
        ledger_ids = set(ledger) if isinstance(ledger, dict) else set()
        for item_id, item_delta in touched.items():
            if item_id not in ledger_ids:
                status = delta_item_status(item_delta)
                inactive_statuses = INACTIVE_CLOCK_STATUSES if key == "pressure_clocks" else INACTIVE_EVIDENCE_STATUSES if key == "evidence" else set()
                if status in inactive_statuses:
                    if structured_archive_mentions_item(checkpoint, str(item_id), checkpoint_key):
                        continue
                    if has_malformed_archive_field(checkpoint, str(item_id), checkpoint_key):
                        continue
                    if loose_archive_mentions_item(checkpoint, str(item_id)):
                        warnings.append(f"last_delta.{key}.{item_id} is inactive and only loosely archived; add {archive_field_suggestion(checkpoint_key)} to a phase_summaries or recent_timeline item")
                        continue
                    warnings.append(f"last_delta.{key}.{item_id} is inactive but has no structured archive reference; add {archive_field_suggestion(checkpoint_key)} before removing it from the active ledger")
                    continue
                warnings.append(f"last_delta.{key}.{item_id} is not present in {checkpoint_key}")

    flags = {str(flag) for flag in checkpoint.get("flags", []) if isinstance(flag, str)} if isinstance(checkpoint.get("flags"), list) else set()
    for key in ["flags_added", "flags_removed", "threads_added", "threads_closed"]:
        if key in value:
            check_string_list(value[key], f"last_delta.{key}", errors, warnings)

    if isinstance(value.get("flags_added"), list):
        for flag in value["flags_added"]:
            if isinstance(flag, str) and flag not in flags:
                warnings.append(f"last_delta.flags_added.{flag} is not present in flags")
    if isinstance(value.get("flags_removed"), list):
        for flag in value["flags_removed"]:
            if isinstance(flag, str) and flag in flags:
                warnings.append(f"last_delta.flags_removed.{flag} is still present in flags")

    open_threads = {str(thread) for thread in checkpoint.get("open_threads", []) if isinstance(thread, str)} if isinstance(checkpoint.get("open_threads"), list) else set()
    carried_threads = phase_thread_refs(checkpoint, "carried_threads")
    closed_threads = phase_thread_refs(checkpoint, "closed_threads")
    if isinstance(value.get("threads_added"), list):
        for thread in value["threads_added"]:
            if isinstance(thread, str) and thread not in open_threads and thread not in carried_threads and thread not in closed_threads:
                warnings.append(f"last_delta.threads_added.{thread} is not present in open_threads or phase_summaries")
    if isinstance(value.get("threads_closed"), list):
        for thread in value["threads_closed"]:
            if isinstance(thread, str) and thread in open_threads:
                warnings.append(f"last_delta.threads_closed.{thread} is still present in open_threads")

    phase_summary = value.get("phase_summary")
    if phase_summary is not None:
        if isinstance(phase_summary, str):
            if phase_summary not in phase_summary_ids(checkpoint):
                warnings.append(f"last_delta.phase_summary {phase_summary} is missing from phase_summaries")
        elif isinstance(phase_summary, dict):
            summary_id = phase_summary.get("id")
            if summary_id and summary_id not in phase_summary_ids(checkpoint):
                warnings.append(f"last_delta.phase_summary.id {summary_id} is missing from phase_summaries")
        else:
            errors.append("last_delta.phase_summary must be a string or object when present")


def validate(checkpoint: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(checkpoint, dict):
        return {"ok": False, "errors": ["checkpoint must be a JSON object"], "warnings": []}

    for key in REQUIRED_KEYS:
        if key not in checkpoint:
            errors.append(f"missing required key: {key}")

    if checkpoint.get("kind") != "life_restart_world_checkpoint":
        errors.append("kind must be life_restart_world_checkpoint")
    for key in ["version", "turn", "age", "life_cap"]:
        if key in checkpoint and not is_int_like(checkpoint.get(key)):
            errors.append(f"{key} must be numeric")
    if is_int_like(checkpoint.get("life_cap")) and int(checkpoint["life_cap"]) <= 0:
        errors.append("life_cap must be positive")
    for key in ["session_id", "realm", "existence_state"]:
        if key in checkpoint and (not isinstance(checkpoint[key], str) or not checkpoint[key].strip()):
            errors.append(f"{key} must be a nonempty string")
    if "terminal" in checkpoint and not isinstance(checkpoint["terminal"], bool):
        errors.append("terminal must be a boolean")
    if checkpoint.get("terminal") is True and not checkpoint.get("terminal_reason"):
        warnings.append("terminal is true but terminal_reason is empty")
    if checkpoint.get("terminal") is False and checkpoint.get("terminal_reason"):
        warnings.append("terminal_reason is set while terminal is false")
    if "time" in checkpoint and not isinstance(checkpoint["time"], (str, dict)):
        errors.append("time must be a string or object when present")
    check_lifespan_transition(checkpoint, warnings)

    active_clocks = checkpoint.get("pressure_clocks") if isinstance(checkpoint.get("pressure_clocks"), dict) else {}
    if "world" in checkpoint:
        check_world(checkpoint.get("world"), active_clocks, errors, warnings)
    check_attributes(checkpoint.get("attributes"), errors, warnings)
    check_attribute_ranges(checkpoint, warnings)
    for key in LIST_KEYS:
        if key not in {"phase_summaries", "recent_timeline"}:
            check_string_list(checkpoint.get(key), key, errors, warnings)
    check_relationships(checkpoint.get("relationships"), errors, warnings)
    check_pressure_clocks(checkpoint.get("pressure_clocks"), errors, warnings)
    check_evidence(checkpoint.get("evidence"), errors, warnings)
    check_phase_summaries(checkpoint.get("phase_summaries"), checkpoint.get("open_threads"), errors, warnings)
    check_recent_timeline(checkpoint.get("recent_timeline"), errors, warnings)
    check_checkpoint_density(checkpoint, warnings)
    check_next_affordances(checkpoint.get("next_affordances"), collect_known_hooks(checkpoint), errors, warnings)
    if "last_intent" in checkpoint:
        check_last_intent(checkpoint["last_intent"], errors, warnings)
    if "last_delta" in checkpoint:
        check_last_delta(checkpoint["last_delta"], checkpoint, errors, warnings)
    if "last_intent" in checkpoint and "last_delta" in checkpoint:
        check_intent_trace(checkpoint["last_delta"], checkpoint["last_intent"], collect_known_hooks(checkpoint), errors, warnings)

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str]) -> int:
    usage = "Usage: validate_checkpoint.py [--fail-on-warnings] CHECKPOINT_JSON_PATH_OR_INLINE_OR_-"
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
        checkpoint = load_checkpoint(args[0])
    except Exception as exc:  # noqa: BLE001 - this is a CLI diagnostic helper.
        print(json.dumps({"ok": False, "errors": [f"could not load checkpoint: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        return 1
    result = validate(checkpoint)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        return 1
    if fail_on_warnings and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
