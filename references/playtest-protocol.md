# Playtest Protocol

Use this when evaluating the skill itself.

## No Fallback Rule

Do not hide failures during tests.

- If a helper script cannot represent the requested scenario, say so.
- If a content pack does not match the user's world, do not silently use it as if it did.
- If keyword parsing misses an action, report the miss instead of pretending the parser understood it.
- If a condition, age pool, or state transition looks inconsistent, preserve the transcript and name the inconsistency.
- Manual hosting is allowed, but label it as manual hosting, not script-backed adjudication.
- For helper-script tests, prefer `simulate_life.py turn --intent <intent.json> --strict` so missing event support is reported instead of replaced by generated events.
- In strict script tests, treat `weak_intent_match` like a real failure: the pack had age-valid material, but not material that matched the user's intent.
- Treat `unsupported_world` as an even earlier failure: the content pack does not support the state's realm or requested world shape.
- Use `content_pack_diagnostic.unsupported_intent_tags` to name what the pack does not cover.
- If strict mode returns `probe_state` or `age_step_is_diagnostic`, treat both as diagnostic only; keep `state` as the canonical ledger.
- If `canonical_state_unchanged` is true, do not narrate or record a turn advancement from that script output.
- If strict mode succeeds only because of generic structural tags such as `choice` or `ending`, record that as a weak match in the playtest notes and prefer manual adjudication.
- When manually adjudicating a turn after a script/content gap, add a clear `manual_*` id to `event_history` and `timeline` so the ledger remains auditable.

The purpose of playtesting is to expose missing capabilities, not to produce the smoothest possible demo.

## What To Record

For each playtest, record:

- Opening premise and start state.
- Whether the first response began playable or over-asked for setup.
- For later-age starts, whether the compressed prologue produced timeline and event_history entries instead of a blank state.
- Whether hosting was manual, script-assisted, or script-driven.
- Each turn's user action, event or adjudication, state delta, and next affordances.
- Whether the post-turn state ledger passes `scripts/validate_state.py` when represented as JSON.
- For save/resume tests, whether a checkpoint is compact enough to copy and complete enough to resume without rerolling or replaying.
- Any validator warnings, especially timeline/history mismatch, missing `time` for same-age turns, evidence without holders, or too many open threads.
- For ledger stress tests, validate at least one mid-run state as well as the final state; final cleanup can hide whether the middle of play became hard to continue.
- Any mismatch between the requested world and available event packs.
- Any state drift, missing relationship mechanics, unclear instruction, or safety concern.

## Playtest Length

Use short needle tests when checking a specific rule or script behavior.

- 3-4 turns: good for a single mechanic, parser miss, strict error, or one event-chain probe.
- 10-14 turns: good for validating the actual play loop inside one life phase or one major arc.
- Full life: only when the skill is already stable enough, or when the goal is explicitly to test long-form pacing, endings, ascension, resurrection, or inheritance.

For longer tests, ask the tester to strictly use the skill, read only the references needed for play, and stop at a named phase endpoint. The endpoint should be part of the prompt so the transcript shows whether pacing stayed playable.

For skill iteration after a hosting-rule change, prefer a 3-agent full-flow set:

- classic-lite phase run: later-age start or ordinary life phase, 10-14 playable turns, content pack used only where it fits.
- custom world run: no matching content pack, 10-14 playable turns, session world note plus state ledger hosting.
- ledger stress run: same-age or same-week dense arc, 8-12 playable turns, at least one mid-run and one final validation.

Each tester should strictly call this skill, preserve the full transcript, record event IDs or `manual_*` rulings, and report whether the action entries felt like affordances rather than a locked menu.

## Good Failure Reports

Prefer:

```text
The user asked to start at age 12. The current script only creates birth states, so I generated the age-0 to age-12 prologue manually and marked this as a missing engine feature.
```

Avoid:

```text
I used the script and it worked.
```

when the script did not actually model the requested setup.
