# Prologue Protocol

Use this when the user wants to start after birth: "从12岁开始", "大学毕业开局", "我已经是筑基修士", or any named situation with implied history.

The goal is not to play every prior turn. The goal is to produce a causally grounded starting state that gives the user a real first playable moment.

## Procedure

1. Identify the requested start point.
   - Age, realm, occupation, social role, body state, family state, and any named goal.
2. Create the earliest-known state.
   - Usually birth, but it can be awakening, reincarnation, upload, sect entry, or arrival in a new world.
3. Generate 3-7 compressed beats.
   - Each beat should change at least one durable state item: attribute, relationship, flag, open thread, clock, talent, realm, or life cap.
4. Derive the playable state.
   - Do not leave relationships, flags, and open threads empty if the prologue clearly implies them.
5. Present a short character card.
   - Include what the character knows, what they want, what is pressuring them, and where the next scene begins.
6. Start the first interactive turn.
   - Offer 2-4 action entries plus free-form action.

## Beat Template

```json
{
  "age": 10,
  "summary": "The child secretly saved coins from errands to buy old exercise books.",
  "effects": {"WIL": 1, "MNY": -1},
  "relationships": {"mother": {"delta": 1, "note": "notices the restraint but not the secret"}},
  "flags": ["secret_savings"],
  "open_threads": ["money_vs_study"]
}
```

## Start State Template

```json
{
  "age": 12,
  "attributes": {"CHR": 4, "INT": 8, "STR": 4, "MNY": 2, "SPR": 5, "LUK": 5, "WIL": 7},
  "relationships": {
    "mother": {"score": 2, "note": "protective, worried about money"},
    "teacher_li": {"score": 2, "note": "noticed unusual reading speed"}
  },
  "flags": ["teacher_noticed", "family_money_pressure", "secret_savings"],
  "open_threads": ["exam_path", "money_vs_study"],
  "timeline": [
    {"turn": "prologue", "age": 7, "summary": "A teacher noticed the child reading beyond grade level."},
    {"turn": "prologue", "age": 10, "summary": "Secret savings began to compete with school time."}
  ]
}
```

## Narration Standard

The prologue should be story-shaped, not a raw table. It can list the beats afterward for clarity, but the user should first feel the character has already lived a little.

For tests, clearly label whether the prologue was manually hosted or script-assisted. If the helper script cannot produce the later-age state, report that as an engine limitation and continue manually only when the test is evaluating Game Master behavior.
