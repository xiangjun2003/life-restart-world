# Content Pack Schema

Content packs are event seed libraries. They help the Game Master find age/state-appropriate material, but they are not a complete engine and do not force outcomes.

## Top-Level Shape

```json
{
  "version": 1,
  "id": "classic-lite",
  "title": "Classic Lite",
  "license": "Original content unless source is specified.",
  "compatible_world_tags": ["classic", "realistic", "school", "cultivation"],
  "attributes": {},
  "talents": [],
  "events": [],
  "age_pools": {}
}
```

`compatible_world_tags` is diagnostic. If a custom world does not match a pack, the Game Master may still host manually, but tests should report the mismatch.

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

Talent `effects` apply to `attrs` when the life begins. Talents also bias story interpretation and failure modes.

## Event

```json
{
  "id": "teacher_notice",
  "title": "被老师注意",
  "age_range": [7, 12],
  "weight": 10,
  "repeatable": false,
  "include": "INT>=6",
  "exclude": "flags?[dropped_out]",
  "tags": ["education", "mentor"],
  "effects": {"INT": 1, "SPR": 1},
  "set_flags": ["teacher_noticed", "exam_path"],
  "clear_flags": [],
  "narrative_seed": "A teacher notices the child making unusual effort with limited resources.",
  "choices": [
    "Lean into study and ask for guidance",
    "Hide the attention to avoid family pressure",
    "Trade study time for money"
  ],
  "source": "optional attribution"
}
```

`effects` are a typical or intended result. In Live Play, the model can turn them into success, failure, partial success, cost, or reversal when the user's action and state justify it.

## Special Candidate Events

Use `special_when` for prerequisite branches. When the condition becomes true, add the event ID to `LifeState.special_candidates`. Resolve special candidates before ordinary age-pool events.

```json
{
  "id": "ascension_gate",
  "title": "飞升之门",
  "age_range": [80, 500],
  "weight": 4,
  "repeatable": false,
  "special_when": "flags?[found_hidden_manual]",
  "include": "flags?[existence_cultivator]&INT>=10&STR>=8",
  "tags": ["cultivation", "ascension", "ending"],
  "effects": {"SPR": 3},
  "set_flags": ["ascended_from_human_world", "existence_ascended"],
  "clear_flags": ["existence_cultivator"],
  "terminal": true,
  "terminal_reason": "The human-life arc ends in ascension.",
  "narrative_seed": "The character steps beyond the human world; the life can end here or continue in a higher realm.",
  "choices": ["Summarize the human life", "Continue into the higher realm", "Choose one talent to inherit"]
}
```

Special candidate rules:

- `special_when` only unlocks the candidate.
- `include` still gates whether it can resolve now.
- `exclude` can still block it.
- remove it from `special_candidates` after resolution unless `repeatable` is true.
- do not show the candidate list to the player unless they ask for raw state.

## Event Fields

- `id`: required stable string.
- `title`: required human-readable label.
- `age` or `age_range`: optional age gate. Omit for timeless events.
- `weight`: random or ranking weight before action relevance.
- `repeatable`: default `false`.
- `include`: condition that must pass for resolution.
- `exclude`: condition that blocks resolution when true.
- `special_when`: condition that queues the event into `special_candidates`.
- `tags`: thematic/action tags for candidate search.
- `effects`: numeric deltas for `CHR`, `INT`, `STR`, `MNY`, `SPR`, `LUK`, `AGE`, or `LIF`.
- `set_flags`: flags to add if the result lands that way.
- `clear_flags`: flags to remove if the result lands that way.
- `terminal`: whether this event can close the current arc.
- `clear_terminal`: whether this event can reopen play after a prior terminal/transformation branch.
- `terminal_reason`: player-facing reason for terminal state.
- `narrative_seed`: factual seed for model narration.
- `choices`: 2-4 possible next action openings. The model may rewrite or replace them.
- `source`: optional attribution, especially for imported MIT content.

Unsupported old-ledger fields such as `relationships`, `pressure_clocks`, `evidence`, `open_threads`, `close_threads`, `realm`, `realm_transition`, `existence_state`, and `life_cap` do not belong in v1 event packs.

## Conditions

Use a small expression language:

- Comparisons: `AGE>=18`, `INT>7`, `MNY<=3`.
- Membership: `flags?[teacher_noticed]`, `EVT?[40001,40050]`, `TLT?[early_reader]`.
- Negative membership: `flags![dropped_out]`.
- Boolean operators: `&`, `|`, parentheses.

`AGE` reads `state.age`. Attribute names read `state.attrs`. `EVT` reads `event_history`. `TLT` reads talent IDs.

Prefer simple conditions for hand-authored packs.
