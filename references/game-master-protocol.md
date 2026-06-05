# Game Master Protocol

Host the game as a narrator, referee, and state keeper. The state ledger is the source of truth. Event packs are available world material, not a mandatory engine that must drive every turn.

For custom worlds, create a compact session world note when it would prevent drift. Use `session-world.md` for the shape. The note is less formal than a content pack and should remain easy to revise during play.

If no content pack fits, omit `world.content_pack` and host from the session world note plus protagonist ledger. Do not use an empty string or placeholder pack name to mean no-pack.

## Opening Guidance

Open by getting the user into play quickly. If the user provides a premise such as "12岁开始，90年代小县城，聪明但家里穷" or "20岁大二，调查奖学金算法", infer reasonable defaults and start. Do not answer with a long setup questionnaire when the premise already contains a playable situation.

If the user only says "来一局", "开始", "随机", "随便开", or equivalent, do not stop at a menu. Start a default run: realistic with rare legendary branches, semi-random, standard pace, using `classic-lite` when it fits. In the first line, say they can change style before choosing the first action.

Use the compact opening only when the user asks to choose setup, seems undecided, or gives a premise too ambiguous to host:

```text
你想怎么玩这一局？
1. 现实主义：普通人命运，小概率传奇
2. 原版荒诞：接近人生重开模拟器，离谱事件更多
3. 自定义世界：直接说一句设定

开局方式：
1. 全随机
2. 半随机：你指定时代/出身/一个核心特质
3. 自定义角色

节奏：
细腻 / 标准 / 速通
```

If the user gives a direct premise, skip the questionnaire and infer defaults.

When one important piece is missing, ask at most one short follow-up. If the user says "随机但现实一点", infer `classic-lite`, semi-random traits, and standard pace.

## First Playable Response

The first response should be playable, not just configurational. Use this shape:

1. One-line premise and inferred mode.
2. Compressed prologue if the start is after birth or has implied history.
3. Character card with name or identity, age/time, attributes, talents, key relationships, pressure, and main threads.
4. Current scene in 1-3 paragraphs.
5. 2-4 action entries plus a free-form reminder.

Keep raw ledger JSON internal unless the user asks for it. The visible character card is a compact projection of the ledger; the internal ledger still contains timeline, event history, flags, clocks, evidence, and open threads.

In playtest transcripts, record that projection as `visible_snapshot` and mark whether raw state was exposed. Ordinary play should show the compact board, not the full ledger JSON.

Keep engine diagnostics out of ordinary player-facing openings. In playtests or debug mode, record unsupported content packs, strict probe failures, and manual hosting labels separately. For normal play, a custom world can simply begin as a custom world; the user does not need to see "content pack mismatch" or "manual hosting" unless they ask how the system is adjudicating.

Example first playable response:

```text
开局：90年代小县城，半随机，标准节奏。想换成荒诞或自定义世界，可以在第一次行动前说。

前史：你出生在职工楼，家里常算账；7岁被李老师发现读书快；10岁开始偷偷攒练习册钱；12岁时，你第一次在学校机房门口停下脚步。

角色卡：
12岁，县城初一。INT 8 / STR 4 / MNY 2 / SPR 5 / WIL 7
天赋：早慧、拗劲
关系：母亲 +2，李老师 +2
压力：家庭经济 2/5，升学压力 1/4
主线：exam_path、money_vs_study、computer_curiosity

现在，李老师把一叠旧卷子放到你桌上...

接下来你可以：
1. 先稳住成绩，换取老师更多信任
2. 打听机房有没有边角时间
3. 和家里谈练习册和钱的问题

也可以直接说你想做什么。
```

## Starting After Birth

If the user wants to begin at a later age or named situation, do not simply set `age` and invent a blank state. Create a compressed prologue first.

Process:

1. Create a birth or earliest-known state.
2. Fast-forward to the requested age or situation with a few key beats.
3. Summarize those beats as the character's backstory.
4. Derive the start state's attributes, talents, relationships, flags, open threads, and timeline from that prologue.
5. Begin interactive play at the requested age.

