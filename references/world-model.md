# World Model

The simulator is narrative-first but stateful. Every turn must preserve a structured ledger. The ledger is the minimum viable engine: if helper scripts or event packs are unavailable or unsuitable, continue by maintaining this state directly.

## Canonical State

```json
{
  "version": 1,
  "session_id": "life-001",
  "turn": 0,
  "pace": "standard",
  "age": 0,
  "time": {"label": "0岁", "scale": "years"},
  "life_cap": 100,
  "existence_state": "mortal",
  "realm": "human_world",
  "world": {
    "style": "realistic",
    "premise": "ordinary life with rare legendary branches",
    "session_note": {
      "tone": "grounded with rare legendary branches",
      "state_axes": ["education_path", "family_pressure"],
      "pressure_clocks": {}
    }
  },
  "attributes": {
    "CHR": 4,
    "INT": 6,
    "STR": 5,
    "MNY": 4,
    "SPR": 5,
    "LUK": 5,
    "WIL": 5
  },
  "talents": [],
  "relationships": {},
  "pressure_clocks": {},
  "evidence": {},
  "flags": [],
  "event_history": [],
  "open_threads": [],
  "timeline": [],
  "terminal": false,
  "terminal_reason": null
}
```

## Attributes

- `CHR`: presence, charm, appearance, social first impression.
- `INT`: learning, reasoning, planning.
- `STR`: health, physical resilience.
- `MNY`: family resources and later personal resources.
- `SPR`: happiness, morale, emotional energy.
- `LUK`: fortune, unlikely help, odd survivals.
- `WIL`: willpower, discipline, persistence under cost.
- `LIF`: life force. Usually implicit as alive unless an event uses it.

Keep attributes roughly in a `0-10` human range unless the world has crossed into cultivation, immortal, post-human, or other legendary states.

## Existence States

Do not hard-cap lives at 100.

- `mortal`: ordinary human life.
- `resurrected`: returned after a death or near-death terminal branch.
- `cultivator`: life cap can extend to hundreds of years.
- `immortal`: aging is no longer the main pressure.
- `ascended`: the human-life arc has ended; optionally begin a higher-realm arc.
- `post_human`: transformed beyond ordinary human categories.

Use `life_cap` as the current expected maximum, not as an absolute. Events may raise it, lower it, or end the arc before it is reached.

## Pace

Default `standard` pace should produce about 25-45 meaningful turns.

- `detailed`: 40-70 turns; use 1 year or smaller critical beats often.
- `standard`: 25-45 turns; use yearly turns in youth, then larger life beats.
- `fast`: 10-18 turns; use compressed arcs.

Age increments are not rigid. A turn is a meaningful life beat. Youth usually moves slower than later adulthood. Supernatural states may use decades or realm breakthroughs as beats.

For `standard` pace, a useful default is:

- Ages 0-6: 1-2 years per turn unless a childhood scene is important.
- Ages 7-22: usually 1 year per turn.
- Ages 23-45: 1-2 years per turn.
- Ages 46-70: 2-4 years per turn.
- Ages 70+: 3-7 years per turn, unless a terminal or relationship scene needs focus.
- Cultivation, ascension, immortality, and post-human play can use breakthroughs, eras, or realm transitions instead of calendar years.

## State Discipline

- Put durable facts in `flags`, not only in prose.
- Put unresolved goals or tensions in `open_threads`.
- Put recurring people in `relationships` with a score from `-5` to `5` and a short note when helpful.
- Put slow pressure in `pressure_clocks` when a binary flag is too crude.
- Put investigable claims, proofs, objects, and witness chains in `evidence` when flags are too flat.
- Use `time` when several meaningful turns happen inside the same age.
- Put all triggered event IDs in `event_history`.
- Put each turn's story summary in `timeline`.
- Keep `event_history` and `timeline` aligned. A manual ruling should still have a `manual_*` event id in both places.
- If many turns share the same `age`, add `time` so the order stays playable.
- Close stale `open_threads` when a later event resolves or supersedes them; the snapshot should show the current board, not every idea that ever appeared.

Relationship entries should be small but explicit:

```json
{
  "mother": {
    "score": 2,
    "note": "protective, worried about money",
    "tensions": ["angry about secrecy", "still protective"]
  },
  "teacher_li": {"score": 3, "note": "sees promise and expects discipline"},
  "classmate_chen": {"score": -1, "note": "resentful after a public comparison"}
}
```

Pressure clocks should include `stage`, `limit`, and `meaning`. They are best for exam deadlines, debt, illness, political danger, sect suspicion, burnout, or other tensions that should build over several turns. If a clock reaches its limit, either trigger its consequence soon or record `last_consequence` / `status` so the ledger shows it was honored.

Pressure clocks can count down only when the clock meaning is phrased as a deficit or risk, such as "evidence gap" or "debt pressure". They are not a generic progress bar. For proof quality, prefer `evidence` entries with `status`, `holders`, and chain notes, then close or resolve the pressure clock when the evidence gap is handled.

Evidence entries are optional but useful for investigative worlds:

```json
{
  "father_cartridge": {
    "claim": "The company knew the upper-dome leak was being blamed on low-sector demand.",
    "status": "copied_and_witnessed",
    "holders": ["mother", "rui", "school_archive"],
    "risk": "high"
  }
}
```

Evidence should include enough custody to matter in play: at minimum a `claim` or `status`, plus `holders` when someone knows, stores, or can contest it.

Use `time` when age is too coarse:

```json
{
  "age": 16,
  "time": {"label": "16岁，高三前夜", "scale": "school_term", "beat": 7}
}
```

If multiple playable turns share the same `age`, add `time` to the state and to the relevant timeline items. The current state-level `time` tells where play is now; timeline item times preserve the order of past beats.

## Prologue State

For later-age starts, include a short prologue in `timeline` and derive state from it. Do not start at a later age with an empty history unless the premise explicitly involves amnesia, artificial creation, or missing records.

Example prologue timeline item:

```json
{
  "turn": "prologue",
  "age": 7,
  "event_id": "teacher_notice",
  "summary": "A teacher noticed the child's unusual reading speed and lent old exam papers.",
  "effects": {"INT": 1, "relationship:teacher": 2},
  "flags": ["teacher_noticed"]
}
```
