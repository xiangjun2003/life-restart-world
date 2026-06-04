---
name: life-restart-world
description: Run and help build natural-language Life Restart style life simulations in Codex or other agent frameworks. Use when the user wants to play, host, design, extend, or debug an interactive text life simulator with talents, attributes, age events, branching fate, custom worlds, reincarnation, ascension, endings, and structured state tracking inspired by VickScarlet/lifeRestart.
---

# Life Restart World

## Purpose

Use this skill to host a narrative-first, stateful life simulation. The user can start a custom life in natural language, make free-form choices, and watch the Game Master maintain a structured state ledger for attributes, relationships, flags, event history, open threads, and endings.

The core play object is the state ledger, not the helper script. Treat event packs and scripts as references or adjudication aids. Do not force a custom world through a mismatched event pack.

The upstream project `VickScarlet/lifeRestart` is MIT licensed. If you reuse upstream code, data, event text, or converted content, preserve the license in `references/lifeRestart-LICENSE.md` and cite the upstream repository.

## Dependency Posture

Default to instruction-only hosting. Do not require network access, package installation, or third-party Python modules.

Optional helper scripts in `scripts/` use only Python 3 standard library. Use them for inspection, deterministic spot checks, or importing upstream data. They are not required for hosting and should not override good Game Master judgment.

## Reference Map

Load only what is needed:

- `references/game-master-protocol.md`: turn loop, opening guidance, natural-language action handling, output format.
- `references/world-model.md`: canonical state ledger, attributes, flags, immortality and ascension states.
- `references/turn-state-contract.md`: state-first turn contract, intent, resolution, delta, and affordance rules.
- `references/session-world.md`: lightweight world note for custom settings, factions, pressure clocks, and event seeds.
- `references/prologue-protocol.md`: concrete later-age start and compressed backstory procedure.
- `references/content-pack-schema.md`: JSON schema for events, talents, choices, effects, and conditions.
- `references/upstream-mapping.md`: how the original Life Restart modules and XLSX sheets map into this skill.
- `references/safety-boundaries.md`: safety rules for fictional death, reincarnation, minors, self-harm, and high-risk content.
- `references/playtest-protocol.md`: no-fallback testing rules and how to report exposed problems.
- `references/content-packs/classic-lite.json`: small built-in offline seed pack.

## Hosting Workflow

1. Establish play mode.
   - If the user gave enough detail, infer the mode and begin with a first playable response.
   - Otherwise ask a compact opening prompt: world style, randomness level, and pace. Ask only for missing essentials, not for a full form.
   - Default to `narrative-first`, `semi-random`, `standard` pace.
   - For custom worlds, draft a short session world note before resolving turns. This is a consistency aid, not a content-pack requirement.

2. Create the initial state ledger.
   - Include `age`, `life_cap`, `existence_state`, `realm`, attributes, talents, relationships, flags, event history, open threads, and terminal status.
   - If the user requests a later starting age or situation, generate a compressed prologue first, then begin interactive play at that age with a causally grounded state.
   - Give the user a short character card before the first turn, then immediately offer 2-4 playable action entries. Do not print raw JSON unless the user asks for debug view.

3. Resolve each turn in this order.
   - Interpret the user's natural-language action into an intent object.
   - Consult relevant event packs and open threads when they fit the world.
   - Adjudicate what happens from state, user intent, genre, and any matching event material. If the user acts outside the listed entries, treat that action as first-class play, not as a fallback or error.
   - Apply effects to the state ledger using the turn state contract.
   - Render a complete story scene from the rule result.
   - Present state deltas and 2-4 action entries, while allowing free-form action.

4. Keep narrative and rules aligned.
   - The story may be vivid, but every mechanical consequence must appear in the state delta.
   - Do not erase previous timeline facts unless an explicit supernatural or memory-altering event establishes it.
   - If a user proposes an implausible action, convert it into an attempt with cost, risk, and a check rather than refusing by default.
   - At natural phase endpoints, close or summarize stale threads into a phase summary so the current board stays playable.
   - When the user asks to save, resume, hand off to another agent, or continue after a long arc, create or consume a compact state checkpoint. Keep ordinary turns light unless a checkpoint is useful.

5. End or transcend the life.
   - Do not hard-cap life at 100 years. Use `life_cap`, `existence_state`, and terminal events.
   - Events such as resurrection, cultivation, immortality, ascension, or post-human transformation can extend or close the human-life arc.
   - At the end, summarize lifespan, identity arc, achievements, relationships, regrets, and any inherited talent or next-life hook.

## Optional Script Use

Use `scripts/simulate_life.py` when deterministic state stepping is useful, but do not treat it as the canonical game loop:

```bash
python3 scripts/simulate_life.py new --world "1990s county realism" --seed 7
python3 scripts/simulate_life.py turn --state state.json --action "I study hard but secretly earn money"
python3 scripts/simulate_life.py turn --state state.json --intent intent.json --strict
python3 scripts/simulate_life.py demo --seed 7 --turns 5
python3 scripts/validate_state.py state.json
```

Do not use `simulate_life.py` as a later-age prologue generator or same-age micro-turn engine. For starts such as "20 岁大二" or dense arcs such as an investigation, manually create and update the state ledger, then use `scripts/validate_state.py` to check structure. If you probe the content pack during such tests, report strict mismatches instead of converting them into generated fallback events.

Use `scripts/import_liferestart.py` only when an upstream `lifeRestart/data/<locale>/*.xlsx` directory is available and the user wants to convert MIT-licensed original sheets into a content pack. The importer uses `zipfile` and XML parsing from the Python standard library; it does not require `openpyxl`.

When playtesting, do not use fallback behavior to hide mismatches. If the script, content pack, or parser cannot support the requested world or action, report the mismatch plainly and continue manually only if the playtest goal is to evaluate Game Master behavior. Use `--strict` for script-assisted tests where generated fallback events or weakly related age events would hide a missing event.

Strict script failures can include `unsupported_world`, `no_matching_event`, or `weak_intent_match`. Treat all of them as useful diagnostics, not as narrative failures to smooth over.

## Output Shape For Play

For each playable turn, respond in this order:

1. A short scene in story form.
2. A compact state delta.
3. Current state snapshot.
4. Action entries:
   - Include 2-4 plausible action entries.
   - Make them affordances, not hard limits. Each entry should imply a different method, cost, ally, risk, or future thread.
   - End with a reminder that the user can answer freely.

Avoid command-heavy UX. The user should not need to learn `/select`, `/alloc`, or numeric event IDs unless they explicitly ask for a raw engine/debug view.
