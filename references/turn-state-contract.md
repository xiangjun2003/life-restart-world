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
- flags and event history,
- open threads,
- terminal or post-terminal state.

The player-facing snapshot can be compact, but the internal state must stay explicit.

## Intent

Convert the user's action into a semantic intent:

```json
{
  "summary": "ask the teacher for computer-room access while hiding the part-time job",
  "selected_entry": 3,
  "modifiers": ["partial truth", "protect family from worry"],
  "tags": ["study", "technology", "relationship", "secret"],
  "risk": "medium",
  "checks": ["INT", "CHR", "WIL"],
  "desired_outcome": "legitimate computer access without exposing the job"
}
```

If the user says "选 2，但..." preserve both the selected entry and the modification. If the user ignores the entries, parse the free-form action directly.

## Resolution

Resolve from these inputs, in order:

1. Current state ledger.
2. User intent.
3. Session world note.
4. Matching event material, if any.
5. Genre expectations and safety boundaries.

The chosen event material is a seed, not the whole answer. If no authored event fits, create a state-led ruling from the ledger and label script/content gaps during tests.

## Delta

Every durable story consequence must appear in the delta.

```json
{
  "age": [14, 15],
  "attributes": {"INT": 1, "SPR": 1},
  "relationships": {
    "mentor_teacher": {"delta": 1, "note": "offers supervised lab time"}
  },
  "pressure_clocks": {
    "secrecy_risk": {"delta": -1, "limit": 4, "meaning": "秘密行动被发现的风险"}
  },
  "flags_added": ["authorized_lab_time"],
  "flags_removed": [],
  "threads_added": [],
  "threads_closed": [],
  "event_material": ["school_computer_room_access"],
  "timeline_item": "15岁：你用半真半假的坦白换来每周一次机房边角时间。"
}
```

Prefer small deltas. A vivid scene does not need many flags, but any fact that changes future play must be tracked.

## State Snapshot

After applying the delta, show a compact snapshot:

- age, realm, existence state, and life cap when relevant,
- key attributes that changed or matter now,
- 2-5 active relationships or factions,
- 2-5 open threads or pressure clocks,
- terminal status if the arc has ended or transformed.

Do not print the full JSON ledger unless the user asks for debug/raw state.

## Action Entries

Offer 2-4 entries. They should be affordances, not a menu lock.

Good spread:

- a steady or conservative action,
- a risky or costly action,
- a relationship, faction, or honesty action,
- a world-specific or talent-specific action when justified.

Avoid four cosmetic variants of the same plan. Each entry should imply a different cost, ally, risk, or future thread.

## Turn Checklist

Before sending the turn:

- Did the user's free-form intent survive, or was it collapsed into the nearest listed option?
- Did every durable story fact land in attributes, relationships, flags, clocks, threads, timeline, terminal state, or realm?
- Did any pressure clock advance, reduce, fill, or close?
- Are action entries plausible from the updated state?
- If script/content material failed, is that failure named during tests instead of hidden?
