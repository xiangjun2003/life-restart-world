# Turn State Notes

This file is a developer-only debugging aid. It is not a second Live Play mode and not a shape the player should see.

Use it only when you need to inspect why a hosted turn drifted away from `LifeState v1`.

## Internal Update Discipline

For each turn, the Game Master should be able to answer these questions internally:

1. What did the user try to do?
2. Which current state facts made success more or less plausible?
3. Which event seed, if any, was used?
4. Did the result succeed, fail, partially succeed, or create a side effect?
5. Which `LifeState v1` fields changed?

Do not print those answers as JSON in ordinary play. Use them to keep story and state aligned.

## Player Action Interpretation

Users can:

- choose an offered action,
- modify an offered action,
- combine several offered actions,
- ignore the offers and act freely,
- ask to fast-forward,
- ask for debug state.

Interpret the action semantically. Do not rely on a fixed keyword table for important understanding.

Examples:

- "选第二个，但别告诉家里" means the secrecy matters.
- "先读书，再偷偷打工" combines a steady and risky plan.
- "我去赚一个亿" is an attempted ambition, not an automatic success.
- "算了，我躺平" should affect morale, opportunity, time, or later regret when appropriate.

## State Update Surface

Only update:

- `age`
- `attrs`
- `talents`
- `flags`
- `event_history`
- `special_candidates`
- `terminal`

Optional developer fields such as `turn`, `session_id`, or `rng_seed` may be maintained by tools, but Live Play should not depend on them.

## Event Use

When an authored event is used:

- add its ID to `event_history` if it materially occurred,
- apply only the effects that actually landed in the narrated result,
- add/clear flags only when the story supports them,
- remove the event from `special_candidates` after resolution unless it is repeatable.

When the model creates a manual event, use a stable `manual_*` ID. This keeps later references possible without creating a full transcript ledger.

## Failure Check

Before finalizing a turn, check:

- Did the user's actual intent survive the ruling?
- Did an impossible action become a plausible attempt rather than literal obedience?
- Did any durable story fact land in flags, attrs, event history, special candidates, or terminal?
- Did an event-pack result fail or partially land when the user's state made full success unlikely?
- Did any special candidate unlock or resolve?
- Is the player-facing answer still mostly story?

If the answer would need a large hidden object to stay coherent, prefer a short flag or event-history item instead.
