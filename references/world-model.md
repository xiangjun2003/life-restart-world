# World Model

Live Play uses a small LifeRestart-like state. The state exists to keep consequences stable; it is not a full world database and not a transcript.

## LifeState v1

Canonical shape:

```json
{
  "version": 1,
  "age": 0,
  "attrs": {
    "CHR": 4,
    "INT": 6,
    "STR": 5,
    "MNY": 4,
    "SPR": 5,
    "LUK": 5
  },
  "talents": [],
  "flags": [],
  "event_history": [],
  "special_candidates": [],
  "terminal": false
}
```

Optional developer fields such as `session_id`, `turn`, `rng_seed`, or `notes` may appear in tool output, but the Game Master should not depend on them during ordinary play. Do not add relationship boards, pressure clocks, evidence objects, phase summaries, or open-thread lists in v1.

## Attributes

- `CHR`: charm, appearance, presence, and social first impression.
- `INT`: learning, reasoning, planning, technical ability.
- `STR`: health, physical resilience, stamina.
- `MNY`: family resources and later personal resources.
- `SPR`: happiness, morale, emotional energy.
- `LUK`: fortune, unlikely help, strange survivals.

Keep ordinary human attributes roughly in `0-10`. Legendary, cultivation, immortal, or post-human arcs may exceed that range when flags and narration justify it.

`LIF` can appear in event `effects` as a life-force shortcut. It is not stored as a normal attribute. If an event or ruling reduces `LIF` below survival, set `terminal`.

## Talents

Talents are compact traits that bias interpretation. They may be strings or small objects with `id`, `name`, `description`, `effects`, and `tags`.

Examples:

```json
[
  {"id": "early_reader", "name": "早慧", "effects": {"INT": 1, "SPR": -1}},
  "root_of_cultivation"
]
```

During play, talents should create opportunities, costs, temptations, and failure modes. They do not guarantee success.

## Flags

Flags are the main durable memory surface. Use them for:

- traits and conditions that should keep affecting play,
- old relationship facts reduced to simple memory,
- current goals or pressures,
- acquired resources or scars,
- supernatural transitions,
- special branch prerequisites.

Good flags are short and reusable:

```json
[
  "teacher_noticed",
  "family_money_pressure",
  "computer_curiosity",
  "existence_cultivator",
  "ascended_from_human_world"
]
```

Do not put every sentence into flags. Add a flag only when it can change a later event, choice, failure, or ending.

## Event History

`event_history` records event IDs that already mattered. It supports:

- preventing one-time events from repeating,
- unlocking prerequisite branches,
- explaining later-age starts,
- summarizing what the character has already lived.

Manual or model-created events should still have stable IDs, usually `manual_*`, such as `manual_prologue_secret_savings` or `manual_failed_get_rich_scheme`.

## Special Candidates

`special_candidates` is a short list of event IDs that have been unlocked but not yet resolved.

Use it for events with prerequisite chains:

1. A normal event, flag, talent, or player action satisfies the event's `special_when` condition.
2. Add the event ID to `special_candidates`.
3. When choosing next event material, check `special_candidates` before ordinary age candidates.
4. If the event is resolved, remove it unless the event is `repeatable: true`.

Example:

```json
{
  "flags": ["found_hidden_manual"],
  "event_history": ["hidden_manual"],
  "special_candidates": ["ascension_gate"]
}
```

Do not let `special_candidates` become a quest log. Keep it to genuinely unlocked branches that deserve priority when the next scene is offered.

## Terminal

`terminal` is `false` while the current arc is active. When the life or human-life arc ends, set it to an object:

```json
{
  "kind": "death",
  "reason": "The life closes in old age.",
  "event_id": "ordinary_old_age"
}
```

Useful `kind` values include `death`, `ending`, `ascension`, `transformation`, `failure`, and `retirement`.

If play continues after resurrection, ascension, reincarnation, or a higher-realm start, clear `terminal` back to `false` and add flags/event history that explain the new active arc.

## Age And Long-Life Branches

Do not hard-cap age at 100. Age is just the current time marker.

When play continues beyond ordinary human limits, the state must explain why through flags and event history, for example:

```json
{
  "age": 160,
  "flags": ["found_hidden_manual", "existence_cultivator", "life_extended"],
  "event_history": ["hidden_manual", "manual_life_extension_breakthrough"],
  "terminal": false
}
```

For immortal or post-human arcs, age may become symbolic, but keep it as a number for compatibility. Use narration to explain eras, realms, or transformations.

## State Discipline

- Initialize `LifeState v1` before the first playable scene. Do not run a scene against a blank or purely implied state.
- After every resolved scene, consider every core field and keep the current state internally current, even if no visible state panel is shown.
- Update `age` when the scene meaningfully advances time. This can be one year, several years, decades, or no time at all for an immediate crisis follow-up.
- Update `attrs` when a durable ability, resource, health, morale, or luck state changes.
- Update `flags` when a fact should affect future rulings.
- Update `event_history` whenever an authored or manual event materially resolves.
- Update `special_candidates` when prerequisite branches unlock or resolve.
- Update `terminal` when an arc closes.
- If the player asks for current state, show a compact readable state summary. Show raw JSON only if they explicitly ask for raw state.

The model may remember richer story context through conversation. The state only tracks facts that need rule-level continuity.
