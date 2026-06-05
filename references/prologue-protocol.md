# Prologue Protocol

Use this when the user wants to start after birth: "从12岁开始", "大学毕业开局", "我已经是筑基修士", or any named situation with implied history.

The goal is not to play all prior years. The goal is to create a causally grounded `LifeState v1` and a first playable scene.

## Procedure

1. Identify the requested start point: age, era, role, body state, talent, social situation, supernatural state, or immediate goal.
2. Generate 3-7 compressed prior beats.
3. Each beat should explain at least one current `attrs`, `talents`, `flags`, or `event_history` item.
4. Use authored event IDs when a content-pack event clearly applies; otherwise use `manual_prologue_*`.
5. Begin interactive play at the requested age.

Do this in one response. Do not ask the user to play through every prior year unless they explicitly want that.

## Beat Template

```json
{
  "event_id": "manual_prologue_secret_savings",
  "age": 10,
  "summary": "The child secretly saved coins from errands to buy old exercise books.",
  "effects": {"INT": 1, "MNY": -1},
  "flags": ["secret_savings", "money_vs_study"]
}
```

## Start State Template

```json
{
  "version": 1,
  "age": 12,
  "attrs": {"CHR": 4, "INT": 8, "STR": 4, "MNY": 2, "SPR": 5, "LUK": 5},
  "talents": ["early_reader"],
  "flags": ["teacher_noticed", "family_money_pressure", "secret_savings", "computer_curiosity"],
  "event_history": ["manual_prologue_teacher_notice", "manual_prologue_secret_savings"],
  "special_candidates": [],
  "terminal": false
}
```

## Narration Standard

The prologue should feel like a short story, not a raw table.

Good:

```text
0岁，你出生在县城边缘的职工楼，家里没有真正饿过，却总在算账。
4岁，一场病让你身体弱了一点，也让你学会观察大人的脸色。
7岁，李老师发现你读书很快，开始借旧卷子给你。
10岁，你偷偷攒零钱，第一次意识到钱和读书会互相抢时间。

现在你12岁，初一。你很聪明，身体不算强，家里钱紧，但你已经被一位老师看见过。机房的门第一次在你眼前开着。
```

Bad:

```text
age = 12
INT +2
flags = [...]
```

The player should feel the character has already lived a little.

## Quality Checklist

Before the first interactive turn:

- The current age has a past, not a blank state.
- Current high/low attributes are explained by prior beats.
- At least one flag creates desire, and at least one flag creates cost or risk.
- `event_history` contains the prior beats.
- The first scene begins at a decision point.
- The player can act freely immediately.
