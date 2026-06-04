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
- If strict mode returns `probe_state`, treat it as diagnostic only; keep `state` as the canonical ledger.

The purpose of playtesting is to expose missing capabilities, not to produce the smoothest possible demo.

## What To Record

For each playtest, record:

- Opening premise and start state.
- Whether hosting was manual, script-assisted, or script-driven.
- Each turn's user action, event or adjudication, state delta, and next affordances.
- Any mismatch between the requested world and available event packs.
- Any state drift, missing relationship mechanics, unclear instruction, or safety concern.

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