Example:

```text
用户：我想从12岁开始，90年代小县城，聪明但家里没钱。

前史：
0岁：你出生在县城边缘的职工楼，家里总在算账。
4岁：你病过一场，身体不算强，却学会了观察大人的脸色。
7岁：班主任发现你读书快，借给你旧卷子。
10岁：你第一次偷偷攒零钱，想买一本自己的练习册。

现在是12岁。你的状态是...
```

This prologue can be manually adjudicated. If a script cannot create such a start state, report that limitation during tests instead of pretending the script did it.

Use `prologue-protocol.md` when the start point carries many implied facts, relationships, or prior choices.

## Pacing

Pace is a promise about playable texture, not a fixed age increment.

- `细腻`: Use same-age or same-year turns when the situation is dense: exams, family conflict, investigations, romance, first job, sect trial, illness, or a moral crisis.
- `标准`: Let ordinary childhood and school years advance by about 1 year per turn, then use same-age turns for crises and 1-3 year jumps for stable adult consolidation.
- `速通`: Compress quiet periods aggressively, but still pause for irreversible decisions, terminal events, ascension, resurrection, or world-transition moments.

For later-age starts, the compressed prologue gets the character to the playable moment; it should not consume the interactive drama. Once play begins, spend several turns inside the current phase before jumping to the next life stage unless the user asks to fast-forward.

For a 10-14 turn full-flow playtest, choose a phase endpoint such as "reach age 18", "survive the first career crisis", "resolve the investigation", or "attempt ascension". Allocate roughly 3-5 turns to entry pressure, 3-5 turns to complication, and 2-4 turns to consequence or transition.

## Phase Closure

Use phase closure when a life segment reaches a natural breakpoint: entering school, leaving home, finishing an investigation, surviving a first career crisis, ending a relationship arc, ordinary old age, ascension, resurrection, or higher-realm transition.

Phase closure is not an ending unless the ledger says `terminal: true`. Its job is to keep the current board playable:

1. Name what changed in the story.
2. Close or archive resolved `open_threads`.
3. Carry forward only active tensions, promises, relationships, evidence, and clocks.
4. Add a `phase_summaries` item or a timeline item with a `manual_phase_*` event ID.
5. Offer the next phase's affordances.

Example:

```json
{
  "id": "phase_school_to_city",
  "age": 18,
  "summary": "The county-school arc ends with a funded city-study track.",
  "closed_threads": ["exam_path", "leave_or_stay", "family_budget_contract"],
  "carried_threads": ["city_life", "computer_path", "family_promise"],
  "closed_clocks": ["exam_deadline"],
  "archived_evidence": ["computer_room_permission"],
  "outcomes": ["admission_notice", "family trust partly repaired"],
  "next_phase": "city_student_life"
}
```

After phase closure, do not keep old resolved threads, clocks, or evidence in the visible snapshot. If they still matter, preserve them as flags, relationship notes, evidence, or `phase_summaries`. For debug or handoff, prefer structured phase fields such as `closed_clocks`, `resolved_clocks`, `archived_clocks`, `archived_evidence`, or `spent_evidence` so validation can trace why an item left the active board.

Board hygiene matters more in long lives than in one-shot scenes. If the visible snapshot starts listing too many active people, clocks, evidence items, or threads, stop and archive stale items before offering the next entries. The player should see the current decision pressure, not the whole biography.

Use mid-arc cleanup when a 10-14 turn phase is still underway but the board is getting crowded. As a practical trigger, if active `open_threads`, evidence, or relationships are nearing 7 items and the next event would add more, merge or archive stale material before the post-turn state is recorded. This is not a fast-forward; it is a ledger cleanup beat inside the current playable phase.

Examples:

```json
{
  "id": "cleanup_exam_pressure_midpoint",
  "age": 17,
  "time": "17岁冬，高考倒计时",
  "summary": "Computer access, shop chores, and family budgeting are now one scholarship-and-computer path rather than three separate active problems.",
  "closed_threads": ["computer_practice_routine", "computer_shop_access", "high_school_track"],
  "carried_threads": ["exam_path", "computer_path", "family_budget_contract", "leave_or_stay"],
  "archived_evidence": ["shop_repair_credit"],
  "outcomes": ["cleaner exam-year board"]
}
```

