# Content Pack Schema

Content packs are JSON files. They are data, not prompts. The Game Master uses them to ground events and state changes.

Top-level compatibility fields help tests expose mismatches. They do not force a custom world to use the pack.

## Validation

Run the lightweight integrity checker after editing, importing, or selecting a pack for script-assisted tests:

```bash
python3 scripts/validate_content_pack.py references/content-packs/classic-lite.json
```

The checker reports duplicate IDs, age-pool references to missing events, malformed age ranges, bad field types, evidence without usable holders, and similar pack problems. Treat `errors` as test blockers. Treat `warnings` as review prompts that may still be acceptable for imported upstream data or intentionally sparse reference material.

Passing validation does not make the pack a canonical engine. The Game Master still maintains the state ledger and may manually adjudicate custom worlds when no matching event material exists.

## Top-Level Shape

```json
{
  "version": 1,
  "id": "classic-lite",
  "title": "Classic Lite",
  "license": "Original content unless source is specified.",
  "compatible_realms": ["human_world"],
  "compatible_world_tags": ["classic", "realistic", "school", "cultivation"],
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
  "relationships": {
    "mentor_teacher": {"delta": 1, "note": "quietly opens a harder path"}
  },
  "pressure_clocks": {
    "exam_deadline": {"delta": 1, "limit": 4, "meaning": "升学压力逐步逼近"}
  },
  "evidence": {
    "computer_room_permission": {"status": "witnessed", "holders": ["mentor_teacher"]}
  },
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

## Top-Level Compatibility

- `compatible_realms`: realms this pack can reasonably support, such as `human_world` or `higher_realm`.
- `compatible_world_tags`: broad world tags this pack is meant to cover. Use these for diagnostics, not for hard narrative control.

## Event Fields

- `age` or `age_range`: match by current age. Use `null` for timeless events.
- `age_advance`: optional. Set to `none` for immediate, same-week, or transition events that should not consume years in helper-script stepping. The Game Master should still maintain `time` when several playable turns share the same age.
- `realm`: omit or set to `any` to match all realms.
- `weight`: random weight before action relevance.
- `repeatable`: default `false`.
- `include`: condition that must pass.
- `exclude`: condition that blocks the event when true.
- `tags`: used for action relevance and thematic continuity.
- `effects`: numeric attribute deltas. `LIF <= -1` can end a mortal life.
- `relationships`: relationship score updates keyed by person or faction. Use `{"delta": 1, "note": "..."}` for relative changes or `{"score": 2}` for absolute assignment.
- `pressure_clocks`: slow-tension updates keyed by clock ID. Use `{"delta": 1, "limit": 4, "meaning": "..."}`, `{"set_stage": 2}`, `{"status": "resolved"}`, `{"last_consequence": "..."}`, or `{"close": true}`. Helper scripts mark a clock as `status: filled` when it reaches its limit and no consequence/status is supplied.
- `evidence`: optional evidence updates keyed by evidence ID. Use small entries with `claim`, `status`, `holders`, and optional `risk`.
- `set_flags`, `clear_flags`, `open_threads`, `close_threads`: durable state changes.
- `life_cap`: set or raise current life cap.
- `existence_state`: set a new existence state.
- `realm_transition`: move to a new realm.
- `terminal`: end the current arc.
- `clear_terminal`: reopen play after a terminal transition when starting a new arc, such as continuing after ascension.
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
