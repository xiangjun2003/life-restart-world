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
- `references/content-packs/classic-lite.json`: small built-in offline seed pack. For default or classic-style runs, load it before the first event selection and keep using it as the active candidate source.

## Live Play Workflow

1. Start play quickly.
   - If the user says "来一局", "开始", "随机", or similar, begin a default run.
   - If the user gives a premise, infer reasonable defaults and begin.
   - Ask only one short follow-up when a missing detail blocks play.

2. Create or resume `LifeState v1`.
   - For a birth start, roll or infer core attributes and talents.
   - For a later-age start, generate a compressed prologue first, then begin at the requested age with grounded flags, talents, event history, and attributes.
   - Maintain this state internally after every resolved scene, even when the player only sees prose.
   - Do not show raw JSON unless the user asks for raw state.

3. Use meaningful-beat pacing.
   - Do not default to one year per turn. Choose the time span that makes the next meaningful decision arrive at the right speed.
   - Multiple scenes can happen inside the same year when each scene changes the situation, state, resources, branch, or player commitment. If a scene is mostly routine color, summarize it and move forward.
   - Ordinary play may jump months, years, or decades when quiet time passes. Cultivation, immortal, or post-human arcs can jump eras when the story supports it.
   - Resolve small player actions in one scene, then move to the next meaningful age or pressure unless the consequence demands an immediate follow-up.
   - Keep momentum by watching the last few exchanges: if they did not materially change state, history, or choices, accelerate.

4. Host each turn as a life scene, not a form.
   - Read the current state and recent conversation.
   - For default/classic runs, use the loaded `classic-lite` pack each turn as the event candidate source; do not reread the whole pack if it is already in context, but do filter it every turn by current state.
   - Prioritize `special_candidates` before ordinary events.
   - Treat event `effects` as an intended or typical result, not a guaranteed outcome.
   - Parse the user's natural-language action directly with model judgment.
   - Resolve success, failure, partial success, and side effects from state, genre, action plausibility, and event material.
   - Update only the core state fields.

5. Output almost entirely as story.
   - Write a complete scene.
   - Mention state changes only when they matter to the player. After major changes or every few turns, give a one-sentence state pulse in natural language so the player can feel the maintained state.
   - When useful, end with 2-4 natural action openings.
   - Always allow the user to ignore, combine, or rewrite the offered actions.
   - Never expose JSON, state-diff objects, rule pipelines, event IDs, or validator fields in ordinary play.

6. End, transform, or continue.
   - Do not hard-cap play at 100 years.
   - If a long-life, cultivation, resurrection, ascension, or post-human branch occurs, represent it with flags, event history, and terminal state.
   - `terminal` can close an ordinary death, a transformed human-life arc, or a chosen ending. If play continues after a transformation, clear or replace `terminal` with the new active arc's state.

## Rule Layer vs Model Layer

Rule layer:

- Validates `LifeState v1` field shape.
- Loads the active event pack for compatible runs, then filters events by age, attributes, talents, flags, and event history each turn.
- Adds and consumes `special_candidates`.
- Preserves terminal constraints.
- Treats malformed or mismatched event material as visible friction instead of silently smoothing it over.

Model layer:

- Turns event seeds into full story scenes.
- Understands free-form player actions.
- Decides whether attempted actions succeed, fail, partially succeed, or backfire.
- Updates core state directly.
- Keeps the life coherent through conversation context.
