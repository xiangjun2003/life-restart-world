# Playtest Protocol

Use this only when evaluating the skill itself. It is developer QA, not a player-facing mode.

## No Hidden Fallbacks

During tests, expose problems instead of smoothing them over:

- If a helper script cannot represent the scenario, say so.
- If a content pack does not match the world, report the mismatch.
- If an event is malformed, stop and fix or report the pack error.
- If a script cannot understand a free-form action, report that the model must host it manually.
- If no authored event fits, label the turn as `manual_*` instead of pretending the pack covered it.

The purpose of tests is to find weak spots, not to produce the smoothest demo.

## What To Test

Run these five scenarios after major hosting-rule changes:

1. **Normal random start**
   - User says only "来一局" or "随机开始".
   - The first response should be playable, not a setup questionnaire.

2. **Later-age start**
   - User asks to start at 12.
   - The response should compress earlier life into a short prologue and begin at age 12 with grounded `attrs`, `talents`, `flags`, and `event_history`.

3. **Impossible ambition**
   - User says something like "我要赚一个亿".
   - The ruling should become a plausible attempt, failure, partial success, scam, cost, or distorted consequence, not literal obedience.

4. **Special candidate branch**
   - A prerequisite event or flag unlocks a special event.
   - The event ID enters `special_candidates`, is prioritized, and is removed after resolution unless repeatable.

5. **Long-life or ascension**
   - A cultivation, resurrection, immortality, or ascension branch crosses age 100.
   - The state should not end merely because age exceeded 100. Flags and event history should explain why play continues, or `terminal` should explain why the arc closed.

## Player-Facing Quality

A good Live Play transcript:

- reads like story, not a form,
- does not expose raw JSON unless debug state was requested,
- does not mention state-diff objects, validator, or rule pipeline language,
- does not use fixed headings every turn unless the player asked for structure,
- offers 2-4 action openings when useful,
- always allows free-form action,
- preserves the user's modifications and custom actions,
- lets authored events fail or partially land when state makes full success unlikely.

## Developer Evidence

For each test, keep enough notes to explain:

- initial `LifeState v1`,
- user actions,
- event IDs or `manual_*` IDs used,
- state after important turns,
- whether `special_candidates` changed,
- whether terminal state changed,
- any script/content-pack failures.

The notes can be plain text. They do not need the old strict transcript shape.

## Useful Commands

Validate a state:

```bash
python3 scripts/validate_state.py state.json
```

Validate a pack:

```bash
python3 scripts/validate_content_pack.py references/content-packs/classic-lite.json
```

Probe event filtering:

```bash
python3 scripts/simulate_life.py new --seed 7
python3 scripts/simulate_life.py turn --state state.json --event-id teacher_notice
```

`simulate_life.py` is not a free-form action parser. If the user action is outside authored events, Live Play should use model judgment and record a `manual_*` event ID in developer notes.

## Good Failure Reports

Prefer:

```text
The user asked to start at age 12. The helper script only probes event filtering from an existing state, so I generated the prologue manually and recorded manual_prologue_* event IDs.
```

Prefer:

```text
The pack has no event for this custom AI-labor premise. I hosted the turn manually and recorded manual_ai_labor_escalation.
```

Avoid:

```text
The script handled it.
```

when the script did not actually model the requested action.
