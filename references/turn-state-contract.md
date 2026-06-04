# Turn State Contract

Use this when hosting playable turns. It keeps the game flexible while making the protagonist state auditable.

The contract is not a script format the user must see. It is the Game Master's internal order of operations.

## Canonical Ledger

Before resolving a turn, read the existing state ledger. Do not reconstruct the character from the latest prose alone.

Carry forward:

- identity and current situation,
- attributes and talents,
- relationships,
- pressure clocks,
- time marker and evidence, when the current world needs them,
- flags and event history,
- open threads,
- terminal or post-terminal state.

The player-facing snapshot can be compact, but the internal state must stay explicit.

## Intent

Convert the user's action into a semantic intent:

```json
{
  "summary": "ask the teacher for computer-room access while hiding the part-time job",
  "source": "modified_entry",
  "selected_entry": 3,
  "modifiers": ["partial truth", "protect family from worry"],
  "targets": ["mentor_teacher", "computer_room", "family"],
  "tags": ["study", "technology", "relationship", "secret"],
  "risk": "medium",
  "checks": ["INT", "CHR", "WIL"],
  "desired_outcome": "legitimate computer access without exposing the job"
}
```

If the user says "选 2，但..." preserve both the selected entry and the modification. If the user ignores the entries, parse the free-form action directly.

Use `source` to avoid accidentally turning free play into menu play:

- `entry`: the user selected an entry without changing it.
- `modified_entry`: the user selected an entry but changed means, target, honesty, timing, or risk.
- `freeform`: the user acted outside the entries.
- `implicit_default`: the user gave no action and the Game Master advanced from state.

During playtests, debug output, or handoff, you may store the resolved intent as optional `last_intent` on the state ledger. It is a one-turn audit trace, not protagonist history; replace it each turn or omit it in ordinary play. Use it to prove that a `modified_entry` kept the user's modifiers and that a `freeform` action was not squeezed into a nearby menu entry.

## Resolution

Resolve from these inputs, in order:

1. Current state ledger.
2. User intent.
3. Session world note.
4. Matching event material, if any.
5. Genre expectations and safety boundaries.

The chosen event material is a seed, not the whole answer. If no authored event fits, create a state-led ruling from the ledger and label script/content gaps during tests.

When a turn is manually adjudicated, still write an event-shaped trace into the ledger. Use an id such as `manual_preschool_self_management` or `manual_ethics_meeting`, add it to `event_history`, and include a matching `timeline` item.

When authored and manual material both matter, keep both visible. A composite turn can list multiple event IDs, for example `["exam_crossroads", "manual_family_confession"]` in `event_history` and `"exam_crossroads + manual_family_confession"` in the timeline item's `event_id`.

## Delta

Every durable story consequence must appear in the delta.

```json
{
  "age": [14, 15],
  "time": ["14岁秋", "15岁春"],
  "attributes": {"INT": 1, "SPR": 1},
  "relationships": {
    "mentor_teacher": {"delta": 1, "note": "offers supervised lab time"}
  },
  "pressure_clocks": {
    "secrecy_risk": {"delta": -1, "limit": 4, "meaning": "秘密行动被发现的风险"}
  },
  "evidence": {
    "computer_room_permission": {"status": "witnessed", "holders": ["mentor_teacher"]}
  },
  "flags_added": ["authorized_lab_time"],
  "flags_removed": [],
  "threads_added": [],
  "threads_closed": [],
  "phase_summary": null,
  "event_material": ["school_computer_room_access"],
  "timeline_item": "15岁：你用半真半假的坦白换来每周一次机房边角时间。"
}
```

Prefer small deltas. A vivid scene does not need many flags, but any fact that changes future play must be tracked.

As attributes rise, diversify rewards. Once an ordinary mortal attribute is already high for the current world, reward further competent choices with relationship trust, evidence quality, pressure relief, resources, opened/closed threads, or phase outcomes instead of another attribute increase. Attribute gains should mark real development, not every successful action.

Keep relationship scores within `-5..5`. Do not keep every named person or faction active forever; archive inactive contacts into `phase_summaries`, relationship notes, evidence holders, or timeline summaries so the current relationship board stays playable.