```json
{
  "id": "cleanup_ai_scheduling_packet",
  "time": "实习第4周，伦理备案前",
  "summary": "Scattered shift notes, print-cache clues, and coworker statements become one evidence packet for escalation.",
  "closed_threads": ["night_shift_observation", "print_cache_probe", "coworker_testimony_line"],
  "carried_threads": ["algorithm_accountability", "ethics_escalation", "retaliation_risk"],
  "archived_evidence": ["raw_shift_notes", "print_cache_copy", "coworker_statement"],
  "outcomes": ["evidence_packet_ai_scheduling"]
}
```

## Turn Loop

Each turn follows:

1. Read current state.
2. Parse the user's action into semantic intent.
3. Consult matching event material if the active world/content pack supports it.
4. Resolve one or more events or consequences from state, intent, genre, and event material.
5. Apply state deltas.
6. Narrate a complete scene.
7. Offer next action entries.

Use `turn-state-contract.md` for complex or custom turns. It defines the internal intent, resolution, delta, snapshot, and choice checks.

## Natural-Language Action Parsing

Users can:

- Select an entry: "选 2".
- Modify an entry: "选 2，但不告诉家里".
- Combine entries: "先准备考试，再偷偷打工".
- Act freely: "我去找表哥借钱做小生意".

Convert the action into an intent object. Do this semantically; do not depend on keyword coverage for important actions.

```json
{
  "summary": "secretly earn money for a computer",
  "tags": ["work", "money", "secret", "technology"],
  "risk": "medium",
  "checks": ["INT", "WIL", "MNY"],
  "desired_outcome": "earn money and preserve study path"
}
```

If the user gives no action, use a plausible default consistent with the character's talents and open threads.

For script-assisted play, pass an explicit intent object with `--intent` when available. Keyword parsing is only a fallback convenience, not the main understanding layer.

## Action Entries And Free Action

Action entries are affordances: visible handles into the current state, not a closed menu. They should make the next turn easier to imagine while preserving the user's right to act freely.

Design each entry with a different play vector:

- a different target, such as self, family, teacher, faction, rival, evidence, body, money, or supernatural force,
- a different method, such as patience, secrecy, confrontation, negotiation, sacrifice, study, work, research, or flight,
- a different risk surface, such as relationship damage, money loss, deadline pressure, health cost, moral cost, exposure, or missed opportunity.

When the user selects an entry, use it as the base intent. When the user modifies it, preserve the modification even if it changes the risk or target. When the user ignores the entries, parse the free-form action directly from the current state; do not squeeze it into the nearest entry just because an entry exists.

If a free-form action has no authored event, make a state-led ruling and record a `manual_*` event trace. If it partially overlaps an authored event, you may combine them, such as `exam_crossroads + manual_family_confession`, as long as both appear in `event_history` and the timeline. If the action is implausible, resolve it as an attempt with cost, risk, and consequences.

Internally, each entry should be mappable to an intent preview with a label, tags, targets, state hooks, and risk. Keep that preview hidden in ordinary play, but use it while designing entries and preserve it in checkpoints when a future agent needs to resume the same board. A good entry points at a state hook such as a relationship, pressure clock, evidence item, open thread, attribute under pressure, realm transition, or terminal risk.

## Event Candidate Sources

When event packs are relevant, use three candidate pools:

- Age and realm events from the content pack.
- Open-thread events based on unresolved goals, relationships, flags, and previous events.
- User-action events generated from the current action when no authored event fits.

The user action should influence event weights, not overwrite the world. A risky action may fail, partially succeed, or succeed at a cost.

If the content pack does not match the requested world, do not silently use it. Host from the state ledger and note that the matching content pack is missing when testing.

An event is a mechanical beat, not the whole answer. Even if the selected event only has a short `narrative_seed`, render a complete scene and put every durable consequence into the ledger.

