#!/usr/bin/env python3
"""Diagnostic Life Restart World event probe.

This helper uses only the Python standard library. It can create a compact
LifeState v1 object, filter content-pack events, and apply an authored event as
a rough probe. It is not a natural-language game engine.
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

CORE_ATTRS = ("CHR", "INT", "STR", "MNY", "SPR", "LUK")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)


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
    inner = text[1:-1].strip() if text.startswith("[") and text.endswith("]") else text
    if not inner:
        return []
    return [normalize_scalar(item.strip()) for item in inner.split(",")]


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
    if prop in state.get("attrs", {}):
        return state["attrs"].get(prop, 0)
    if prop == "flags":
        return state.get("flags", [])
    if prop in {"EVT", "event_history"}:
        return state.get("event_history", [])
    if prop in {"TLT", "talents"}:
        return talent_ids(state)
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


def clamp_attr(value: int) -> int:
    return max(0, min(9999, value))


def apply_effects(state: dict[str, Any], effects: dict[str, Any] | None) -> dict[str, int]:
    landed: dict[str, int] = {}
    for key, delta in (effects or {}).items():
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            continue
        if key in CORE_ATTRS:
            before = int(state["attrs"].get(key, 0))
            state["attrs"][key] = clamp_attr(before + delta)
            landed[key] = state["attrs"][key] - before
        elif key == "AGE":
            before = int(state.get("age", 0))
            state["age"] = max(0, before + delta)
            landed[key] = state["age"] - before
        elif key == "LIF" and delta < 0:
            state["terminal"] = {
                "kind": "death",
                "reason": "Life force fell below survival.",
                "event_id": state.get("_current_event_id"),
            }
            landed[key] = delta
    return landed


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


def age_matches(event: dict[str, Any], age: int) -> bool:
    if "age" in event and event["age"] is not None:
        return int(event["age"]) == age
    if "age_range" in event and event["age_range"]:
        low, high = event["age_range"]
        return int(low) <= age <= int(high)
    return True


def matching_pool_entries(pack: dict[str, Any], age: int) -> dict[str, int]:
    matched: dict[str, int] = {}
    for key, items in pack.get("age_pools", {}).items():
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


def event_by_id(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(event.get("id")): event for event in pack.get("events", []) if isinstance(event, dict)}


def event_resolvable(event: dict[str, Any], state: dict[str, Any]) -> bool:
    event_id = str(event.get("id"))
    if not event.get("repeatable", False) and event_id in state.get("event_history", []):
        return False
    if not eval_condition(state, event.get("include")):
        return False
    if event.get("exclude") and eval_condition(state, event.get("exclude")):
        return False
    return True


def update_special_candidates(pack: dict[str, Any], state: dict[str, Any]) -> list[str]:
    added: list[str] = []
    special = list(state.get("special_candidates", []))
    special_set = set(str(item) for item in special)
    history = set(str(item) for item in state.get("event_history", []))
    for event in pack.get("events", []):
        event_id = str(event.get("id"))
        if not event.get("special_when"):
            continue
        if not event.get("repeatable", False) and (event_id in history or event_id in special_set):
            continue
        if eval_condition(state, event.get("special_when")):
            special.append(event_id)
            special_set.add(event_id)
            added.append(event_id)
    state["special_candidates"] = special
    return added


def collect_candidates(pack: dict[str, Any], state: dict[str, Any]) -> list[tuple[dict[str, Any], float]]:
    by_id = event_by_id(pack)
    age = int(state.get("age", 0))
    special_ids = [event_id for event_id in state.get("special_candidates", []) if event_id in by_id]
    special_candidates = []
    for event_id in special_ids:
        event = by_id[event_id]
        if event_resolvable(event, state):
            special_candidates.append((copy.deepcopy(event), float(event.get("weight", 1))))
    if special_candidates:
        return special_candidates

    pool_entries = matching_pool_entries(pack, age)
    has_age_pool = bool(pack.get("age_pools"))
    candidates: list[tuple[dict[str, Any], float]] = []
    for raw in pack.get("events", []):
        event = copy.deepcopy(raw)
        event_id = str(event.get("id"))
        authored_age = "age" in event or "age_range" in event
        if authored_age and not age_matches(event, age):
            continue
        if has_age_pool and event_id not in pool_entries and not authored_age:
            continue
        if event_id in state.get("special_candidates", []):
            continue
        if not event_resolvable(event, state):
            continue
        base = pool_entries.get(event_id, int(event.get("weight", 1)))
        candidates.append((event, max(0.1, float(base))))
    return candidates


def pick_event(candidates: list[tuple[dict[str, Any], float]], rng: random.Random) -> dict[str, Any]:
    total = sum(weight for _, weight in candidates)
    pick = rng.uniform(0, total)
    upto = 0.0
    for event, weight in candidates:
        upto += weight
        if pick <= upto:
            return event
    return candidates[-1][0]


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    event_id = str(event.get("id", "unknown_event"))
    before = copy.deepcopy(state)
    state["_current_event_id"] = event_id
    landed_effects = apply_effects(state, event.get("effects"))
    state.pop("_current_event_id", None)

    flags = set(str(item) for item in state.get("flags", []))
    flags.update(str(item) for item in event.get("set_flags", []) if isinstance(item, str))
    flags.difference_update(str(item) for item in event.get("clear_flags", []) if isinstance(item, str))
    state["flags"] = sorted(flags)

    if event.get("clear_terminal"):
        state["terminal"] = False
    if event.get("terminal"):
        tags = {str(tag) for tag in event.get("tags", [])}
        kind = "ascension" if "ascension" in tags else "death" if "old_age" in tags else "ending"
        state["terminal"] = {
            "kind": kind,
            "reason": event.get("terminal_reason") or event.get("title") or event_id,
            "event_id": event_id,
        }

    history = list(state.get("event_history", []))
    if event_id not in history:
        history.append(event_id)
    state["event_history"] = history

    if event_id in state.get("special_candidates", []) and not event.get("repeatable", False):
        state["special_candidates"] = [item for item in state.get("special_candidates", []) if item != event_id]

    state["turn"] = int(state.get("turn", 0)) + 1
    return {
        "event_id": event_id,
        "landed_effects": landed_effects,
        "flags_added": sorted(set(state.get("flags", [])) - set(before.get("flags", []))),
        "flags_removed": sorted(set(before.get("flags", [])) - set(state.get("flags", []))),
        "terminal": state.get("terminal"),
    }


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "age": state.get("age"),
        "attrs": state.get("attrs"),
        "talents": [talent.get("id") if isinstance(talent, dict) else talent for talent in state.get("talents", [])],
        "flags": state.get("flags", []),
        "event_history": state.get("event_history", []),
        "special_candidates": state.get("special_candidates", []),
        "terminal": state.get("terminal"),
    }


def create_state(pack: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    rng = random.Random(args.seed)
    attrs = {key: rng.randint(3, 7) for key in CORE_ATTRS}
    talents = weighted_sample_without_replacement(pack.get("talents", []), args.talents, rng)
    state = {
        "version": 1,
        "session_id": str(uuid.uuid4())[:12],
        "turn": 0,
        "age": args.age,
        "attrs": attrs,
        "talents": talents,
        "flags": [],
        "event_history": [],
        "special_candidates": [],
        "terminal": False,
        "rng_seed": args.seed,
    }
    for talent in talents:
        apply_effects(state, talent.get("effects"))
    update_special_candidates(pack, state)
    return state


def load_state_arg(value: str) -> dict[str, Any]:
    if value == "-":
        return json.loads(sys.stdin.read())
    stripped = value.lstrip()
    if stripped.startswith("{"):
        return json.loads(value)
    path = Path(value)
    try:
        if path.exists():
            return load_json(path)
    except OSError:
        pass
    return json.loads(value)


def summarize_candidates(candidates: list[tuple[dict[str, Any], float]], special_ids: set[str] | None = None) -> list[dict[str, Any]]:
    special_ids = special_ids or set()
    return [
        {
            "id": event.get("id"),
            "title": event.get("title"),
            "tags": event.get("tags", []),
            "weight": round(weight, 3),
            "special": str(event.get("id")) in special_ids,
        }
        for event, weight in candidates[:12]
    ]


def command_new(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = create_state(pack, args)
    print(dump({"state": state, "gm_instruction": "Render this as story, not JSON, unless the user asked for debug state."}))


def command_candidates(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = load_state_arg(args.state)
    added = update_special_candidates(pack, state)
    candidates = collect_candidates(pack, state)
    print(dump({
        "state": state,
        "special_candidates_added": added,
        "candidates": summarize_candidates(candidates, set(str(item) for item in state.get("special_candidates", []))),
        "gm_instruction": "Use candidates as event seeds only. Free-form user action still requires model judgment.",
    }))


def command_turn(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = load_state_arg(args.state)
    seed = state.get("rng_seed")
    rng = random.Random(f"{seed}:{state.get('turn', 0)}:{args.event_id or 'auto'}")
    added = update_special_candidates(pack, state)
    candidates = collect_candidates(pack, state)
    if not candidates:
        result = {
            "error": "no_matching_event",
            "state": state,
            "special_candidates_added": added,
            "gm_instruction": "No authored event fits. In Live Play, host manually with a manual_* event ID; do not pretend this script understood a free-form action.",
        }
        print(dump(result))
        raise SystemExit(2)

    if args.event_id:
        selected = next((event for event, _ in candidates if event.get("id") == args.event_id), None)
        if selected is None:
            result = {
                "error": "event_not_candidate",
                "requested_event_id": args.event_id,
                "state": state,
                "candidates": summarize_candidates(candidates, set(str(item) for item in state.get("special_candidates", []))),
            }
            print(dump(result))
            raise SystemExit(3)
    else:
        selected = pick_event(candidates, rng)

    selected = copy.deepcopy(selected)
    applied = apply_event(state, selected)
    update_special_candidates(pack, state)
    result = {
        "selected_event": selected,
        "applied_probe": applied,
        "state": state,
        "action_entries": selected.get("choices", [])[:4],
        "gm_instruction": "This is a state probe. In real Live Play, narrate the event and let its effects fail, partially land, or change when the user's action/state calls for it.",
    }
    if args.save:
        Path(args.save).write_text(dump(state) + "\n", encoding="utf-8")
    print(dump(result))


def command_demo(args: argparse.Namespace) -> None:
    pack = load_json(Path(args.pack))
    state = create_state(pack, args)
    print("# Demo State")
    print(dump(state_summary(state)))
    for index in range(args.turns):
        candidates = collect_candidates(pack, state)
        skipped_ages = []
        while not candidates and state.get("terminal") is False and int(state.get("age", 0)) < 120:
            state["age"] = int(state.get("age", 0)) + 1
            skipped_ages.append(state["age"])
            candidates = collect_candidates(pack, state)
        if not candidates:
            print(f"\n# Turn {index + 1}: no_matching_event")
            break
        rng = random.Random(f"{state.get('rng_seed')}:{state.get('turn', 0)}")
        event = pick_event(candidates, rng)
        age_before = state.get("age")
        applied = apply_event(state, copy.deepcopy(event))
        if state.get("terminal") is False and state.get("age") == age_before:
            state["age"] = int(state.get("age", 0)) + 1
        update_special_candidates(pack, state)
        print(f"\n# Turn {index + 1}: {event.get('title')}")
        payload = {"applied_probe": applied, "state": state_summary(state), "choices": event.get("choices", [])[:4]}
        if skipped_ages:
            payload["skipped_to_age"] = state.get("age")
        print(dump(payload))
        if state.get("terminal"):
            break


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Life Restart World v1 event probe")
    sub = p.add_subparsers(dest="command", required=True)

    def add_pack(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--pack", default=str(DEFAULT_PACK), help="content pack JSON path")

    new = sub.add_parser("new", help="create a new LifeState v1 object")
    add_pack(new)
    new.add_argument("--seed", type=int, default=None)
    new.add_argument("--age", type=int, default=0)
    new.add_argument("--talents", type=int, default=3, help="number of random talents to sample")
    new.set_defaults(func=command_new)

    candidates = sub.add_parser("candidates", help="show currently valid authored event candidates")
    add_pack(candidates)
    candidates.add_argument("--state", required=True, help="state JSON path, JSON string, or '-' for stdin")
    candidates.set_defaults(func=command_candidates)

    turn = sub.add_parser("turn", help="apply one authored event probe")
    add_pack(turn)
    turn.add_argument("--state", required=True, help="state JSON path, JSON string, or '-' for stdin")
    turn.add_argument("--event-id", help="specific candidate event id to apply")
    turn.add_argument("--save", help="optional path to save updated state")
    turn.set_defaults(func=command_turn)

    demo = sub.add_parser("demo", help="run a small authored-event probe")
    add_pack(demo)
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--age", type=int, default=0)
    demo.add_argument("--talents", type=int, default=3)
    demo.add_argument("--turns", type=int, default=5)
    demo.set_defaults(func=command_demo)
    return p


def main() -> int:
    args = parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
