#!/usr/bin/env python3
"""Portable Life Restart World simulator.

This helper intentionally uses only the Python standard library. It is a
lightweight rules engine for state stepping; the agent still renders the final
story scene according to the skill's Game Master protocol.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import re
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "references" / "content-packs" / "classic-lite.json"


ATTRIBUTES = ("CHR", "INT", "STR", "MNY", "SPR", "LUK", "WIL")
INTENT_STOP_TAGS = {"achievement", "birth", "choice", "ending", "old_age", "origin"}

ACTION_TAGS = {
    "study": {"学习", "读书", "认字", "课本", "练习册", "借书", "考试", "学校", "成绩", "study", "exam", "school"},
    "work": {"打工", "赚钱", "工作", "兼职", "创业", "work", "job", "earn", "business"},
    "money": {"钱", "电脑", "买", "攒钱", "money", "computer", "buy"},
    "technology": {"电脑", "编程", "代码", "互联网", "技术", "ai", "computer", "code", "internet", "technology"},
    "family": {"家", "父母", "母亲", "父亲", "亲人", "family", "parent"},
    "secret": {"偷偷", "隐瞒", "不告诉", "秘密", "secret", "hide"},
    "relationship": {"朋友", "恋人", "老师", "信任", "关系", "friend", "love", "teacher", "trust"},
    "health": {"身体", "锻炼", "病", "健康", "health", "train"},
    "cultivation": {"修仙", "飞升", "灵根", "功法", "cultivation", "ascend"},
    "risk": {"冒险", "赌", "拼", "risk", "danger"},
    "observation": {"观察", "留意", "记住", "察觉", "observe", "observation", "notice"},
    "investigation": {"调查", "证据", "取证", "核验", "追查", "investigate", "evidence", "verify"},
    "labor": {"劳动", "排班", "夜班", "工时", "实习", "labor", "shift", "schedule", "internship"},
    "elder_care": {"老人", "养老", "照护", "护理", "elder", "eldercare", "care", "nursing"},
    "ethics": {"伦理", "隐私", "同意", "合规", "ethics", "privacy", "consent", "compliance"},
    "ai_scheduling": {"ai排班", "AI排班", "算法排班", "排班算法", "ai scheduling", "algorithmic scheduling"},
    "evidence": {"证据", "留痕", "材料", "记录", "evidence", "record"},
    "stealth": {"低调", "偷偷", "隐蔽", "不声张", "stealth", "quietly"},
    "worker_fatigue": {"疲劳", "过劳", "夜班", "burnout", "fatigue", "overwork"},
    "relationship_pressure": {"关系压力", "施压", "约谈", "人情", "relationship pressure", "pressure"},
}

TAG_GROUPS = {
    "study": {"study", "education", "exam", "school", "mentor"},
    "work": {"work", "job", "business", "career", "achievement", "city"},
    "money": {"money", "resources", "poverty"},
    "technology": {"technology", "computer", "code", "internet"},
    "family": {"family", "parent", "origin"},
    "secret": {"secret", "hide", "mystery"},
    "relationship": {"relationship", "family", "mentor", "friend", "love", "regret"},
    "health": {"health", "body", "illness"},
    "cultivation": {"cultivation", "ascend", "ascension", "mystery", "longevity"},
    "risk": {"risk", "danger", "choice", "crossroads"},
    "observation": {"observation", "observe", "notice", "family", "mystery"},
    "investigation": {"investigation", "evidence", "verify"},
    "labor": {"labor", "schedule", "shift"},
    "elder_care": {"elder_care", "care", "nursing"},
    "ethics": {"ethics", "privacy", "consent", "compliance"},
    "ai_scheduling": {"ai_scheduling", "algorithmic_scheduling"},
    "evidence": {"evidence", "record"},
    "stealth": {"stealth"},
    "worker_fatigue": {"worker_fatigue", "burnout", "fatigue", "overwork"},
    "relationship_pressure": {"relationship_pressure"},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)


def clamp_human(value: int, state: dict[str, Any]) -> int:
    existence = state.get("existence_state", "mortal")
    if existence in {"cultivator", "immortal", "ascended", "post_human"}:
        return max(-50, min(5000, value))
    return max(0, min(12, value))


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?\d+\.\d+", text):
            return float(text)
        return text.strip("'\"")
    return value


def parse_list(text: str) -> list[Any]:
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
    else:
        inner = text
    if not inner:
        return []
    out = []
    for item in inner.split(","):
        out.append(normalize_scalar(item.strip()))
    return out


def strip_outer_parens(expr: str) -> str:
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        depth = 0
        balanced = True
        for index, char in enumerate(expr):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(expr) - 1:
                    balanced = False
                    break
        if not balanced:
            break
        expr = expr[1:-1].strip()
    return expr


def split_top(expr: str, operator: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    bracket = 0
    start = 0
    for index, char in enumerate(expr):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == operator and depth == 0 and bracket == 0:
            parts.append(expr[start:index].strip())
            start = index + 1
    if parts:
        parts.append(expr[start:].strip())
    return parts


def talent_ids(state: dict[str, Any]) -> list[Any]:
    ids = []
    for talent in state.get("talents", []):
        if isinstance(talent, dict):
            ids.append(talent.get("id"))
        else:
            ids.append(talent)
    return ids


def get_prop(state: dict[str, Any], prop: str) -> Any:
    prop = prop.strip()
    if prop in {"AGE", "age"}:
        return state.get("age", 0)
    if prop in state.get("attributes", {}):
        return state["attributes"].get(prop, 0)
    if prop == "flags":
        return state.get("flags", [])
    if prop in {"EVT", "event_history"}:
        return state.get("event_history", [])
    if prop in {"TLT", "talents"}:
        return talent_ids(state)
    if prop in {"realm", "existence_state", "pace"}:
        return state.get(prop)
    if prop == "life_cap":
        return state.get("life_cap")
    return state.get(prop)


def contains_any(container: Any, values: list[Any]) -> bool:
    if not isinstance(container, list):
        container = [container]
    normalized = {str(normalize_scalar(item)) for item in container}
    return any(str(normalize_scalar(value)) in normalized for value in values)


def eval_atom(state: dict[str, Any], atom: str) -> bool:
    atom = strip_outer_parens(atom)
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(>=|<=|!=|>|<|=|\?|\!)(.+)$", atom)
    if not match:
        return bool(atom)
    prop, op, raw = match.groups()
    actual = get_prop(state, prop)
    if op in {"?", "!"}:
        result = contains_any(actual, parse_list(raw))
        return result if op == "?" else not result
    expected = normalize_scalar(raw)
    if op == "=":
        if isinstance(actual, list):
            return contains_any(actual, [expected])
        return str(actual) == str(expected)
    if op == "!=":
        if isinstance(actual, list):
            return not contains_any(actual, [expected])
        return str(actual) != str(expected)
    try:
        left = float(actual)
        right = float(expected)
    except (TypeError, ValueError):
        return False
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    return False


def eval_condition(state: dict[str, Any], expr: str | None) -> bool:
    if not expr:
        return True
    expr = strip_outer_parens(str(expr))
    or_parts = split_top(expr, "|")
    if or_parts:
        return any(eval_condition(state, part) for part in or_parts)
    and_parts = split_top(expr, "&")
    if and_parts:
        return all(eval_condition(state, part) for part in and_parts)
    return eval_atom(state, expr)


def infer_action(action: str | None) -> dict[str, Any]:
    action = (action or "").strip()
    tags = set()
    lower = action.lower()
    for tag, words in ACTION_TAGS.items():
        if any(word.lower() in lower for word in words):
            tags.add(tag)
    risk = "low"
    if "risk" in tags or any(word in lower for word in ["偷偷", "冒险", "赌", "危险", "secret"]):
        risk = "medium"
    if any(word in lower for word in ["拼命", "all in", "孤注一掷"]):
        risk = "high"
    checks = []
    if {"study", "technology", "cultivation", "investigation", "evidence", "ai_scheduling"} & tags:
        checks.append("INT")
    if {"work", "risk", "secret", "stealth", "ethics", "relationship_pressure"} & tags:
        checks.append("WIL")
    if {"health", "cultivation", "labor", "worker_fatigue", "elder_care"} & tags:
        checks.append("STR")
    if {"relationship", "relationship_pressure"} & tags:
        checks.append("CHR")
    return {
        "summary": action or "continue along the current life pressure",
        "tags": sorted(tags),
        "risk": risk,
        "checks": checks or ["WIL"],
    }


def normalize_intent(value: dict[str, Any], action: str | None = None) -> dict[str, Any]:
    intent = dict(value)
    if not intent.get("summary"):
        intent["summary"] = action or "continue along the current life pressure"
    tags = intent.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    intent["tags"] = sorted(str(tag) for tag in tags)
    checks = intent.get("checks", [])
    if isinstance(checks, str):
        checks = [check.strip() for check in checks.split(",") if check.strip()]
    intent["checks"] = [str(check) for check in checks]
    intent["risk"] = intent.get("risk", "low")
    return intent


def weighted_sample_without_replacement(items: list[dict[str, Any]], count: int, rng: random.Random) -> list[dict[str, Any]]:
    pool = [copy.deepcopy(item) for item in items]
    chosen = []
    grade_weight = {0: 8, 1: 6, 2: 3, 3: 1}
    while pool and len(chosen) < count:
        weights = [grade_weight.get(int(item.get("grade", 1)), 4) for item in pool]
        total = sum(weights)
        pick = rng.uniform(0, total)
        upto = 0.0
        index = 0
        for index, weight in enumerate(weights):
            upto += weight
            if pick <= upto:
                break
        chosen.append(pool.pop(index))
    return chosen


def apply_effects(state: dict[str, Any], effects: dict[str, Any] | None) -> None:
    for key, delta in (effects or {}).items():
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            continue
        if key in ATTRIBUTES:
            state["attributes"][key] = clamp_human(state["attributes"].get(key, 0) + delta, state)
        elif key == "AGE":
            state["age"] = max(0, state.get("age", 0) + delta)
        elif key == "LIF" and delta < 0:
            state["terminal"] = True
            state["terminal_reason"] = state.get("terminal_reason") or "Life force fell below survival."


def clamp_relationship(value: int) -> int:
    return max(-5, min(5, value))


def relationship_score(entry: Any) -> int:
    if isinstance(entry, dict):
        try:
            return int(entry.get("score", 0))
        except (TypeError, ValueError):
            return 0
    try:
        return int(entry)
    except (TypeError, ValueError):
        return 0


def apply_relationships(state: dict[str, Any], updates: dict[str, Any] | None) -> None:
    if not isinstance(updates, dict):
        return
    relationships = state.setdefault("relationships", {})
    for name, update in updates.items():
        current = relationships.get(name, {})
        entry = dict(current) if isinstance(current, dict) else {"score": relationship_score(current)}
        if isinstance(update, dict):
            if "score" in update:
                entry["score"] = clamp_relationship(relationship_score(update.get("score")))
            else:
                delta = update.get("delta", update.get("score_delta", 0))
                entry["score"] = clamp_relationship(relationship_score(entry) + int(delta or 0))
            if update.get("note"):
                entry["note"] = str(update["note"])
        else:
            entry["score"] = clamp_relationship(relationship_score(entry) + int(update or 0))
        relationships[str(name)] = entry


def apply_pressure_clocks(state: dict[str, Any], updates: dict[str, Any] | None) -> None:
    if not isinstance(updates, dict):
        return
    clocks = state.setdefault("pressure_clocks", {})
    for clock_id, update in updates.items():
        if update is None:
            clocks.pop(clock_id, None)
            continue
        if not isinstance(update, dict):
            update = {"delta": update}
        if update.get("close"):
            clocks.pop(clock_id, None)
            continue
        current = clocks.get(clock_id, {})
        clock = dict(current) if isinstance(current, dict) else {"stage": int(current or 0)}
        if "set_stage" in update:
            stage = int(update.get("set_stage") or 0)
        else:
            stage = int(clock.get("stage", 0)) + int(update.get("delta", 0) or 0)
        limit = update.get("limit", clock.get("limit"))
        if limit is not None:
            limit = int(limit)
            stage = max(0, min(limit, stage))
            clock["limit"] = limit
        else:
            stage = max(0, stage)
        clock["stage"] = stage
        for key in ["meaning", "on_fill", "status", "last_consequence"]:
            if update.get(key):
                clock[key] = str(update[key])
        if limit is not None and stage >= limit and not clock.get("last_consequence") and not clock.get("status"):
            clock["status"] = "filled"
        elif clock.get("status") == "filled" and limit is not None and stage < limit:
            clock.pop("status", None)
        clocks[str(clock_id)] = clock


def apply_evidence(state: dict[str, Any], updates: dict[str, Any] | None) -> None:
    if not isinstance(updates, dict):
        return
    evidence = state.setdefault("evidence", {})
    for item_id, update in updates.items():
        if update is None:
            evidence.pop(item_id, None)
            continue
        if not isinstance(update, dict):
            update = {"status": str(update)}
        current = evidence.get(item_id, {})
        item = dict(current) if isinstance(current, dict) else {}
        for key, value in update.items():
            item[key] = value
        evidence[str(item_id)] = item


def apply_event(state: dict[str, Any], event: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    apply_effects(state, event.get("effects"))
    apply_relationships(state, event.get("relationships"))
    apply_pressure_clocks(state, event.get("pressure_clocks"))
    apply_evidence(state, event.get("evidence"))
    flags = set(state.get("flags", []))
    flags.update(event.get("set_flags", []))
    flags.difference_update(event.get("clear_flags", []))
    state["flags"] = sorted(flags)

    threads = list(state.get("open_threads", []))
    for thread in event.get("open_threads", []):
        if thread not in threads:
            threads.append(thread)
    close_threads = set(event.get("close_threads", []))
    state["open_threads"] = [thread for thread in threads if thread not in close_threads]

    if event.get("life_cap") is not None:
        state["life_cap"] = max(int(event["life_cap"]), int(state.get("life_cap", 100)))
    if event.get("existence_state"):
        state["existence_state"] = event["existence_state"]
    if event.get("realm_transition"):
        state["realm"] = event["realm_transition"]
    if event.get("clear_terminal"):
        state["terminal"] = False
        state["terminal_reason"] = None
    if event.get("terminal"):
        state["terminal"] = True
        state["terminal_reason"] = event.get("terminal_reason") or event.get("title")

    event_id = event.get("id", "generated_event")
    if event_id not in state.get("event_history", []):
        state.setdefault("event_history", []).append(event_id)
    state.setdefault("timeline", []).append(
        {
            "turn": state.get("turn"),
            "age": state.get("age"),
            "event_id": event_id,
            "title": event.get("title"),
            "action": intent.get("summary"),
        }
    )
    return event


def age_matches(event: dict[str, Any], age: int) -> bool:
    if "age" in event and event["age"] is not None:
        return int(event["age"]) == age
    if "age_range" in event and event["age_range"]:
        low, high = event["age_range"]
        return int(low) <= age <= int(high)
    return True


def matching_pool_entries(pack: dict[str, Any], age: int) -> dict[str, int]:
    matched: dict[str, int] = {}
    pools = pack.get("age_pools", {})
    for key, items in pools.items():
        if "-" in str(key):
            low, high = [int(x) for x in str(key).split("-", 1)]
            is_match = low <= age <= high
        else:
            is_match = int(key) == age
        if not is_match:
            continue
        for item in items:
            matched[str(item.get("event_id"))] = int(item.get("weight", 1))
    return matched


def pool_weight(pack: dict[str, Any], event_id: str, age: int) -> int | None:
    return matching_pool_entries(pack, age).get(str(event_id))


def raw_tags(tags: Any) -> set[str]:
    if isinstance(tags, str):
        return {tags}
    return {str(tag) for tag in (tags or [])}


def context_tokens(values: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(values, dict):
        iterable = values.keys()
    elif isinstance(values, (list, tuple, set)):
        iterable = values
    elif values:
        iterable = [values]
    else:
        iterable = []
    for value in iterable:
        text = str(value)
        if not text:
            continue
        tokens.add(text)
        for part in re.split(r"[_\-\s:/]+", text):
            if part:
                tokens.add(part)
    return tokens


def state_context_tags(state: dict[str, Any]) -> set[str]:
    raw = set()
    raw.update(context_tokens(state.get("flags", [])))
    raw.update(context_tokens(state.get("open_threads", [])))
    raw.update(context_tokens(state.get("event_history", [])))
    raw.update(context_tokens(state.get("relationships", {})))
    return semantic_tags(raw)


def include_flag_refs(event: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    expr = str(event.get("include") or "")
    for raw in re.findall(r"flags\?\[([^\]]+)\]", expr):
        refs.update(str(item).strip() for item in raw.split(",") if str(item).strip())
    return refs


def action_relevance(event: dict[str, Any], intent: dict[str, Any]) -> float:
    event_raw = raw_tags(event.get("tags", [])) - INTENT_STOP_TAGS
    action_raw = raw_tags(intent.get("tags", [])) - INTENT_STOP_TAGS
    if not action_raw:
        return 1.0
    event_tags = semantic_tags(event_raw)
    action_tags = semantic_tags(action_raw)
    direct_overlap = len(event_raw & action_raw)
    semantic_overlap = len(event_tags & action_tags)
    weak_overlap = max(0, semantic_overlap - direct_overlap)
    return 1.0 + direct_overlap * 2.0 + weak_overlap * 0.35


def direct_intent_overlap(event: dict[str, Any], intent: dict[str, Any]) -> int:
    event_raw = raw_tags(event.get("tags", [])) - INTENT_STOP_TAGS
    action_raw = raw_tags(intent.get("tags", [])) - INTENT_STOP_TAGS
    return len(event_raw & action_raw)


def state_relevance(event: dict[str, Any], state: dict[str, Any]) -> float:
    score = 1.0
    event_tags = semantic_tags(event.get("tags", []))
    state_tags = state_context_tags(state)
    overlap = event_tags & state_tags
    if overlap:
        score += min(len(overlap), 4) * 0.25
    flags = set(str(item) for item in state.get("flags", []))
    matched_flags = include_flag_refs(event) & flags
    if matched_flags:
        score += min(len(matched_flags), 2) * 1.0
    event_id = str(event.get("id", ""))
    if event_id in state.get("open_threads", []):
        score += 1.0
    return score


def raw_tag_catalog(pack: dict[str, Any]) -> set[str]:
    tags = raw_tags(pack.get("compatible_world_tags", []))
    for event in pack.get("events", []):
        tags.update(raw_tags(event.get("tags", [])))
    for talent in pack.get("talents", []):
        tags.update(raw_tags(talent.get("tags", [])))
    return tags


def unsupported_tag_report(tags: list[str], raw_catalog: set[str], semantic_catalog: set[str]) -> tuple[list[str], list[str]]:
    unsupported = []
    weakly_supported = []
    for tag in tags:
        expanded = semantic_tags([tag])
        if not (expanded & semantic_catalog):
            unsupported.append(tag)
        elif tag not in raw_catalog:
            weakly_supported.append(tag)
    return unsupported, weakly_supported


def semantic_tags(tags: Any) -> set[str]:
    if isinstance(tags, str):
        raw_tags = {tags}
    else:
        raw_tags = {str(tag) for tag in (tags or [])}
    expanded = set(raw_tags)
    for tag in raw_tags:
        for group, members in TAG_GROUPS.items():
            if tag == group or tag in members:
                expanded.add(group)
                expanded.update(members)
    return expanded


def intent_aligned(event: dict[str, Any], intent: dict[str, Any]) -> bool:
    meaningful_intent = raw_tags(intent.get("tags", [])) - INTENT_STOP_TAGS
    action_tags = semantic_tags(meaningful_intent)
    if not action_tags:
        return True
    event_tags = semantic_tags(raw_tags(event.get("tags", [])) - INTENT_STOP_TAGS)
    return bool(event_tags & action_tags)


def summarize_candidates(candidates: list[tuple[dict[str, Any], float]]) -> list[dict[str, Any]]:
    summary = []
    for event, weight in candidates[:8]:
        summary.append(
            {
                "id": event.get("id"),
                "title": event.get("title"),
                "tags": event.get("tags", []),
                "weight": round(weight, 3),
            }
        )
    return summary


def pack_tag_catalog(pack: dict[str, Any]) -> set[str]:
    tags = semantic_tags(pack.get("compatible_world_tags", []))
    for event in pack.get("events", []):
        tags.update(semantic_tags(event.get("tags", [])))
    for talent in pack.get("talents", []):
        tags.update(semantic_tags(talent.get("tags", [])))
    return tags


def world_compatibility_tags(state: dict[str, Any]) -> list[str]:
    world = state.get("world", {})
    if not isinstance(world, dict):
        return []
    tags: list[str] = []
    for key in ["tags", "world_tags"]:
        value = world.get(key)
        if isinstance(value, str):
            tags.extend(tag.strip() for tag in value.split(",") if tag.strip())
        elif isinstance(value, list):
            tags.extend(str(tag) for tag in value)
    note = world.get("session_note", {})
    if isinstance(note, dict):
        for key in ["tags", "world_tags", "compatibility_tags"]:
            value = note.get(key)
            if isinstance(value, str):
                tags.extend(tag.strip() for tag in value.split(",") if tag.strip())
            elif isinstance(value, list):
                tags.extend(str(tag) for tag in value)
    seen = set()
    unique = []
    for tag in tags:
        if tag and tag not in seen:
            unique.append(tag)
            seen.add(tag)
    return unique


def content_pack_diagnostic(pack: dict[str, Any], state: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    compatible_realms = set(str(item) for item in pack.get("compatible_realms", []))
    realm = str(state.get("realm", "human_world"))
    intent_tags = [str(tag) for tag in intent.get("tags", [])]
    tag_catalog = pack_tag_catalog(pack)
    raw_catalog = raw_tag_catalog(pack)
    unsupported_tags, weakly_supported_tags = unsupported_tag_report(intent_tags, raw_catalog, tag_catalog)
    world_tags = world_compatibility_tags(state)
    unsupported_world_tags, weakly_supported_world_tags = unsupported_tag_report(world_tags, raw_catalog, tag_catalog)
    return {
        "pack_id": pack.get("id"),
        "realm": realm,
        "realm_supported": not compatible_realms or realm in compatible_realms or "any" in compatible_realms,
        "compatible_realms": sorted(compatible_realms),
        "unsupported_intent_tags": unsupported_tags,
        "weakly_supported_intent_tags": weakly_supported_tags,
        "world_compatibility_tags": world_tags,
        "world_shape_tags": world_tags,
        "unsupported_world_tags": unsupported_world_tags,
        "weakly_supported_world_tags": weakly_supported_world_tags,
    }


def collect_candidates(pack: dict[str, Any], state: dict[str, Any], intent: dict[str, Any]) -> list[tuple[dict[str, Any], float]]:
    age = int(state.get("age", 0))
    realm = state.get("realm", "human_world")
    history = set(str(item) for item in state.get("event_history", []))
    pool_entries = matching_pool_entries(pack, age)
    has_age_pool = bool(pack.get("age_pools"))
    candidates = []
    for raw in pack.get("events", []):
        event = copy.deepcopy(raw)
        event_id = str(event.get("id"))
        authored_age = "age" in event or "age_range" in event
        if authored_age and not age_matches(event, age):
            continue
        if has_age_pool and event_id not in pool_entries and not authored_age:
            continue
        event_realm = event.get("realm", "any")
        if event_realm not in {"any", realm, None}:
            continue
        pooled = pool_entries.get(event_id)
        if not event.get("repeatable", False) and event_id in history:
            continue
        if not eval_condition(state, event.get("include")):
            continue
        if event.get("exclude") and eval_condition(state, event.get("exclude")):
            continue
        base = pooled if pooled is not None else int(event.get("weight", 1))
        weight = max(0.1, base * action_relevance(event, intent) * state_relevance(event, state))
        candidates.append((event, weight))
    return candidates


def generated_event(state: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    tags = set(intent.get("tags", []))
    effects = {"WIL": 1}
    if "study" in tags:
        effects.update({"INT": 1, "SPR": -1})
    elif "work" in tags or "money" in tags:
        effects.update({"MNY": 1, "SPR": -1})
    elif "relationship" in tags or "family" in tags:
        effects.update({"SPR": 1})
    elif "health" in tags:
        effects.update({"STR": 1, "SPR": -1})
    elif "cultivation" in tags:
        effects.update({"INT": 1, "STR": 1, "SPR": -1})
    else:
        effects.update({"SPR": 0})
    flag = "action_" + re.sub(r"[^a-z0-9_]+", "_", "_".join(sorted(tags)) or "self_directed").strip("_")
    return {
        "id": f"session_generated_{state.get('turn', 0):03d}",
        "title": "自选行动",
        "weight": 1,
        "repeatable": True,
        "tags": sorted(tags),
        "effects": effects,
        "set_flags": [flag],
        "narrative_seed": f"The character acts on a self-directed goal: {intent.get('summary')}",
        "choices": ["Accept the cost", "Look for help", "Change strategy"],
    }


def pick_event(candidates: list[tuple[dict[str, Any], float]], rng: random.Random) -> dict[str, Any]:
    total = sum(weight for _, weight in candidates)
    pick = rng.uniform(0, total)
    upto = 0.0
    for event, weight in candidates:
        upto += weight
        if pick <= upto:
            return event
    return candidates[-1][0]


def pick_best_event(candidates: list[tuple[dict[str, Any], float]], intent: dict[str, Any]) -> dict[str, Any]:
    return max(candidates, key=lambda item: (direct_intent_overlap(item[0], intent), item[1]))[0]


def advance_age(state: dict[str, Any], rng: random.Random) -> dict[str, int]:
    before = int(state.get("age", 0))
    pace = state.get("pace", "standard")
    existence = state.get("existence_state", "mortal")
    if pace == "detailed":
        inc = 1 if before < 30 else rng.randint(1, 2)
    elif pace == "fast":
        inc = rng.randint(2, 5) if before < 25 else rng.randint(5, 12)
    else:
        if before < 7:
            inc = rng.randint(1, 2)
        elif before < 23:
            inc = 1
        elif before < 45:
            inc = rng.randint(1, 2)
        elif before < 70:
            inc = rng.randint(2, 4)
        elif existence in {"cultivator", "immortal", "ascended", "post_human"}:
            inc = rng.randint(5, 20)
        else:
            inc = rng.randint(3, 7)
    state["age"] = before + inc
    return {"before": before, "after": state["age"], "increment": inc}


def state_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    if before.get("age") != after.get("age"):
        diff["age"] = [before.get("age"), after.get("age")]
    attr_delta = {}
    for key in ATTRIBUTES:
        old = before.get("attributes", {}).get(key)
        new = after.get("attributes", {}).get(key)
        if old != new:
            attr_delta[key] = new - old
    if attr_delta:
        diff["attributes"] = attr_delta
    for key in ["life_cap", "existence_state", "realm", "terminal", "terminal_reason"]:
        if before.get(key) != after.get(key):
            diff[key] = [before.get(key), after.get(key)]
    old_flags = set(before.get("flags", []))
    new_flags = set(after.get("flags", []))
    if old_flags != new_flags:
        diff["flags_added"] = sorted(new_flags - old_flags)
        diff["flags_removed"] = sorted(old_flags - new_flags)
    old_threads = set(before.get("open_threads", []))
    new_threads = set(after.get("open_threads", []))
    if old_threads != new_threads:
        diff["threads_added"] = sorted(new_threads - old_threads)
        diff["threads_closed"] = sorted(old_threads - new_threads)
    if before.get("relationships", {}) != after.get("relationships", {}):
        changed = {}
        before_relationships = before.get("relationships", {})
        after_relationships = after.get("relationships", {})
        for key in sorted(set(before_relationships) | set(after_relationships)):
            if before_relationships.get(key) != after_relationships.get(key):
                changed[key] = [before_relationships.get(key), after_relationships.get(key)]
        diff["relationships"] = changed
    if before.get("pressure_clocks", {}) != after.get("pressure_clocks", {}):
        changed = {}
        before_clocks = before.get("pressure_clocks", {})
        after_clocks = after.get("pressure_clocks", {})
        for key in sorted(set(before_clocks) | set(after_clocks)):
            if before_clocks.get(key) != after_clocks.get(key):
                changed[key] = [before_clocks.get(key), after_clocks.get(key)]
        diff["pressure_clocks"] = changed
    if before.get("evidence", {}) != after.get("evidence", {}):
        changed = {}
        before_evidence = before.get("evidence", {})
        after_evidence = after.get("evidence", {})
        for key in sorted(set(before_evidence) | set(after_evidence)):
            if before_evidence.get(key) != after_evidence.get(key):
                changed[key] = [before_evidence.get(key), after_evidence.get(key)]
        diff["evidence"] = changed
    return diff


def default_choices(event: dict[str, Any], state: dict[str, Any]) -> list[str]:
    choices = list(event.get("choices", []))
    if event.get("terminal") or state.get("terminal"):
        return choices[:4] if choices else ["Review this life", "Choose an inheritance", "Close the arc"]
    if len(choices) >= 3:
        return choices[:4]
    fallback = [
        "Take the stable path and reduce risk",
        "Push harder toward the current goal",
        "Ask someone important for help",
        "Change direction and accept the cost",
    ]
    for item in fallback:
        if len(choices) >= 4:
            break
        if item not in choices:
            choices.append(item)
    return choices[:4]


def create_state(pack: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    rng = random.Random(args.seed)
    attrs = {key: rng.randint(3, 7) for key in ATTRIBUTES}
    talents = weighted_sample_without_replacement(pack.get("talents", []), args.talents, rng)
    state = {
        "version": 1,
        "session_id": str(uuid.uuid4())[:12],
        "turn": 0,
        "pace": args.pace,
        "age": 0,
        "life_cap": 100,
        "existence_state": "mortal",
        "realm": "human_world",
        "world": {
            "style": args.style,
            "premise": args.world or "ordinary life with rare legendary branches",
            "content_pack": pack.get("id"),
            "session_note": {
                "tone": args.style,
                "state_axes": [],
                "pressure_clocks": {},
            },
        },
        "attributes": attrs,
        "talents": talents,
        "relationships": {},
        "pressure_clocks": {},
        "flags": [],
        "event_history": [],
        "open_threads": [],
        "timeline": [],
        "terminal": False,
        "terminal_reason": None,
        "rng_seed": args.seed,
    }
    for talent in talents:
        apply_effects(state, talent.get("effects"))
    birth_pool = matching_pool_entries(pack, 0)
    birth_events = []
    for event in pack.get("events", []):
        event_id = str(event.get("id"))
        if event.get("age") == 0 or event_id in birth_pool:
            if eval_condition(state, event.get("include")):
                birth_events.append(event)
    if birth_events:
        apply_event(state, copy.deepcopy(birth_events[0]), infer_action("birth"))
    return state


def load_state_arg(value: str) -> dict[str, Any]:
    if value == "-":
        return json.loads(sys.stdin.read())
    stripped = value.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(value)
    path = Path(value)
    try:
        if path.exists():
            return load_json(path)
    except OSError:
        pass
    return json.loads(value)


def load_intent_arg(value: str | None, action: str | None = None) -> dict[str, Any] | None:
    if not value:
        return None
    if value == "-":
        return normalize_intent(json.loads(sys.stdin.read()), action)
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return normalize_intent(json.loads(value), action)
    path = Path(value)
    try:
        if path.exists():
            return normalize_intent(load_json(path), action)
    except OSError:
        pass
    return normalize_intent(json.loads(value), action)


def command_new(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = create_state(pack, args)
    print(dump({"state": state, "opening_guidance": "Render a character card, then ask for the first action."}))


def command_turn(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = load_state_arg(args.state)
    seed = state.get("rng_seed")
    intent = load_intent_arg(args.intent, args.action) or infer_action(args.action)
    rng = random.Random(f"{seed}:{state.get('turn', 0)}:{intent.get('summary')}")
    before = copy.deepcopy(state)
    diagnostic = content_pack_diagnostic(pack, state, intent)
    unsupported_world = (not diagnostic["realm_supported"]) or bool(diagnostic.get("unsupported_world_tags"))
    if args.strict and unsupported_world:
        result = {
            "error": "unsupported_world",
            "intent": intent,
            "content_pack_diagnostic": diagnostic,
            "state_delta": {},
            "state": before,
            "canonical_state_unchanged": True,
            "gm_instruction": "Strict mode found that this content pack does not support the state's realm or declared world shape. Report the content-pack mismatch and host manually only if the playtest is evaluating Game Master behavior.",
        }
        print(dump(result))
        raise SystemExit(4)
    age_step = advance_age(state, rng)
    state["turn"] = int(state.get("turn", 0)) + 1
    candidates = collect_candidates(pack, state, intent)
    if args.strict and intent.get("tags"):
        aligned_candidates = [(event, weight) for event, weight in candidates if intent_aligned(event, intent)]
        if candidates and not aligned_candidates:
            result = {
                "error": "weak_intent_match",
                "intent": intent,
                "age_step": age_step,
                "age_step_is_diagnostic": True,
                "candidate_summaries": summarize_candidates(candidates),
                "content_pack_diagnostic": diagnostic,
                "state_delta": {},
                "state": before,
                "probe_state": state,
                "probe_only": True,
                "canonical_state_unchanged": True,
                "gm_instruction": "Strict mode found only weakly related age-valid events. Report this gap instead of using an unrelated event. Keep state as the canonical pre-turn state; age_step and probe_state are diagnostic only.",
            }
            print(dump(result))
            raise SystemExit(3)
        candidates = aligned_candidates
    if not candidates and args.strict:
        result = {
            "error": "no_matching_event",
            "intent": intent,
            "age_step": age_step,
            "age_step_is_diagnostic": True,
            "content_pack_diagnostic": diagnostic,
            "state_delta": {},
            "state": before,
            "probe_state": state,
            "probe_only": True,
            "canonical_state_unchanged": True,
            "gm_instruction": "Strict mode found no matching event. Report this gap instead of generating a fallback event. Keep state as the canonical pre-turn state; age_step and probe_state are diagnostic only.",
        }
        print(dump(result))
        raise SystemExit(2)
    if candidates:
        event = pick_best_event(candidates, intent) if args.strict else pick_event(candidates, rng)
    else:
        event = generated_event(state, intent)
    selected = copy.deepcopy(event)
    if selected.get("age_advance") == "none":
        state["age"] = before.get("age", state.get("age", 0))
        age_step = {"before": before.get("age", 0), "after": state["age"], "increment": 0}
    apply_event(state, selected, intent)
    if not state.get("terminal") and int(state.get("age", 0)) >= int(state.get("life_cap", 100)):
        if state.get("existence_state") in {"mortal", "resurrected"}:
            state["terminal"] = True
            state["terminal_reason"] = "The life reaches its current natural limit."
    result = {
        "intent": intent,
        "age_step": age_step,
        "selected_event": selected,
        "content_pack_diagnostic": diagnostic,
        "state_delta": state_diff(before, state),
        "state": state,
        "action_entries": default_choices(selected, state),
        "gm_instruction": "Use selected_event.narrative_seed and state_delta to write a complete story scene before showing choices.",
    }
    if args.save:
        Path(args.save).write_text(dump(state) + "\n", encoding="utf-8")
    print(dump(result))


def command_demo(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    new_args = argparse.Namespace(
        pack=args.pack,
        seed=args.seed,
        pace=args.pace,
        style=args.style,
        world=args.world,
        talents=3,
    )
    state = create_state(pack, new_args)
    print("# Demo State")
    print(dump(state))
    for index in range(args.turns):
        action = demo_action_for_age(state)
        turn_args = argparse.Namespace(pack=args.pack, state=dump(state), action=action, save=None)
        pack_data = load_json(Path(args.pack))
        rng = random.Random(f"{state.get('rng_seed')}:{state.get('turn', 0)}:{action}")
        before = copy.deepcopy(state)
        intent = infer_action(action)
        age_step = advance_age(state, rng)
        state["turn"] = int(state.get("turn", 0)) + 1
        candidates = collect_candidates(pack_data, state, intent)
        event = pick_event(candidates, rng) if candidates else generated_event(state, intent)
        selected = copy.deepcopy(event)
        apply_event(state, selected, intent)
        print(f"\n# Turn {index + 1}: {action}")
        print(dump({
            "age_step": age_step,
            "event": selected,
            "delta": state_diff(before, state),
            "choices": default_choices(selected, state),
        }))
        if state.get("terminal"):
            break


def demo_action_for_age(state: dict[str, Any]) -> str:
    age = int(state.get("age", 0))
    flags = set(str(item) for item in state.get("flags", []))
    if age < 5:
        return "我认真观察家里人的期待和钱的问题"
    if age < 9:
        return "我记住见过的屏幕和机器，想弄明白它们"
    if age < 13:
        return "我努力学习，争取老师帮助"
    if age < 16 and "teacher_noticed" in flags:
        return "我请老师允许我多用机房学习电脑"
    if age < 19:
        return "我在学习之外偷偷打工，攒钱买电脑"
    if age < 27:
        return "我想离开家乡去更大的城市"
    if "found_hidden_manual" in flags:
        return "我继续修炼并寻找突破"
    return "我稳住事业，也回头处理家里的关系"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Life Restart World portable simulator")
    p.set_defaults(func=None)
    sub = p.add_subparsers(dest="command", required=True)

    def add_pack(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--pack", default=str(DEFAULT_PACK), help="content pack JSON path")

    new = sub.add_parser("new", help="create a new state")
    add_pack(new)
    new.add_argument("--seed", type=int, default=None)
    new.add_argument("--pace", choices=["detailed", "standard", "fast"], default="standard")
    new.add_argument("--style", default="realistic")
    new.add_argument("--world", default="")
    new.add_argument("--talents", type=int, default=3, help="number of random talents to sample")
    new.set_defaults(func=command_new)

    turn = sub.add_parser("turn", help="advance one turn")
    add_pack(turn)
    turn.add_argument("--state", required=True, help="state JSON path, JSON string, or '-' for stdin")
    turn.add_argument("--action", default="")
    turn.add_argument("--intent", help="semantic intent JSON path or JSON string; prefer this over keyword parsing when available")
    turn.add_argument("--strict", action="store_true", help="fail with no_matching_event instead of generating a fallback event")
    turn.add_argument("--save", help="optional path to save updated state")
    turn.set_defaults(func=command_turn)

    demo = sub.add_parser("demo", help="run a small deterministic demo")
    add_pack(demo)
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--turns", type=int, default=5)
    demo.add_argument("--pace", choices=["detailed", "standard", "fast"], default="standard")
    demo.add_argument("--style", default="realistic")
    demo.add_argument("--world", default="1990s county realism with rare legendary branches")
    demo.set_defaults(func=command_demo)
    return p


def main() -> int:
    args = parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