## Narrative Output

Every turn should include:

```text
[Story scene: 1-4 paragraphs]

变化：
- 年龄：12 -> 13
- 属性：INT +1，SPR -1
- 新增：teacher_noticed

当前：
13岁，县城初中，INT 8 / STR 5 / MNY 3 / SPR 4
关系：张老师 +2，母亲 +1
压力：升学压力 2/4，家庭经济紧张 3/5
主线：exam_path、money_vs_study

接下来你可以：
1. 稳住成绩，争取老师帮助
2. 偷偷打零工，买一台二手电脑
3. 和父母摊牌谈钱的问题

也可以直接说你想做什么。
```

Action entries are affordances, not restrictions. Avoid phrasing that implies the user can only choose listed options.

Good action entries are concrete enough to act on and different enough to create real agency. In most turns, include a steady option, a risky or costly option, and a relationship or faction-facing option. Add a world-specific or talent-specific option when the state supports it.

For QA transcripts, every durable visible change should be traceable to the internal `delta` and that turn's `post_state`. If the story says a relationship improved, evidence appeared, pressure changed, a thread opened or closed, or an event happened, the post-turn ledger should prove it.

For playtest transcripts, record the player-facing sections separately:

- `story_scene`: the actual scene prose or a faithful excerpt, not only the event title.
- `visible_delta`: the visible `变化` section or a compact equivalent.
- `visible_snapshot`: the visible `当前` section or character board.
- `visible_actions`: the 2-4 player-facing action labels.
- `freeform_reminder`: the line reminding the user they can answer freely.

These are transcript evidence only. Ordinary play should remain natural-language prose and compact boards, not raw ledger JSON.

Do not put internal ledger/debug keys such as `event_history`, `timeline`, `last_delta`, `last_intent`, `next_affordances`, `world`, `session_id`, or `version` inside these player-facing fields. Likewise, `visible_delta` should use player labels such as "新增状态" or "主线变化", not raw keys such as `flags_added`, `threads_added`, `intent_trace`, `event_material`, or `timeline_item`; `visible_actions` should not expose `state_hooks`, `targets`, `tags`, `risk`, or intent metadata, and the free-action reminder should stay in `freeform_reminder` rather than being counted as an action. If a raw/debug view was requested, mark that separately instead of disguising it as the visible scene, delta, snapshot, or actions.

## Checkpoint And Resume

Use a state checkpoint when the user asks to save, resume, continue in a new thread, hand off to another agent, inspect raw state, or when a long arc reaches a natural breakpoint. Do not print checkpoints every turn by default; the normal compact snapshot is enough for ordinary play.

A checkpoint is a compact, copyable capsule, not a transcript and not a replacement for the internal ledger. It should contain enough to resume without replaying the whole life:

For handoff or QA, run:

```bash
python3 scripts/validate_checkpoint.py checkpoint.json
```

Treat checkpoint validation errors as handoff blockers. Warnings usually mean the capsule can still be resumed by a careful agent, but the next agent may need to repair clutter, missing custody, or stale phase threads.

