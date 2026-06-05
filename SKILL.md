---
name: life-restart-world
description: Host natural-language Life Restart style life simulations in Codex or other agent frameworks. Use when the user wants to play or host an interactive text life simulator with talents, six core attributes, age events, branching fate, custom actions, reincarnation, ascension, endings, and lightweight state tracking inspired by VickScarlet/lifeRestart.
---

# Life Restart World

## Purpose

Use this skill to host **Live Play**: a narrative-first life simulation where the user plays through a custom life in natural language.

The Game Master maintains a small LifeRestart-like state, not a script transcript. Event packs are reference material and candidate generators. The model is responsible for story continuity, free-form action understanding, and consequence adjudication.

The upstream project `VickScarlet/lifeRestart` is MIT licensed. If you reuse upstream code, data, event text, or converted content, preserve the license in `references/lifeRestart-LICENSE.md` and cite the upstream repository.

## Core State

Maintain only the `LifeState v1` core during play:

- `age`
- `attrs`: `CHR`, `INT`, `STR`, `MNY`, `SPR`, `LUK`
- `talents`
- `flags`
- `event_history`
- `special_candidates`
- `terminal`

Do not add relationship boards, pressure clocks, evidence ledgers, phase summaries, or open-thread lists for v1 play. If the story needs memory, preserve it through the conversation context and compact flags/event history.

## Reference Map

Load only what is needed:

- `references/game-master-protocol.md`: Live Play hosting, openings, free-form actions, event use, and narrative output.
- `references/world-model.md`: `LifeState v1`, attribute meanings, state discipline, terminal handling, and long-life branches.
- `references/content-pack-schema.md`: event pack fields, conditions, special candidate events, and validation rules.
- `references/prologue-protocol.md`: starting from a later age or an already-implied situation.
- `references/safety-boundaries.md`: safety rules for fictional death, reincarnation, minors, self-harm, and high-risk content.
- `references/content-packs/classic-lite.json`: small built-in offline seed pack.

## Live Play Workflow

1. Start play quickly.
   - If the user says "来一局", "开始", "随机", or similar, begin a default run.
   - If the user gives a premise, infer reasonable defaults and begin.
   - Ask only one short follow-up when a missing detail blocks play.

2. Create or resume `LifeState v1`.
   - For a birth start, roll or infer core attributes and talents.
   - For a later-age start, generate a compressed prologue first, then begin at the requested age with grounded flags, talents, event history, and attributes.
   - Do not show raw JSON unless the user asks for raw state.

3. Host each turn as a life scene, not a form.
   - Read the current state and recent conversation.
   - Check event-pack candidates when a pack fits the run.
   - Prioritize `special_candidates` before ordinary events.
   - Treat event `effects` as an intended or typical result, not a guaranteed outcome.
   - Parse the user's natural-language action directly with model judgment.
   - Resolve success, failure, partial success, and side effects from state, genre, action plausibility, and event material.
   - Update only the core state fields.

4. Output almost entirely as story.
   - Write a complete scene.
   - Mention state changes only when they matter to the player.
   - When useful, end with 2-4 natural action openings.
   - Always allow the user to ignore, combine, or rewrite the offered actions.
   - Never expose JSON, state-diff objects, rule pipelines, event IDs, or validator fields in ordinary play.

5. End, transform, or continue.
   - Do not hard-cap play at 100 years.
   - If a long-life, cultivation, resurrection, ascension, or post-human branch occurs, represent it with flags, event history, and terminal state.
   - `terminal` can close an ordinary death, a transformed human-life arc, or a chosen ending. If play continues after a transformation, clear or replace `terminal` with the new active arc's state.

## Rule Layer vs Model Layer

Rule layer:

- Validates `LifeState v1` field shape.
- Filters events by age, attributes, talents, flags, and event history.
- Adds and consumes `special_candidates`.
- Preserves terminal constraints.
- Treats malformed or mismatched event material as visible friction instead of silently smoothing it over.

Model layer:

- Turns event seeds into full story scenes.
- Understands free-form player actions.
- Decides whether attempted actions succeed, fail, partially succeed, or backfire.
- Updates core state directly.
- Keeps the life coherent through conversation context.
