# Content Pack Schema

Content packs are JSON files. They are data, not prompts. The Game Master uses them to ground events and state changes.

## Top-Level Shape

```json
{
  "version": 1,
  "id": "classic-lite",
  "title": "Classic Lite",
  "license": "Original content unless source is specified.",
  "attributes": {},
  "talents": [],
  "events": [],
  "age_pools": {}
}
```

## Talent

```json
{
  "id": "early_reader",
  "name": "早慧",
  "description": "你很早学会从书里寻找出口。",
  "grade": 1,
  "effects": {"INT": 1, "SPR": -1},
  "tags": ["education"],
  "exclude": []
}
```

## Event

```json
{
  "id": "teacher_notice",
  "title": "被老师注意",
  "age_range": [7, 12],
  "realm": "human_world",
  "weight": 10,
  "repeatable": false,
  "include": "INT>=6",
  "exclude": "flags?[dropped_out]",
  "tags": ["education", "mentor"],
  "effects": {"INT": 1, "SPR": 1},
  "set_flags": ["teacher_noticed"],
  "open_threads": ["exam_path"],
  "narrative_seed": "A teacher notices the child making unusual effort with limited resources.",
  "choices": [
    "Lean into study and ask for guidance",
    "Hide the attention to avoid family pressure",
    "Trade study time for money"
  ]
}
```

## Event Fields

- `age` or `age_range`: match by current age. Use `null` for timeless events.
- `realm`: omit or set to `any` to match all realms.
- `weight`: random weight before action relevance.
- `repeatable`: default `false`.
- `include`: condition that must pass.
- `exclude`: condition that blocks the event when true.
- `tags`: used for action relevance and thematic continuity.
- `effects`: numeric attribute deltas. `LIF <= -1` can end a mortal life.
- `set_flags`, `clear_flags`, `open_threads`, `close_threads`: durable state changes.
- `life_cap`: set or raise current life cap.
- `existence_state`: set a new existence state.
- `realm_transition`: move to a new realm.
- `terminal`: end the current arc.
- `terminal_reason`: summary for endings.
- `narrative_seed`: factual seed for story rendering.
- `choices`: next action entries.
- `source`: optional attribution, especially for imported MIT content.

## Conditions

Use a small expression language compatible with the original project:

- Comparisons: `AGE>=18`, `INT>7`, `MNY<=3`.
- Equality: `realm=human_world`, `existence_state!=mortal`.
- Membership: `flags?[teacher_noticed]`, `EVT?[40001,40050]`, `TLT?[early_reader]`.
- Negative membership: `flags![dropped_out]`.
- Boolean operators: `&`, `|`, parentheses.

Prefer simple conditions for hand-authored packs.
