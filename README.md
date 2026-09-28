# New Vesper

A persistent, text-based RPG with an AI dungeon master. It's set in New Vesper, a rain-soaked megacity where magic and technology both run on attention. The tone is grimbright. Start with the [teaser](docs/teaser.md). The full rules are in [docs/design.md](docs/design.md).

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

The first time you play, you make a character: origin, stats, two knacks, languages, name, pronouns, and a few details. After that, write what your character does in third person ("Mara ducks under the awning and…") and put their spoken words in quotes. The DM narrates and calls for rolls.

In-game commands:

| Command | Does |
| --- | --- |
| `/look` | Your sheet and where you are |
| `/map` | District map: where you are and where you've been |
| `/time` | City clock, weather, moon and tide |
| `/who` | Who's here and what they're doing |
| `/ask <question>` | Ask what your character sees or knows (no time passes) |
| `/speak <language>` | Choose which of your languages your character speaks aloud |
| `/go <place>` | Move somewhere in the district, e.g. `/go tarp-row` |
| `/places` | Places you can go |
| `/level` | Spend XP on a level |
| `/budget` | How much of your monthly allowance is left |
| `/help` | This list |
| `/quit` | Log off |

Check spending from outside the game with `new-vesper budget`.

### Good to know

- **The world lives in `vesper.db`** in the folder you run from. Delete it to start over, or use `--db other.db` to keep a separate world.
- **Each install is its own city for now.** Until multiplayer is built, you and a friend won't meet.
- **Spending limits:** by default, the city goes quiet at $50 a month in total, and each player gets $10 a month. You can change these with `NEW_VESPER_MONTHLY_CAP_USD` and `NEW_VESPER_PLAYER_ALLOWANCE_USD`.
- **To update:** run `git pull`, then `pip install -e .` again. Database migrations run automatically.
- Windows gets its time zone data from the `tzdata` package, which installs automatically.

## Where we are, what's next

**Done** (all on this branch, 813 tests passing):
- Build steps 1–5: the rules engine, the SQLite state, the Market District content, the DM agent with its validated tool contract, and the budget with a usage ledger, caps and allowances.
- Playtest layers 1–5:
  - fixes from the first playtest
  - character details and ASCII art (vignettes, NPC portraits, a district map)
  - the city clock, weather, NPC routines and the daily tick
  - seasons, the moon, tides and the harbor
  - NPC memory and attitudes
  - encounters, which the DM writes fresh from a daily pool for each district
  - languages: speech in a language your character doesn't know shows as gibberish or a note, a Heart roll gets the gist, and `/speak` picks what you speak aloud
- Decisions D1–D81 are recorded in [docs/design.md](docs/design.md), with a decision log at the end.

**Next:**
1. **Playtest layer 6, languages (D76–D81).** Watch whether the DM tags every line and keeps translations out of plain narration.
2. **Layer 7, setting-native kinds as origins (D42).**
3. A playtest after each layer.
4. Then multiplayer (D32): a shared city, and a second look at the city-day rule (D29/D50).

**Open question, high priority:** D10, who a favor is owed to. The player should understand where a debt accrues and have some choice in it. See the open questions in `docs/design.md`.

### For development

```sh
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
```

Start a new Claude Code session with:

> Read CLAUDE.md and docs/design.md, then start layer 7, setting-native kinds.

Tests use a stubbed model client and never call the API.
