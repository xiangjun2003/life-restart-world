# Life Restart World

Story-first Life Restart style live play for Codex and other agent frameworks.

`life-restart-world` is a Codex skill/world prototype for playing custom natural-language life simulations inspired by [VickScarlet/lifeRestart](https://github.com/VickScarlet/lifeRestart). It keeps a small rule-backed state while letting the model handle narrative continuity, free-form player actions, partial success, failure, ascension, reincarnation, and unusual life branches.

## What It Does

- Hosts **Live Play** only: no player-facing audit mode or rigid turn transcript.
- Maintains a compact `LifeState v1`: `age`, six attributes, talents, flags, event history, special candidates, and terminal state.
- Uses event packs as candidate material, not as a deterministic game engine.
- Lets every action and event fail, partially succeed, or backfire when the state makes that more plausible.
- Supports later-age starts by generating a compressed prologue before interactive play.
- Allows long-life branches beyond age 100 through flags, event history, and terminal state.

## Install For Codex

Clone the repo, then link it into your Codex skills directory:

```bash
git clone https://github.com/xiangjun2003/life-restart-world.git
ln -s "$(pwd)/life-restart-world" ~/.codex/skills/life-restart-world
```

In Codex, start with:

```text
Use $life-restart-world to start a story-first Life Restart style life.
```

## Repository Layout

```text
life-restart-world/
├── SKILL.md                         # Codex skill entrypoint
├── agents/openai.yaml               # Codex UI metadata
├── references/
│   ├── world-model.md               # LifeState v1
│   ├── game-master-protocol.md      # Live Play hosting protocol
│   ├── content-pack-schema.md       # Event pack schema
│   ├── prologue-protocol.md         # Later-age starts
│   ├── playtest-protocol.md         # Developer QA notes
│   ├── safety-boundaries.md         # Safety guidance
│   ├── upstream-mapping.md          # Mapping from original lifeRestart
│   ├── lifeRestart-LICENSE.md       # Upstream MIT license
│   └── content-packs/classic-lite.json
└── scripts/
    ├── validate_state.py            # Validate LifeState v1
    ├── validate_content_pack.py     # Validate event packs
    ├── validate_playtest.py         # Lightweight playtest checker
    ├── simulate_life.py             # Event candidate/state probe
    └── import_liferestart.py        # Import upstream xlsx data
```

## Live Play Flow

1. The Game Master creates or resumes a `LifeState v1`.
2. If the user starts at a later age, the Game Master writes a compressed prologue first.
3. Each turn is a meaningful scene or event fragment, not necessarily one year.
4. Event candidates are filtered by age, attributes, talents, flags, event history, and special prerequisites.
5. The user's natural-language action is interpreted by the model directly.
6. The model adjudicates success, failure, partial success, cost, or twist.
7. The core state is updated, then the player receives mostly narrative output with optional action openings.

## Developer Checks

```bash
python3 -m py_compile scripts/validate_state.py scripts/validate_content_pack.py scripts/validate_playtest.py scripts/simulate_life.py scripts/import_liferestart.py
python3 scripts/validate_content_pack.py references/content-packs/classic-lite.json
python3 scripts/simulate_life.py demo --seed 7 --turns 8
```

`simulate_life.py` is only a diagnostic probe. It is not the canonical game loop and should not be used as a free-form action parser.

## License And Credits

This project is released under the MIT License. See [LICENSE](LICENSE).

This project is inspired by the original [VickScarlet/lifeRestart](https://github.com/VickScarlet/lifeRestart), which is also MIT licensed. The upstream license text is preserved at [references/lifeRestart-LICENSE.md](references/lifeRestart-LICENSE.md).
