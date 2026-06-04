---
name: life-restart-world
description: Run and help build natural-language Life Restart style life simulations in Codex or other agent frameworks. Use when the user wants to play, host, design, extend, or debug an interactive text life simulator with talents, attributes, age events, branching fate, custom worlds, reincarnation, ascension, endings, and structured state tracking inspired by VickScarlet/lifeRestart.
---

# Life Restart World

## Purpose

Use this skill to host a narrative-first, rules-constrained life simulation. The user can start a custom life in natural language, make free-form choices, and watch a structured fate engine update attributes, relationships, flags, event history, and endings.

The upstream project `VickScarlet/lifeRestart` is MIT licensed. If you reuse upstream code, data, event text, or converted content, preserve the license in `references/lifeRestart-LICENSE.md` and cite the upstream repository.

## Dependency Posture

Default to instruction-only hosting. Do not require network access, package installation, or third-party Python modules.

Optional helper scripts in `scripts/` use only Python 3 standard library. If Python is unavailable, host the game manually using the same state and event protocol from the reference files.

## Reference Map

Load only what is needed:

- `references/game-master-protocol.md`: turn loop, opening guidance, natural-language action handling, output format.
- `references/world-model.md`: canonical state ledger, attributes, flags, immortality and ascension states.
- `references/content-pack-schema.md`: JSON schema for events, talents, choices, effects, and conditions.
- `references/upstream-mapping.md`: how the original Life Restart modules and XLSX sheets map into this skill.
- `references/safety-boundaries.md`: safety rules for fictional death, reincarnation, minors, self-harm, and high-risk content.
- `references/content-packs/classic-lite.json`: small built-in offline seed pack.

## Hosting Workflow

1. Establish play mode.
   - If the user gave enough detail, infer the mode and begin.
   - Otherwise ask a compact opening prompt: world style, randomness level, and pace.
   - Default to `narrative-first`, `semi-random`, `standard` pace.

2. Create the initial state ledger.
   - Include `age`, `life_cap`, `existence_state`, `realm`, attributes, talents, relationships, flags, event history, open threads, and terminal status.
   - Give the user a short character card before the first turn.

3. Resolve each turn in this order.
   - Interpret the user's natural-language action into an intent object.
   - Collect candidate events from the active content pack, open threads, and the user's action.
   - Filter by conditions and safety boundaries.
   - Reweight candidates by relevance to the user's action.
   - Pick or adjudicate one event.
   - Apply effects to the state ledger.
   - Render a complete story scene from the rule result.
   - Present state deltas and 2-4 action entries, while allowing free-form action.

4. Keep narrative and rules aligned.
   - The story may be vivid, but every mechanical consequence must appear in the state delta.
   - Do not erase previous timeline facts unless an explicit supernatural or memory-altering event establishes it.
   - If a user proposes an implausible action, convert it into an attempt with cost, risk, and a check rather than refusing by default.

5. End or transcend the life.
   - Do not hard-cap life at 100 years. Use `life_cap`, `existence_state`, and terminal events.
   - Events such as resurrection, cultivation, immortality, ascension, or post-human transformation can extend or close the human-life arc.
   - At the end, summarize lifespan, identity arc, achievements, relationships, regrets, and any inherited talent or next-life hook.

## Optional Script Use

Use `scripts/simulate_life.py` when deterministic state stepping is useful:

```bash
python3 scripts/simulate_life.py new --world "1990s county realism" --seed 7
python3 scripts/simulate_life.py turn --state state.json --action "I study hard but secretly earn money"
python3 scripts/simulate_life.py demo --seed 7 --turns 5
```

Use `scripts/import_liferestart.py` only when an upstream `lifeRestart/data/<locale>/*.xlsx` directory is available and the user wants to convert MIT-licensed original sheets into a content pack. The importer uses `zipfile` and XML parsing from the Python standard library; it does not require `openpyxl`.

## Output Shape For Play

For each playable turn, respond in this order:

1. A short scene in story form.
2. A compact state delta.
3. Current state snapshot.
4. Action entries:
   - Include 2-4 plausible action entries.
   - Make them affordances, not hard limits.
   - End with a reminder that the user can answer freely.

Avoid command-heavy UX. The user should not need to learn `/select`, `/alloc`, or numeric event IDs unless they explicitly ask for a raw engine/debug view.
