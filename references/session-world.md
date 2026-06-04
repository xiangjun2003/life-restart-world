# Session World Note

Use this for custom worlds when a full content pack would be too heavy. The note keeps the Game Master consistent while leaving narrative room open.

The session world note is reference material, not an engine. It should constrain interpretation, event selection, and consequences, but the canonical play state remains the state ledger.

## Minimal Shape

```json
{
  "premise": "A 12-year-old in a 1990s county town wants to change family fate through study and early computer access.",
  "tone": "grounded with rare legendary branches",
  "scale": "family, school, county, later city",
  "boundaries": ["no effortless success", "money pressure is persistent"],
  "state_axes": ["education_path", "family_pressure", "money_vs_study", "self_belief"],
  "factions": {
    "family": "protective but cash-strapped",
    "school": "limited resources, one perceptive teacher",
    "local_market": "small chances to earn money with social risk"
  },
  "pressure_clocks": {
    "exam_deadline": {"stage": 1, "limit": 4, "meaning": "升学压力逐步逼近"},
    "family_debt": {"stage": 1, "limit": 5, "meaning": "家里经济余地变窄"}
  },
  "evidence_tracks": [],
  "event_seeds": [
    "teacher notices unusual effort",
    "secret work conflicts with study",
    "a used computer becomes possible but risky"
  ],
  "likely_choices": ["study", "earn money", "seek help", "hide or reveal pressure"],
  "terminal_paths": ["ordinary adulthood", "class mobility", "burnout", "legendary branch"]
}
```

Keep it short. A good note fits in one screen and can be updated when the user adds decisive world facts.

## Validation

`scripts/validate_state.py` checks the basic shape of `world.session_note` when it is present. For custom or no-pack worlds, expect warnings if the note is missing, has no `state_axes`, or has no `factions`.

Keep active pressure in the protagonist ledger. If `world.session_note.pressure_clocks` names a live clock, mirror it in top-level `pressure_clocks`; otherwise the note has become hidden state instead of context.

## When To Create One

Create or update a session world note when:

- The user names a custom world or unusual premise.
- The available content pack only partially matches the world.
- A later-age start needs a coherent backstory.
- A recurring faction, rule, taboo, resource, or pressure must stay stable.

Do not require a session world note for a quick original-style run if the user wants to start immediately.

## How It Affects Play

- `premise`, `tone`, and `boundaries` guide what counts as plausible.
- `state_axes` become good candidates for `flags`, `open_threads`, and state summaries.
- `state_axes` are ledger design axes, not content-pack compatibility tags. If a custom world needs compatibility diagnostics, put explicit tags in `tags`, `world_tags`, or `compatibility_tags`.
- `factions` help relationships and consequences stay specific.
- `pressure_clocks` model slow-moving threats without forcing scripted events.
- `evidence_tracks` remind the Game Master when proof, witnesses, artifacts, or credibility matter.
- `event_seeds` provide authored-feeling material when no content-pack event fits.
- `terminal_paths` remind the Game Master that endings can be social, emotional, supernatural, or transitional.

If an event pack disagrees with the session world note, prefer the note for this session and report the mismatch during tests.

## Pressure Clocks

Pressure clocks are lightweight counters for unresolved tension.

```json
{
  "id": "exam_deadline",
  "stage": 2,
  "limit": 4,
  "meaning": "The entrance exam pressure is becoming visible.",
  "on_fill": "force an exam crossroads or equivalent consequence"
}
```

Advance a clock when the character delays, pays a cost, takes a risky shortcut, or an external deadline approaches. Reduce or close a clock only when the story and state ledger both justify it.

## Choice Design

Each turn should offer 2-4 action entries that are genuinely different. Prefer this spread:

- One steady or conservative action.
- One risky, ambitious, secret, or costly action.
- One relationship or faction-facing action.
- One world-specific, talent-specific, or strange action when appropriate.

Entries are affordances. The user can always ignore, combine, or modify them in natural language.
