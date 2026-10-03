# New Vesper

A persistent, shared, text-based RPG with an AI narrator. Setting: New Vesper, a rain-soaked megacity where magic and technology both run on attention. Tone: grimbright.

**Source of truth:** `docs/design.md`. Read it before any rules, content or Narrator work. If code and the design doc disagree, the doc wins; if the doc is wrong or silent, stop and flag it rather than inventing a rule.

## Core principle: the AI proposes, code decides

This is the one rule that shapes everything else.

- The Narrator agent (Claude API) decides *what is being attempted* and *how the story reads*: whether a roll is needed, which stat, which difficulty rung, which move from the allowed list, and all narration.
- Code decides *what actually happens*: dice, Harm, Fade, stats, inventory, currency, loot, XP, region Light, and what exists in the world.
- The Narrator changes state **only** through tools. Every tool validates its request against the rules before writing. Narration never changes state on its own.
- Player text is **untrusted input**. A player can type anything, including instructions aimed at the Narrator. Validation happens in code, never in the prompt.

## Stack

- Python 3.12+, standard library first.
- SQLite for state (`sqlite3`), with a single migrations file per schema change.
- `anthropic` SDK for the Narrator agent. Prompt caching on the setting prompt and tool definitions.
- `pytest` for tests. `ruff` for lint and format.
- CLI first. No web server until the prototype plays well.

## Layout

```
new_vesper/
  rules/        # pure functions: resolver, tiers, tracks, leveling, moves, magic costs
  state/        # SQLite schema, migrations, repositories
  content/      # districts, NPCs, gods, knacks, loot tables (YAML or JSON data)
  dm/           # Narrator agent: prompts, tool definitions, tool handlers, play loop
  budget/       # usage ledger, monthly cap, per-player allowances
  cli.py        # entry point
tests/
docs/design.md
```

`rules/` must not import from `dm/`, `state/` or the network. (The Narrator was once called the DM; the `dm/` package, `Actor.DM` and other internal names keep the old name.) It is deterministic given an injected RNG.

## Build order

Build and finish each step, with tests passing, before starting the next.

1. **Rules engine** (`rules/`). The 2d6 resolver with stat and difficulty modifiers; three tiers (10+, 7–9, 6-); difficulty ladder (Routine +1, Risky 0, Hard −1, Desperate −2); stat cap +3; Harm and Fade tracks (6 boxes, thresholds per the doc); Fall or Endure at full Harm; slipping into Old Vesper at full Fade; leveling (N+1 costs 5 + N XP, choices per the doc, milestone every fifth level); the eight allowed moves with magnitude caps; opposed rolls for PvP.
2. **State** (`state/`). Tables for players, characters, origins and tags, knacks, regions with Light (0–10), items, the favor ledger, scenes and beats, an append-only event log, and the usage ledger.
3. **Content** (`content/`). The Market District: 4–5 locations, the drowned subway station entrance to Old Vesper, a handful of NPCs, one god with a shrine, about 8 starter knacks, one loot table. Data files, not code.
4. **Narrator agent** (`dm/`). Setting prompt built from `docs/design.md`; the tool contract below; a single-player terminal play loop.
5. **Budget** (`budget/`). Record every API call's token usage against the player and scene that triggered it; enforce a monthly spending cap and per-player allowances; when the cap is reached, the city goes quiet until reset.
6. **Playtest.** Play one scene end to end; tune the prompt; log cost per player-hour.

## Narrator tool contract

| Tool | Does |
| --- | --- |
| `look(entity)` | Returns current state so narration matches the world |
| `call_for_roll(stat, difficulty, stakes, knack?, magic?)` | Code rolls 2d6 + stat + modifier (+ knack bonus); returns total, tier and a single-use roll id |
| `apply_consequence(roll_id, type, target, magnitude)` | Checks the roll's tier (7–9 cost, 6− move, 10+ none), the allowed list and the magnitude cap; writes state |
| `grant_from_table(roll_id, table_id)` | Loot from a table on a 7+ roll, once per roll; the Narrator never invents items |
| `report_trigger(trigger_id, evidence)` | Flags an XP trigger; code decides the payout |
| `adjust_light(region, direction, size, reason)` | Moves a region's Light by a deed (±1) or major deed (±2); one change per region per scene |

Rules for tool handlers:

- Reject anything not in an allowed list: unknown stat, unknown difficulty rung, unknown move type, out-of-range magnitude, unknown table or trigger. Return a clear error to the model; never partially apply.
- Respect origin tags (for example, `no hands` blocks lock-picking).
- No PvP state change at a haven.
- Every successful write appends to the event log.

## Testing

- Every rule in `rules/` gets unit tests, including edge cases: stat at the cap, a track exactly filling, leveling at a milestone, a move at maximum magnitude.
- Inject a seeded RNG for deterministic tests. Also include a statistical test checking the tier distribution for +1 and +3 against the table in the doc.
- Tool handlers are tested with malicious and malformed inputs: wrong types, forbidden moves, injected instructions in string fields.
- Narrator agent tests use a stubbed model client. No live API calls in the test suite.

## Conventions

- Type hints everywhere. Small pure functions. No global state.
- Secrets from environment variables only (`ANTHROPIC_API_KEY`). Never log keys or full prompts containing them.
- Use the cheapest model that does the job: Haiku for routine narration, Sonnet for adjudication. Make the model configurable per call type.
- Keep scene history short: summarize older beats rather than resending them.
- New Vesper's narrator is a proper noun: the Narrator. Lowercase "narrator" only for narrators in general.

## Working with the designer

- **The designer decides design; Claude proposes.** When docs/design.md is silent or ambiguous on something that changes how the game plays or feels, stop and ask rather than inventing a rule. Implementation details with a conventional answer are Claude's to choose: pick one and mention it.
- **Few questions, each answerable.** Ask at most a handful at a time, most important first. Give each one two to four concrete options and a recommendation with a one-line reason, so a short reply ("b, agreed on 6") is enough.
- **Record answers where they live.** A decision goes into docs/design.md with the next D-number and a decision-log row. An idea the designer isn't committed to goes under Open Questions, marked as an idea, with its open sub-questions.
- **Ideas are not decisions.** Don't build from an open question, a draft or an "(idea)" entry until the designer says so.
- **Flag, don't fix, what's outside the task.** Note playtest findings and stray issues in the doc or as a suggestion; don't widen the current change.
- **Playtests:** when playing, reply with exactly one line to type, and keep out-of-game notes clearly separate and brief.
- **PRs only when asked**, and watch them when asked.

## Setting guardrails for content and prompts

- Many cultures, not a western default. Gods are invented for the setting, inspired by many traditions, never lifted from living religions.
- Grimbright: the world is cruel but not nihilistic. Kindness and effort matter on the page.
- Discworld-style levity sits on top of real stakes and never cancels them.
- Dice never kill a character. Death is always the player's choice (Fall or Endure).
