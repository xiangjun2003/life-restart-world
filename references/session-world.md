# Session World Note

Use this only when a custom world needs a compact consistency note. It is not part of `LifeState v1` and should not become hidden state.

A good note helps the Game Master interpret plausibility, tone, social forces, and event style while the actual mechanical continuity stays in `age`, `attrs`, `talents`, `flags`, `event_history`, `special_candidates`, and `terminal`.

## Minimal Shape

```json
{
  "premise": "A 12-year-old in a 1990s county town wants to change family fate through study and early computer access.",
  "tone": "grounded with rare legendary branches",
  "scale": "family, school, county, later city",
  "boundaries": ["no effortless success", "money pressure is persistent"],
  "event_seeds": [
    "teacher notices unusual effort",
    "secret work conflicts with study",
    "a used computer becomes possible but risky"
  ],
  "likely_failures": [
    "money schemes backfire",
    "hiding pressure damages trust",
    "overwork lowers health or morale"
  ],
  "terminal_paths": ["ordinary adulthood", "class mobility", "burnout", "legendary branch"]
}
```

Keep it short enough to hold in conversation context. If a note detail becomes mechanically important, convert it into a flag or event history item.

## When To Create One

Create or update a note when:

- the user names a custom world or unusual premise,
- an event pack only partially matches the world,
- a later-age start needs coherent social context,
- a recurring rule, taboo, resource, or genre constraint must stay stable.

Do not require a note for a quick original-style run.

## How It Affects Play

- `premise`, `tone`, and `boundaries` guide plausibility.
- `event_seeds` inspire manual events when no pack event fits.
- `likely_failures` keeps impossible or overpowered player actions grounded.
- `terminal_paths` reminds the Game Master that endings can be social, emotional, supernatural, or transitional.

If the event pack disagrees with the note, prefer the note for story judgment and report the mismatch during tests.