## State Snapshot

After applying the delta, show a compact snapshot:

- age, realm, existence state, and life cap when relevant,
- key attributes that changed or matter now,
- 2-5 active relationships or factions,
- 2-5 open threads or pressure clocks,
- important evidence or time markers when they drive the next turn,
- terminal status if the arc has ended or transformed.

Do not print the full JSON ledger unless the user asks for debug/raw state.

For save/resume or agent handoff, provide a checkpoint capsule instead of the full ledger. The checkpoint should preserve the current playable state: session id, turn, age/time, realm/existence state, attributes, talents, active relationships, clocks, evidence, flags, open threads, recent timeline, and next affordances. Keep older resolved history summarized unless it still affects play.

When resuming, expand compact checkpoint notation into full ledger objects before validating or resolving the next turn. Do not leave active clocks as `"3/4"` strings or evidence as bare labels in the reconstructed state.

If an ordinary mortal attribute rises outside the usual human range, either justify it in `attribute_notes` or slow/clamp future deltas. A note can say why the value is exceptional and what future ordinary successes should stop increasing.

For phase closure, write a `phase_summary` or add an item to `phase_summaries` with a stable `id`. Close resolved threads rather than leaving them in the active board. A thread listed in `closed_threads` should not still appear in `open_threads` unless the story explicitly reopened it as a new active problem. Carry forward only tensions that can drive the next turn.

## Action Entries

Offer 2-4 entries. They should be affordances, not a menu lock.

Player-facing entries can be short natural-language lines, but each one should have an internal intent preview:

```json
{
  "label": "打听机房有没有边角时间，但先问清老师的规矩",
  "tags": ["technology", "mentor", "boundary"],
  "targets": ["mentor_teacher", "computer_room"],
  "state_hooks": ["computer_curiosity", "mentor_teacher", "exam_deadline"],
  "risk": "low"
}
```

Do not show this JSON during ordinary play. Use it as a design check and as optional checkpoint detail when another agent must resume the same board.

During playtests or debug handoff, you may store these objects as optional `next_affordances` on the state ledger before running `scripts/validate_state.py`. Ordinary live play does not need to show or persist them every turn, but the QA field helps catch duplicate labels, missing state hooks, and cosmetic variants.

Good spread:

- a steady or conservative action,
- a risky or costly action,
- a relationship, faction, or honesty action,
- a world-specific or talent-specific action when justified.

Avoid four cosmetic variants of the same plan. Each entry should imply a different cost, ally, risk, or future thread.

Each entry should touch at least one current or plausible ledger hook: an attribute under pressure, a relationship, a pressure clock, evidence, a flag, an open thread, the realm, or terminal/transition state. If an entry would not change or test the state in any way, rewrite it as scene color or omit it.

Use stable hook names. Good `state_hooks` usually reference existing attribute keys, relationship IDs, pressure clock IDs, evidence IDs, flags, open threads, or `world.session_note.state_axes`. A future hook is allowed only when the action is explicitly trying to open that thread or create that evidence; if validation warns about it, make sure the next delta creates or rejects that hook plainly.

## Turn Checklist

Before sending the turn:

- Did the user's free-form intent survive, or was it collapsed into the nearest listed option?
- Did the intent `source` match how the user acted?
- Did every durable story fact land in attributes, relationships, flags, clocks, threads, timeline, terminal state, or realm?
- Did evidence, proof, promises, or physical objects need an `evidence` entry instead of only a flag?
- If multiple turns happen at the same age, did the time marker or timeline make the sequence clear?
- Did any pressure clock advance, reduce, fill, or close?
- If this turn closed a phase, did stale threads move into a phase summary instead of staying active?
- If an attribute is outside the ordinary range, did the ledger explain it with `attribute_notes` or clamp future gains?
- Are action entries plausible from the updated state?
- If this is a save/resume/handoff moment, is there a checkpoint concise enough to copy but complete enough to continue?
- If script/content material failed, is that failure named during tests instead of hidden?
