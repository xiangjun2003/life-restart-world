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
AFFORDANCE_RISKS = {"low", "medium", "high", "critical"}
INTENT_SOURCES = {"entry", "modified_entry", "freeform", "implicit_default"}
CUSTOM_INTENT_SOURCES = {"modified_entry", "freeform"}
INTENT_RISKS = {"none", "low", "medium", "high", "critical"}
PRESSURE_STATUSES = {"active", "filled", "resolved", "closed", "archived", "inactive"}
PROLOGUE_EXCEPTION_FLAGS = {"amnesia", "missing_records", "artificial_creation", "newly_created", "memory_erased", "unknown_past"}
NO_PACK_PLACEHOLDERS = {"", "none", "no-pack", "no_pack", "custom", "manual"}
PACK_POLICY_MODES = {"none", "reference", "adjudication", "active"}
NON_ADJUDICATING_PACK_POLICY_MODES = {"none", "reference"}
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


def looks_transcendent_realm(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(text) and any(hint in text for hint in TRANSCENDENT_REALM_HINTS)


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
        if str(clock.get("status", "")).lower() in INACTIVE_CLOCK_STATUSES:
            warnings.append(f"pressure_clocks.{clock_id} has inactive status {clock['status']}; move the result into phase_summaries or remove it from the active ledger")
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
                if str(item.get("status", "")).lower() in INACTIVE_EVIDENCE_STATUSES:
                    warnings.append(f"evidence.{item_id} has inactive status {item['status']}; archive it into phase_summaries, timeline, flags, or relationship notes")
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
                for key in PHASE_STRING_LIST_KEYS:
                    if key in item and not isinstance(item[key], list):
                        errors.append(f"phase_summaries[{index}].{key} must be a list when present")


def check_lifespan_transition(state: dict[str, Any], warnings: list[str]) -> None:
    existence_state = str(state.get("existence_state", "mortal"))
    if existence_state and existence_state not in KNOWN_EXISTENCE_STATES:
        warnings.append(f"existence_state is unusual: {existence_state}")
    if existence_state in MORTAL_LIKE_STATES and state.get("terminal") is not True and looks_transcendent_realm(state.get("realm")):
        warnings.append("realm looks transcendent while existence_state is mortal-like; confirm a mortal visitor premise or update existence_state")
    if not is_int_like(state.get("age")) or not is_int_like(state.get("life_cap")):
        return
    if state.get("terminal") is True:
        return

    age = int(state["age"])
    life_cap = int(state["life_cap"])
    if age < life_cap:
        return
    if existence_state in MORTAL_LIKE_STATES:
        warnings.append("age has reached or exceeded life_cap while terminal is false; mark an ending or record a concrete life extension/transformation")
    elif existence_state == "cultivator":
        warnings.append("cultivator age has reached or exceeded life_cap; extend life_cap, advance realm, or resolve the breakthrough/ending")


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


def collect_known_hooks(state: dict[str, Any]) -> set[str]:
    hooks = set(ATTRIBUTES)
    for key in ["relationships", "pressure_clocks", "evidence"]:
        value = state.get(key)
        if isinstance(value, dict):
            hooks.update(str(item) for item in value)
    for key in ["flags", "open_threads", "talents"]:
        value = state.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    hooks.add(item)
                elif isinstance(item, dict):
                    for id_key in ["id", "name"]:
                        if item.get(id_key):
                            hooks.add(str(item[id_key]))
    phase_summaries = state.get("phase_summaries")
    if isinstance(phase_summaries, list):
        for item in phase_summaries:
            if isinstance(item, dict) and item.get("id"):
                hooks.add(str(item["id"]))
    world = state.get("world")
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


def collect_current_board_hooks(state: dict[str, Any]) -> set[str]:
    hooks: set[str] = set()
    for key in ["relationships", "pressure_clocks", "evidence"]:
        value = state.get(key)
        if isinstance(value, dict):
            hooks.update(str(item) for item in value)
    for key in ["flags", "open_threads"]:
        value = state.get(key)
        if isinstance(value, list):
            hooks.update(str(item) for item in value if isinstance(item, str))
    affordances = state.get("next_affordances")
    if isinstance(affordances, list):
        for item in affordances:
            if isinstance(item, dict):
                for key in ["state_hooks", "targets"]:
                    value = item.get(key)
                    if isinstance(value, list):
                        hooks.update(str(hook) for hook in value if isinstance(hook, str))
    intent = state.get("last_intent")
    if isinstance(intent, dict):
        for key in ["targets", "tags"]:
            value = intent.get(key)
            if isinstance(value, list):
                hooks.update(str(hook) for hook in value if isinstance(hook, str))
    delta = state.get("last_delta")
    if isinstance(delta, dict):
        hooks.update(collect_delta_hooks(delta))
    return hooks


def check_next_affordances(value: Any, known_hooks: set[str], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("next_affordances must be a list when present")
        return
    if len(value) < 2 or len(value) > 4:
        warnings.append(f"next_affordances has {len(value)} entries; live turns should preserve 2-4 playable affordances")
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
                check_string_list_value(item[key], f"{path}.{key}", errors, warnings)
        state_hooks = item.get("state_hooks")
        if not state_hooks:
            warnings.append(f"{path}.state_hooks is missing or empty; live affordances should point at ledger hooks")
        elif isinstance(state_hooks, list) and not any(str(hook) in known_hooks for hook in state_hooks):
            warnings.append(f"{path}.state_hooks do not reference known ledger hooks: {state_hooks}")
        if not any(item.get(key) for key in ["tags", "targets", "state_hooks"]):
            warnings.append(f"{path} should include tags, targets, or state_hooks for state-led play")
        if item.get("risk") and str(item["risk"]) not in AFFORDANCE_RISKS:
            warnings.append(f"{path}.risk is unusual: {item['risk']}")
        signature = affordance_signature(item)
        if signature:
            signatures.append(signature)
    if structured_count >= 2 and len(set(signatures)) < 2:
        warnings.append("next_affordances do not expose at least two distinct state hook or target sets; avoid cosmetic variants")


def check_intent_list_field(intent: dict[str, Any], key: str, errors: list[str], warnings: list[str]) -> None:
    if key in intent:
        check_string_list_value(intent[key], f"last_intent.{key}", errors, warnings)


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
            check_string_list_value(trace[key], f"last_delta.intent_trace.{key}", errors, warnings)
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


def phase_thread_refs(state: dict[str, Any], key: str) -> set[str]:
    refs: set[str] = set()
    phase_summaries = state.get("phase_summaries")
    if not isinstance(phase_summaries, list):
        return refs
    for item in phase_summaries:
        if isinstance(item, dict) and isinstance(item.get(key), list):
            refs.update(str(thread) for thread in item[key] if isinstance(thread, str))
    return refs


def phase_summary_ids(state: dict[str, Any]) -> set[str]:
    phase_summaries = state.get("phase_summaries")
    if not isinstance(phase_summaries, list):
        return set()
    return {str(item.get("id")) for item in phase_summaries if isinstance(item, dict) and item.get("id")}


def timeline_event_ids(state: dict[str, Any]) -> set[str]:
    timeline = state.get("timeline")
    if not isinstance(timeline, list):
        return set()
    ids: set[str] = set()
    for item in timeline:
        if isinstance(item, dict):
            ids.update(parse_timeline_event_ids(item.get("event_id")))
    return ids


def archived_reference_text(state: dict[str, Any]) -> str:
    archive_surface = {
        "phase_summaries": state.get("phase_summaries"),
        "timeline": state.get("timeline"),
        "flags": state.get("flags"),
        "relationships": state.get("relationships"),
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


def structured_archive_mentions_item(state: dict[str, Any], item_id: str, state_key: str) -> bool:
    archive_keys = ARCHIVE_KEYS_BY_KIND.get(state_key, set())
    if not archive_keys:
        return False
    for surface_key in ["phase_summaries", "timeline"]:
        surface = state.get(surface_key)
        if not isinstance(surface, list):
            continue
        for entry in surface:
            if isinstance(entry, dict) and any(list_contains_id(entry.get(key), item_id) for key in archive_keys):
                return True
    return False


def has_malformed_archive_field(state: dict[str, Any], item_id: str, state_key: str) -> bool:
    archive_keys = ARCHIVE_KEYS_BY_KIND.get(state_key, set())
    for surface_key in ["phase_summaries", "timeline"]:
        surface = state.get(surface_key)
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


def loose_archive_mentions_item(state: dict[str, Any], item_id: str) -> bool:
    return str(item_id) in archived_reference_text(state)


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


def archive_field_suggestion(state_key: str) -> str:
    if state_key == "pressure_clocks":
        return "closed_clocks/resolved_clocks/archived_clocks"
    if state_key == "evidence":
        return "closed_evidence/resolved_evidence/archived_evidence/spent_evidence"
    return "structured archive fields"


def check_last_delta(value: Any, state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("last_delta must be an object when present")
        return
    if not value.get("summary") and not value.get("timeline_item"):
        warnings.append("last_delta should include summary or timeline_item")

    event_material = value.get("event_material") or value.get("event_ids")
    if event_material is not None:
        check_string_list_value(event_material, "last_delta.event_material", errors, warnings)
        if isinstance(event_material, list):
            history_ids = {str(item) for item in state.get("event_history", [])} if isinstance(state.get("event_history"), list) else set()
            timeline_ids = timeline_event_ids(state)
            for event_id in event_material:
                if isinstance(event_id, str):
                    if event_id not in history_ids:
                        warnings.append(f"last_delta.event_material.{event_id} is missing from event_history")
                    if event_id not in timeline_ids:
                        warnings.append(f"last_delta.event_material.{event_id} is missing from timeline event_id")

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

    for key, state_key in [("relationships", "relationships"), ("pressure_clocks", "pressure_clocks"), ("evidence", "evidence")]:
        touched = value.get(key)
        if touched is None:
            continue
        if not isinstance(touched, dict):
            errors.append(f"last_delta.{key} must be an object when present")
            continue
        ledger = state.get(state_key)
        ledger_ids = set(ledger) if isinstance(ledger, dict) else set()
        for item_id, item_delta in touched.items():
            if item_id not in ledger_ids:
                status = delta_item_status(item_delta)
                inactive_statuses = INACTIVE_CLOCK_STATUSES if key == "pressure_clocks" else INACTIVE_EVIDENCE_STATUSES if key == "evidence" else set()
                if status in inactive_statuses:
                    if structured_archive_mentions_item(state, str(item_id), state_key):
                        continue
                    if has_malformed_archive_field(state, str(item_id), state_key):
                        continue
                    if loose_archive_mentions_item(state, str(item_id)):
                        warnings.append(f"last_delta.{key}.{item_id} is inactive and only loosely archived; add {archive_field_suggestion(state_key)} to a phase_summaries or timeline item")
                        continue
                    warnings.append(f"last_delta.{key}.{item_id} is inactive but has no structured archive reference; add {archive_field_suggestion(state_key)} before removing it from the active ledger")
                    continue
                warnings.append(f"last_delta.{key}.{item_id} is not present in state.{state_key}")

    flags = {str(flag) for flag in state.get("flags", []) if isinstance(flag, str)} if isinstance(state.get("flags"), list) else set()
    for key in ["flags_added", "flags_removed", "threads_added", "threads_closed"]:
        if key in value:
            check_string_list_value(value[key], f"last_delta.{key}", errors, warnings)

    if isinstance(value.get("flags_added"), list):
        for flag in value["flags_added"]:
            if isinstance(flag, str) and flag not in flags:
                warnings.append(f"last_delta.flags_added.{flag} is not present in state.flags")
    if isinstance(value.get("flags_removed"), list):
        for flag in value["flags_removed"]:
            if isinstance(flag, str) and flag in flags:
                warnings.append(f"last_delta.flags_removed.{flag} is still present in state.flags")

    open_threads = {str(thread) for thread in state.get("open_threads", []) if isinstance(thread, str)} if isinstance(state.get("open_threads"), list) else set()
    carried_threads = phase_thread_refs(state, "carried_threads")
    closed_threads = phase_thread_refs(state, "closed_threads")
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
            if phase_summary not in phase_summary_ids(state):
                warnings.append(f"last_delta.phase_summary {phase_summary} is missing from phase_summaries")
        elif isinstance(phase_summary, dict):
            summary_id = phase_summary.get("id")
            if summary_id and summary_id not in phase_summary_ids(state):
                warnings.append(f"last_delta.phase_summary.id {summary_id} is missing from phase_summaries")
        else:
            errors.append("last_delta.phase_summary must be a string or object when present")


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

        for key in PHASE_STRING_LIST_KEYS:
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
            continue
        state_clock = state_clocks.get(clock_id) if isinstance(state_clocks, dict) else None
        status = str(state_clock.get("status", "")).lower() if isinstance(state_clock, dict) else ""
        if status in INACTIVE_CLOCK_STATUSES:
            warnings.append(f"{path} mirrors a {status} clock; move resolved pressure to phase_summaries or remove it from the active session note")
        if isinstance(state_clock, dict):
            for key in ["stage", "limit"]:
                if key in clock and key in state_clock and is_int_like(clock[key]) and is_int_like(state_clock[key]) and int(clock[key]) != int(state_clock[key]):
                    warnings.append(f"{path}.{key}={clock[key]} differs from state.pressure_clocks.{clock_id}.{key}={state_clock[key]}; state ledger is the source of truth")


def check_session_note_ledger_anchors(state: dict[str, Any], note: dict[str, Any], warnings: list[str]) -> None:
    anchors = collect_current_board_hooks(state)
    state_axes = {str(item) for item in note.get("state_axes", []) if isinstance(item, str)}
    factions = set(note.get("factions", {})) if isinstance(note.get("factions"), dict) else set()
    if state_axes and not (state_axes & anchors):
        warnings.append("world.session_note.state_axes are not anchored in the active ledger or next affordances; custom world axes should appear as flags, open_threads, clock/evidence ids, relationship ids, or state_hooks")
    if factions and not (factions & anchors):
        warnings.append("world.session_note.factions are not anchored in the active ledger or next affordances; at least one active faction should appear as a relationship/thread/clock/evidence id or state_hook")


def has_real_content_pack(world: dict[str, Any]) -> bool:
    content_pack = world.get("content_pack")
    if not isinstance(content_pack, str):
        return False
    return content_pack.strip().lower() not in NO_PACK_PLACEHOLDERS


def collect_event_ids(state: dict[str, Any]) -> set[str]:
    event_ids: set[str] = set()
    history = state.get("event_history")
    if isinstance(history, list):
        event_ids.update(str(item) for item in history if isinstance(item, str))
    timeline = state.get("timeline")
    if isinstance(timeline, list):
        for item in timeline:
            if isinstance(item, dict) and isinstance(item.get("event_id"), str):
                event_ids.add(item["event_id"])
    return event_ids


def check_pack_policy(state: dict[str, Any], world: dict[str, Any], content_pack_present: bool, errors: list[str], warnings: list[str]) -> None:
    policy = world.get("pack_policy")
    if policy is None:
        if not content_pack_present:
            warnings.append("custom or no-pack world should include world.pack_policy with mode none, reference, or adjudication")
        return
    if not isinstance(policy, dict):
        errors.append("world.pack_policy must be an object when present")
        return

    mode = policy.get("mode")
    if not isinstance(mode, str) or mode not in PACK_POLICY_MODES:
        errors.append(f"world.pack_policy.mode must be one of {sorted(PACK_POLICY_MODES)}")
        return

    evaluated_packs = policy.get("evaluated_packs")
    if evaluated_packs is not None:
        check_string_list_value(evaluated_packs, "world.pack_policy.evaluated_packs", errors, warnings)
    if "reason" in policy and not isinstance(policy["reason"], str):
        errors.append("world.pack_policy.reason must be a string when present")

    if content_pack_present and mode == "none":
        warnings.append("world.pack_policy.mode=none but world.content_pack is present")
    if content_pack_present and mode == "reference":
        warnings.append("world.pack_policy.mode=reference should omit world.content_pack; list inspected packs in evaluated_packs unless they adjudicate events")
    if not content_pack_present and mode == "active":
        warnings.append("world.pack_policy.mode=active requires a real world.content_pack")
    if not content_pack_present and mode in {"reference", "adjudication"}:
        if not isinstance(evaluated_packs, list) or not any(isinstance(item, str) and item.strip() for item in evaluated_packs):
            warnings.append(f"world.pack_policy.mode={mode} should name inspected packs in evaluated_packs")
    if mode in NON_ADJUDICATING_PACK_POLICY_MODES:
        non_manual_ids = sorted(event_id for event_id in collect_event_ids(state) if not event_id.startswith("manual_"))
        if non_manual_ids:
            warnings.append(f"world.pack_policy.mode={mode} but non-manual event ids appear without an active/adjudication pack: {non_manual_ids}")


def check_world(state: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    world = state.get("world")
    if not isinstance(world, dict):
        errors.append("world must be an object")
        return

    for key in ["style", "premise", "content_pack"]:
        if key in world and not isinstance(world[key], str):
            errors.append(f"world.{key} must be a string when present")
    if isinstance(world.get("content_pack"), str) and not has_real_content_pack(world):
        warnings.append("world.content_pack looks like a no-pack placeholder; omit content_pack for custom/no-pack worlds")
    content_pack_present = has_real_content_pack(world)
    check_pack_policy(state, world, content_pack_present, errors, warnings)
    if not world.get("premise"):
        warnings.append("world.premise is empty")

    session_note = world.get("session_note")
    if session_note is None:
        if not content_pack_present:
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

    if not content_pack_present:
        if not session_note.get("state_axes"):
            warnings.append("custom or no-pack world.session_note.state_axes is empty")
        if not session_note.get("factions"):
            warnings.append("custom or no-pack world.session_note.factions is empty")
        check_session_note_ledger_anchors(state, session_note, warnings)


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
        for key in PHASE_STRING_LIST_KEYS:
            if key in item:
                check_string_list_value(item[key], f"timeline[{index}].{key}", errors, warnings)
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
    pressure_clocks = state.get("pressure_clocks")
    if isinstance(pressure_clocks, dict) and len(pressure_clocks) > 5:
        warnings.append(f"pressure_clocks has more than 5 active items ({len(pressure_clocks)}): {sorted(pressure_clocks)}; resolve, archive, or summarize stale clocks")
    evidence = state.get("evidence")
    if isinstance(evidence, dict) and len(evidence) > 8:
        warnings.append(f"evidence has more than 8 active items ({len(evidence)}): {sorted(evidence)}; archive stale evidence into phase_summaries, flags, or relationship notes")
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
    check_lifespan_transition(state, warnings)

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
    if "next_affordances" in state:
        check_next_affordances(state["next_affordances"], collect_known_hooks(state), errors, warnings)
    if "last_intent" in state:
        check_last_intent(state["last_intent"], errors, warnings)
    if "last_delta" in state:
        check_last_delta(state["last_delta"], state, errors, warnings)
    if "last_intent" in state and "last_delta" in state:
        check_intent_trace(state["last_delta"], state["last_intent"], collect_known_hooks(state), errors, warnings)
    check_phase_summary_consistency(state, errors, warnings)
    check_timeline_and_history(state, errors, warnings)
    check_ledger_density(state, warnings)

    if state.get("terminal") is False and state.get("terminal_reason"):
        warnings.append("terminal_reason is set while terminal is false")
    if state.get("terminal") is True and not state.get("terminal_reason"):
        warnings.append("terminal is true but terminal_reason is empty")

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
    except Exception as exc:  # noqa: BLE001 - this is a CLI diagnostic helper.
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
