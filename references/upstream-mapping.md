# Upstream Mapping

Upstream repository: `https://github.com/VickScarlet/lifeRestart`

License: MIT. Preserve `references/lifeRestart-LICENSE.md` when reusing substantial upstream code or data.

## Original Architecture

- `src/modules/life.js`: orchestrates initialization, remake, start, yearly next step, summary.
- `src/modules/property.js`: stores properties such as `AGE`, `CHR`, `INT`, `STR`, `MNY`, `SPR`, `LIF`, talents, events, highs/lows, and totals.
- `src/modules/talent.js`: draws talents, handles rarity, exclusions, replacements, and talent effects.
- `src/modules/event.js`: checks event conditions, branches, and applies event effects.
- `src/functions/condition.js`: parses simple condition expressions with comparisons, membership, `&`, `|`, and parentheses.
- `data/<locale>/talents.xlsx`: talent definitions.
- `data/<locale>/events.xlsx`: event definitions.
- `data/<locale>/age.xlsx`: age-to-event weighted pools.
- `data/<locale>/achievement.xlsx`: achievements.
- `data/<locale>/character.xlsx`: celebrity/character presets.

## Mapping Into This Skill

| Upstream | Skill |
| --- | --- |
| `AGE` | `state.age` |
| `CHR`, `INT`, `STR`, `MNY`, `SPR` | `state.attributes` |
| `LIF` | terminal pressure or life force |
| `TLT` | `state.talents` |
| `EVT` / `AEVT` | `state.event_history` |
| `include` / `exclude` | content-pack conditions |
| `branch[]` | conditional event transitions |
| `effect:*` | event or talent effects |
| `age.xlsx` | `age_pools` |
| `grade` | rarity/intensity, not moral value |

## Important Difference

The original game outputs compact event text. This skill outputs complete narrative scenes, but the underlying fact pattern should still come from event data and state transitions.

## Long Life And Ascension

The upstream age table reaches 500 and includes cultivation, resurrection, ascension, and post-human branches. Therefore this skill must not hard-code a 100-year limit. Use `life_cap`, `existence_state`, `realm`, and terminal events instead.
