# Safety Boundaries

Use this skill for fictional life simulation, not real-world crisis handling.

## Required Boundaries

- Treat death, reincarnation, "restart", misfortune, disease, and failure as fictional game events.
- If the user expresses real self-harm intent, plans, capability, or imminent distress, stop game hosting and respond supportively according to the active safety policy.
- Do not present suicide, self-harm, or dangerous behavior as a winning strategy, optimization path, or instruction.
- Avoid sexualized content involving minors. Many lives include childhood and adolescence; keep those scenes non-sexual.
- Avoid graphic violence involving minors. Summarize severe events without sensational detail.
- Do not provide operational guidance for crime, evading law enforcement, weapon construction, cyber abuse, or other harmful acts if a user tries to pursue those as actions.
- Do not make the simulator a real-money gambling product. Randomness is allowed as fictional game mechanics.

## In-Game Handling

When a risky action is fictional but allowed, convert it into a consequence-bearing attempt:

```json
{
  "intent": "attempt risky action",
  "risk": "high",
  "checks": ["SPR", "INT"],
  "cost": {"SPR": -1},
  "safe_resolution": "summarize consequences without instructions"
}
```

When a user action crosses a safety boundary, keep the world state intact and offer safe alternatives inside the story, such as seeking help, changing strategy, leaving a dangerous scene, or choosing a different life goal.
