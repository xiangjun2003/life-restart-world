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

ACTION_TAGS = {
    "study": {"学习", "读书", "考试", "学校", "成绩", "study", "exam", "school"},
    "work": {"打工", "赚钱", "工作", "兼职", "创业", "work", "job", "earn", "business"},
    "money": {"钱", "电脑", "买", "攒钱", "money", "computer", "buy"},
    "family": {"家", "父母", "母亲", "父亲", "亲人", "family", "parent"},
    "secret": {"偷偷", "隐瞒", "不告诉", "秘密", "secret", "hide"},
    "relationship": {"朋友", "恋人", "老师", "关系", "friend", "love", "teacher"},
    "health": {"身体", "锻炼", "病", "健康", "health", "train"},
    "cultivation": {"修仙", "飞升", "灵根", "功法", "cultivation", "ascend"},
    "risk": {"冒险", "赌", "拼", "risk", "danger"},
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
    if {"study", "technology", "cultivation"} & tags:
        checks.append("INT")
    if {"work", "risk", "secret"} & tags:
        checks.append("WIL")
    if {"health", "cultivation"} & tags:
        checks.append("STR")
    if "relationship" in tags:
        checks.append("CHR")
    return {
        "summary": action or "continue along the current life pressure",
        "tags": sorted(tags),
        "risk": risk,
        "checks": checks or ["WIL"],
    }


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


def apply_event(state: dict[str, Any], event: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    apply_effects(state, event.get("effects"))
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


def action_relevance(event: dict[str, Any], intent: dict[str, Any]) -> float:
    event_tags = set(event.get("tags", []))
    action_tags = set(intent.get("tags", []))
    overlap = len(event_tags & action_tags)
    if not action_tags:
        return 1.0
    return 1.0 + overlap * 1.4


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
        if has_age_pool and event_id not in pool_entries and not authored_age:
            continue
        event_realm = event.get("realm", "any")
        if event_realm not in {"any", realm, None}:
            continue
        if not age_matches(event, age):
            pooled = pool_entries.get(event_id)
            if pooled is None:
                continue
        else:
            pooled = pool_entries.get(event_id)
        if not event.get("repeatable", False) and event_id in history:
            continue
        if not eval_condition(state, event.get("include")):
            continue
        if event.get("exclude") and eval_condition(state, event.get("exclude")):
            continue
        base = pooled if pooled is not None else int(event.get("weight", 1))
        weight = max(0.1, base * action_relevance(event, intent))
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
    return diff


def default_choices(event: dict[str, Any], state: dict[str, Any]) -> list[str]:
    choices = list(event.get("choices", []))
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
        },
        "attributes": attrs,
        "talents": talents,
        "relationships": {},
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


def command_new(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = create_state(pack, args)
    print(dump({"state": state, "opening_guidance": "Render a character card, then ask for the first action."}))


def command_turn(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = load_state_arg(args.state)
    seed = state.get("rng_seed")
    rng = random.Random(f"{seed}:{state.get('turn', 0)}:{args.action}")
    before = copy.deepcopy(state)
    intent = infer_action(args.action)
    age_step = advance_age(state, rng)
    state["turn"] = int(state.get("turn", 0)) + 1
    candidates = collect_candidates(pack, state, intent)
    event = pick_event(candidates, rng) if candidates else generated_event(state, intent)
    selected = copy.deepcopy(event)
    apply_event(state, selected, intent)
    if not state.get("terminal") and int(state.get("age", 0)) >= int(state.get("life_cap", 100)):
        if state.get("existence_state") in {"mortal", "resurrected"}:
            state["terminal"] = True
            state["terminal_reason"] = "The life reaches its current natural limit."
    result = {
        "intent": intent,
        "age_step": age_step,
        "selected_event": selected,
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
    actions = [
        "我认真观察家里人的期待",
        "我努力学习，争取老师帮助",
        "我偷偷打工，攒钱买电脑",
        "我想离开家乡去更大的城市",
        "我修炼那本奇怪的书",
    ]
    for index in range(args.turns):
        action = actions[index % len(actions)]
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
    new.add_argument("--talents", type=int, default=3)
    new.set_defaults(func=command_new)

    turn = sub.add_parser("turn", help="advance one turn")
    add_pack(turn)
    turn.add_argument("--state", required=True, help="state JSON path, JSON string, or '-' for stdin")
    turn.add_argument("--action", default="")
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
