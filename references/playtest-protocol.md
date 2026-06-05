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
- Whether action entries have distinct state hooks rather than cosmetic wording differences.
- At least one selected-entry modification or free-form action, with `intent.source` preserved as `modified_entry` or `freeform` in notes.
- Whether the post-turn state ledger passes `scripts/validate_state.py` when represented as JSON. For live-turn QA, include optional structured `next_affordances`, `last_intent`, and `last_delta` in at least one mid-run state.
- For a `modified_entry` or `freeform` turn, whether `last_delta.intent_trace` names the preserved custom action and points to real or newly changed ledger hooks.
- Whether phase endpoints close/summarize stale threads instead of carrying every old thread forward.
- Whether `phase_summaries.closed_threads` are actually absent from `open_threads`, unless the transcript clearly reopens them under a new active problem.
- Whether inactive clocks/evidence named by `last_delta` are absent from the active board but present in structured archive fields such as `closed_clocks`, `archived_clocks`, `archived_evidence`, or `spent_evidence`.
- Whether the current board stays scannable: only active relationships, clocks, evidence, and threads remain visible; old material moves into phase summaries, flags, notes, or timeline.
- For 10-14 turn school, career, investigation, or faction arcs, whether a mid-arc cleanup happened around turns 6-8 or before active threads/evidence neared 7 items.
- Whether each turn includes actual player-facing scene prose, not only an event title or state mutation. In JSON transcripts, record the prose or a faithful excerpt as `story_scene`.
- Whether each turn includes a player-facing change summary, not only the internal delta. In JSON transcripts, record it as `visible_delta`.
- Whether each ordinary turn exposed a compact player-facing current snapshot, not raw ledger JSON. In JSON transcripts, record that projection as `visible_snapshot` and mark `raw_state_exposed: false` unless the player explicitly requested debug/raw state.
- For pacing-sensitive tests, record age span, largest age jump, and same-age transitions. The goal is not to forbid jumps; it is to make accidental speedruns visible.
- For save/resume tests, whether a checkpoint is compact enough to copy and complete enough to resume without rerolling or replaying.
- For save/resume tests, record `scripts/validate_checkpoint.py` output before reconstructing the full ledger, then record `scripts/validate_state.py` output after resuming.
- Any validator warnings, especially timeline/history mismatch, missing `time` for same-age turns, evidence without holders, or too many open threads.
- When editing, importing, or selecting a content pack for script-assisted tests, record `scripts/validate_content_pack.py` output before play begins.
- For custom or no-pack worlds, record whether `world.session_note` exists and whether active pressure clocks are mirrored in the top-level state ledger.
- For custom or no-pack worlds, record whether at least one `state_axes` item and one faction are anchored in active ledger items or structured `next_affordances`; the note should not carry hidden state by itself.
- For custom or no-pack worlds, record `world.pack_policy.mode`, any `evaluated_packs`, and whether `none` / `reference` runs kept event ids as `manual_*`.
- For ledger stress tests, validate at least one mid-run state as well as the final state; final cleanup can hide whether the middle of play became hard to continue.
- Any mismatch between the requested world and available event packs.
- Any state drift, missing relationship mechanics, unclear instruction, or safety concern.

## Playtest Length

Use short needle tests when checking a specific rule or script behavior.

- 3-4 turns: good for a single mechanic, parser miss, strict error, or one event-chain probe.
- 10-14 turns: good for validating the actual play loop inside one life phase or one major arc.
- Full life: only when the skill is already stable enough, or when the goal is explicitly to test long-form pacing, endings, ascension, resurrection, or inheritance.

For longer tests, ask the tester to strictly call this skill, read only the references needed for play, preserve the full transcript, and stop at a named phase endpoint. The endpoint should be part of the prompt so the transcript shows whether pacing stayed playable.

For skill iteration after a hosting-rule change, prefer a 3-agent full-flow set:

- classic-lite phase run: later-age start or ordinary life phase, 10-14 playable turns, content pack used only where it fits.
- custom world run: no matching content pack, 10-14 playable turns, session world note plus state ledger hosting.
- ledger stress run: same-age or same-week dense arc, 8-12 playable turns, at least one mid-run and one final validation.

Each tester should record event IDs or `manual_*` rulings, run `scripts/validate_state.py` on at least one mid-run ledger and the endpoint ledger, and report whether the action entries felt like affordances rather than a locked menu. Include structured `next_affordances` in at least one validated live state so duplicate labels, missing state hooks, or cosmetic variants are visible. Include `last_intent` when testing selected-entry modification or free-form action preservation, and validate it soon after that action because `last_intent` is one-turn scoped. Include `last_delta` when testing whether story consequences landed in attributes, relationships, flags, clocks, evidence, threads, timeline, or phase summaries; for `modified_entry` or `freeform`, include `last_delta.intent_trace`. When using a checkpoint, prefer structured `next_affordances` objects and optional `last_intent` / `last_delta` if the next agent needs to preserve the last user move and its durable state effects.

For multi-turn QA, testers may also produce a compact JSON transcript and run:

```bash
python3 scripts/validate_playtest.py --fail-on-warnings --min-turns 8 --min-freeform 2 --min-modified-entry 1 playtest.json
```

For strict player-output QA, require story prose, a visible change summary, and a visible board each turn, and forbid raw ledger exposure:

```bash
python3 scripts/validate_playtest.py --fail-on-warnings --min-turns 8 --min-freeform 2 --min-modified-entry 1 --min-story-scenes 8 --min-visible-deltas 8 --min-visible-snapshots 8 --forbid-raw-state playtest.json
```

For dense phases, add pacing gates that match the test promise:

```bash
python3 scripts/validate_playtest.py --fail-on-warnings --min-turns 8 --min-freeform 2 --max-age-jump 1 --max-age-span 3 playtest.json
```

Use pacing gates for investigations, exam weeks, career crises, sect trials, hearings, relationships, or other arcs that should stay textured. Do not use them for explicit速通, long-life cultivation spans, immortality, ascension, or user-requested fast-forward unless the test is specifically about catching over-compression.

Pacing metrics use `initial_state`, per-turn `post_state` or `age_after`, and `final_state`. A turn-level `state` is validated as a state snapshot but is not pacing evidence because some transcripts use it for pre-turn state. Metrics include each age point's `time` label when available, and pacing gates warn when same-age transitions lack time labels. Use `--forbid-age-regression` only when the test promises ordinary chronological time; do not use it for reincarnation, memory rewind, time loops, or realm transitions that intentionally reset age.

Minimal transcript shape:

```json
{
  "kind": "life_restart_world_playtest",
  "version": 1,
  "hosting": "manual",
  "turns": [
    {
      "turn": 1,
      "user_action": "选 2，但先向老师隐瞒家里的水票账本",
      "intent_source": "modified_entry",
      "event_ids": ["manual_turn_archive_access"],
      "story_scene": "李老师把旧资料推到你面前时，你没有立刻提账本。你先问水票缺口能不能从公开栏核对，等老师点头后才把家里那部分线索压在心里。",
      "visible_delta": {
        "关系变化": "李老师更愿意帮你查公开材料",
        "新增线索": ["water_ticket_case"],
        "压力变化": "家里账本仍被你暂时隐瞒，后续有暴露风险"
      },
      "visible_snapshot": {
        "age": 12,
        "time": "12岁秋，放学后",
        "attributes": {"INT": 8, "WIL": 7},
        "relationships": {"mentor_teacher": 2, "mother": 1},
        "pressure": {"family_budget": "3/5"},
        "threads": ["water_ticket_case", "exam_path"]
      },
      "raw_state_exposed": false,
      "delta": {
        "intent_trace": {
          "source": "modified_entry",
          "preserved": ["hide the family ledger detail"],
          "state_hooks": ["teacher_trust", "water_ticket_case"],
          "outcome": "created evidence and changed relationship trust"
        }
      },
      "next_affordances": [
        {"label": "核对水票", "state_hooks": ["water_ticket_case"], "targets": ["mother"], "risk": "low"},
        {"label": "追问行会", "state_hooks": ["audit_retaliation"], "targets": ["water_guild"], "risk": "high"}
      ]
    }
  ]
}
```

Add real `post_state`, `mid_state`, and `final_state` ledgers when validating a full transcript; they are omitted above rather than shown as `{}` placeholders because any object in those fields is treated as a real ledger. The playtest validator is not a replacement for the state validator. It checks whether the transcript contains enough evidence: free-form or modified-entry play, event ids, deltas, affordances, state snapshots, and pack-policy consistency.

`story_scene`, `visible_delta`, and `visible_snapshot` are the player-facing projection of the turn: prose, changes, and current board. `post_state`, `mid_state`, and `final_state` are internal ledger evidence. Do not paste raw full JSON into ordinary play unless the user asked for debug/raw state; if they did, mark `raw_state_requested: true` on the turn or transcript.

Use the canonical field names above for new transcripts. `validate_playtest.py` accepts a few older aliases such as `scene`, `change_summary`, or `current_snapshot` for compatibility, but strict QA warns on aliases.

For dense no-pack investigations, include one mid-arc cleanup turn before the active board overloads. A useful pattern is:

```json
{
  "event_ids": ["manual_mid_arc_evidence_cleanup"],
  "story_scene": "The protagonist lays out the scattered notes, removes names that lack consent, and turns the remaining public records into one careful packet.",
  "visible_delta": {
    "主线变化": "零散线索合并为一个可讨论的证据包",
    "压力变化": "报复风险没有消失，但材料更稳",
    "移出当前面板": ["raw_shift_notes", "print_cache_copy", "temporary_interview_line"]
  },
  "delta": {
    "threads_closed": ["raw_shift_notes", "print_cache_probe", "temporary_interview_line"],
    "threads_added": ["evidence_packet_review"],
    "event_material": ["manual_mid_arc_evidence_cleanup"]
  }
}
```

The visible fields use player language; the internal `delta` keeps ledger keys for validation. In the same or following `post_state`, closed threads/evidence should be absent from the active board and referenced in `phase_summaries`, timeline, or structured archive fields.

When the skill seems stable and the goal is broader evaluation, a tester may run a complete small life or ascension arc instead of stopping after 10-14 turns. In that case, still use phase checkpoints so pacing, stale thread cleanup, and ending or transcendence handling are visible in the transcript.

For long-life or ascension tests, include at least one age-cap pressure point: ordinary death near `life_cap`, explicit life extension, resurrection, cultivation breakthrough, immortality, or ascension. The transcript should show whether `life_cap`, `existence_state`, `realm`, terminal status, timeline, and phase summaries stay coherent after the transition.

Use `--fail-on-warnings` when the playtest goal is to expose lifecycle drift or handoff defects through command exit status, not only through the JSON warning list.

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
