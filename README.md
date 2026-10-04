# New Vesper

A persistent, text-based RPG with an AI narrator. It's set in New Vesper, a rain-soaked megacity where magic and technology both run on attention. The tone is grimbright. Start with the [teaser](docs/teaser.md). The full rules are in [docs/design.md](docs/design.md).

The AI tells the story. Code rolls the dice and keeps the books, and the AI can't talk its way around them.

## Install and play

You need:
- **Python 3.12 or newer**. Check with `python3 --version`, or `py --version` on Windows.
- **git**
- **An Anthropic API key** from [console.anthropic.com](https://console.anthropic.com/). Use your own key: the game spends from it. A turn costs about 2¢.

### 1. Get the code

```sh
git clone https://github.com/eriktoorens/new-vesper.git
cd new-vesper
```

If the repository is private, the owner must add you as a collaborator first. The easiest way to sign in is the GitHub CLI: run `gh auth login` and follow the prompts. GitHub no longer accepts your account password for git.

### 2. Make a virtual environment and install

A virtual environment (venv) keeps the game's packages separate from the rest of your system.

macOS / Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Keep the `-e`, because the game reads `docs/design.md` from this folder. Each time you open a new terminal, activate the venv again with the second line.

### 3. Set your API key

Set the key in each new terminal. Don't commit it or paste it anywhere public.

```sh
export ANTHROPIC_API_KEY=sk-ant-...          # macOS / Linux
```

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."        # Windows PowerShell
```

### 4. Play

```sh
new-vesper play --handle yourname
```

The first time you play, you make a character: origin, stats, two knacks, languages, name, pronouns, and a few details, including how they're built and move. After that, write what your character does in third person ("Mara ducks under the awning and…") and put their spoken words in quotes. The Narrator tells the story and calls for rolls.

In-game commands:

| Command | Does |
| --- | --- |
| `/look` | Your sheet and where you are |
| `/map` | District map: where you are and where you've been |
| `/time` | City clock, weather, moon and tide |
| `/who` | Who's here and what they're doing |
| `/ask <question>` | Ask what your character sees or knows (no time passes) |
| `/speak <language>` | Choose which of your languages your character speaks aloud |
| `/rename <name>` | Change your character's name |
| `/pronouns <pronouns>` | Change your character's pronouns, e.g. `/pronouns it/its` |
| `/body <line>` | Change how your character is built and moves, e.g. `/body fins for hands, waddles` |
| `/eat`, `/drink` | Buy food or drink where it's sold |
| `/rest` | Sleep at a haven |
| `/export` | Save your story as your character would tell it (a small model cost) |
| `/export record` | Save your story exactly as you saw it (free) |
| `/go <place>` | Move somewhere in the district, e.g. `/go tarp-row` |
| `/places` | Places you can go |
| `/level` | Spend XP on a level |
| `/budget` | How much of your monthly allowance is left |
| `/help` | This list |
| `/quit` | Log off |

Check spending from outside the game with `new-vesper budget`.

### Good to know

- **One action at a time:** type each action on one line, after you've read the city's answer. Anything typed while the city is answering is dropped, and a paste of several lines is refused whole.
- **Editing what you type:** use ←/→ to move within a line, ↑/↓ to bring back earlier lines, and Ctrl-A/Ctrl-E to jump to the start or end.
- **The world lives in `vesper.db`** in the folder you run from. Delete it to start over, or use `--db other.db` to keep a separate world.
- **Each install is its own city for now.** Until multiplayer is built, you and a friend won't meet.
- **Spending limits:** by default, the city goes quiet at $50 a month in total, and each player gets $10 a month. You can change these with `NEW_VESPER_MONTHLY_CAP_USD` and `NEW_VESPER_PLAYER_ALLOWANCE_USD`.
- **To update:** run `git pull`, then `pip install -e .` again. Database migrations run automatically.
- Windows gets its time zone data from the `tzdata` package, which installs automatically.

## Where we are, what's next

**Done** (all on this branch, 969 tests passing):
- Build steps 1–5: the rules engine, the SQLite state, the Market District content, the Narrator agent with its validated tool contract, and the budget with a usage ledger, caps and allowances.
- Playtest layers 1–5:
  - fixes from the first playtest
  - character details and ASCII art (vignettes, NPC portraits, a district map)
  - the city clock, weather, NPC routines and the daily tick
  - seasons, the moon, tides and the harbor
  - NPC memory and attitudes
  - encounters, which the Narrator writes fresh from a daily pool for each district
  - languages: speech in a language your character doesn't know shows as gibberish or a note, a Heart roll gets the gist, and `/speak` picks what you speak aloud
  - bodily needs: hunger, thirst, tiredness, cold and heat wear down stats and, at their worst, cost Harm or Fade; `/eat`, `/drink` and `/rest` ease them
  - setting-native kinds: play a Hearsay (a story walking), a Castoff (a dead brand's mascot) or a Mislaid (a lost thing become someone)
- Exporting your story: `/export` saves it as your character would tell it, `/export record` exactly as you saw it, and `new-vesper export` saves any character's, even one who has fallen. Files go in `stories/`.
- Decisions D1–D123 are recorded in [docs/design.md](docs/design.md), with a decision log at the end.

**Next:**
1. **Playtest layers 6–8: languages, bodily needs and the new kinds (D76–D93).** Watch whether the Narrator tags every line and keeps translations out of plain narration, whether the needs' rates feel right, and how the Narrator plays a hearsay, a castoff or a mislaid.
2. **The underlying model, belief and being (D106):** one belief field underneath the narrative and social layers, where a character's knowledge is a slice and a thing's reality is the integral. A draft with open questions; see "Draft: The Underlying Model, Belief and Being" in `docs/design.md`.
3. **Attention (D94):** the world's sustaining force, a daily amount per character spent on pushing the world against its grain, remembrance and prayer. Direction set; details open (see "Planned: Attention" in `docs/design.md`).
4. **Self and Seeming:** who a character really is and the face they show. This is proposed, not decided; the open questions are in `docs/design.md`.
5. Then multiplayer (D32): a shared city, and a second look at the city-day rule (D29/D50).

**Open question, high priority:** D10, who a favor is owed to. The player should understand where a debt accrues and have some choice in it. See the open questions in `docs/design.md`.

### For development

```sh
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
```

Start a new Claude Code session with:

> Read CLAUDE.md and docs/design.md, then pick up the next item in "Where we are, what's next".

Tests use a stubbed model client and never call the API.