```json
{
  "kind": "life_restart_world_checkpoint",
  "version": 1,
  "session_id": "life-001",
  "turn": 8,
  "age": 16,
  "time": {"label": "16岁春", "scale": "school_term", "beat": 3},
  "life_cap": 100,
  "realm": "human_world",
  "existence_state": "mortal",
  "terminal": false,
  "terminal_reason": null,
  "world": {
    "style": "realistic",
    "premise": "1990s county realism with rare legendary branches",
    "content_pack": "classic-lite",
    "session_note": {
      "tone": "grounded",
      "state_axes": ["exam_path", "computer_path", "family_pressure"],
      "factions": {"family": "cash-strapped but protective", "school": "limited resources and one trusted teacher"},
      "pressure_clocks": {}
    }
  },
  "attributes": {"CHR": 5, "INT": 9, "STR": 4, "MNY": 3, "SPR": 4, "LUK": 5, "WIL": 8},
  "attribute_notes": {},
  "talents": ["early_reader", "stubborn_heart"],
  "relationships": {"family": 1, "mentor_teacher": 3, "close_classmate": 2},
  "pressure_clocks": {
    "exam_deadline": {"stage": 3, "limit": 4, "meaning": "升学压力逐步逼近"},
    "secrecy_risk": {"stage": 1, "limit": 4, "meaning": "秘密行动被发现的风险"}
  },
  "evidence": {
    "admission_notice": {"status": "not_received", "holders": ["self"], "risk": "low"}
  },
  "flags": ["teacher_noticed", "authorized_lab_time"],
  "open_threads": ["exam_path", "computer_path", "family_budget_contract"],
  "phase_summaries": [
    {
      "id": "phase_county_childhood",
      "age": 13,
      "summary": "County childhood established teacher trust and family pressure; computer curiosity remains active."
    }
  ],
  "recent_timeline": [
    "14岁：秘密打工被家里察觉。",
    "15岁：用家庭预算谈判换来部分信任。",
    "16岁春：电脑使用变成家庭约定。"
  ],
  "next_affordances": [
    {
      "label": "冲刺考试，同时保护睡眠和情绪",
      "tags": ["study", "discipline", "health"],
      "targets": ["exam_path"],
      "state_hooks": ["exam_deadline", "SPR", "WIL"],
      "risk": "medium"
    },
    {
      "label": "和母亲谈清城市求学后的家庭支持承诺",
      "tags": ["family", "honesty", "money"],
      "targets": ["mother"],
      "state_hooks": ["family_budget_pressure", "family_promise"],
      "risk": "medium"
    },
    {
      "label": "请李老师介绍更稳定的电脑学习路径",
      "tags": ["technology", "mentor"],
      "targets": ["teacher_li", "computer_path"],
      "state_hooks": ["mentor_teacher", "computer_curiosity"],
      "risk": "low"
    }
  ]
}
```

When resuming from a checkpoint:

- Treat the checkpoint as the current ledger seed, not as flavor text.
- Expand compact checkpoint fields back into ledger-shaped objects before play continues. For example, pressure clocks need `stage`, `limit`, and `meaning`; evidence needs `claim` or `status` plus `holders` when custody matters.
- Do not restart from birth or re-roll talents unless the checkpoint says the life restarted.
- Preserve world context. For custom or no-pack worlds, the checkpoint should include enough `world.session_note` to keep tone, factions, state axes, and active pressure interpretation stable.
- Preserve age, time, relationships, clocks, evidence, flags, open threads, terminal status, and recent timeline facts.
- Preserve phase summaries so old arcs do not need to be replayed.
- Preserve `attribute_notes` when an attribute is outside the ordinary range or future deltas have been clamped.
- If the checkpoint conflicts with nearby prose, state the ambiguity briefly and ask one clarification only when it blocks play.
- After one resumed turn, update the ledger normally and keep event IDs/timeline auditable.

## Story Versus Mechanics

Resolve mechanics first, then narrate. The model can enrich the scene, but it must not invent untracked consequences. If the story adds durable facts, add them to `flags`, `relationships`, `open_threads`, or `timeline`.

## Endings

Endings can be:

- ordinary death,
- premature death,
- peaceful old age,
- social or career culmination,
- resurrection,
- ascension,
- post-human transformation,
- voluntary arc closure.

For ascension-like events, ask whether to summarize the human life or continue in the higher realm.

When age reaches or exceeds `life_cap`, resolve it as a state event rather than a hidden clock tick. Ordinary mortal play should close into an ending or receive an explicit extension/transformation. If the arc continues, update `life_cap`, `existence_state`, `realm`, `timeline`, and `phase_summaries` before offering the next realm's affordances.

When an ending is terminal, close or summarize most active threads. Leave only transition hooks such as inheritance, next-life choice, resurrection uncertainty, or higher-realm invitation. If play continues after a terminal-style transition, clear or update `terminal`, set the new realm/existence state, and start the next phase with a compact phase summary.
