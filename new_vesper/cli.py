"""Terminal entry point: `new-vesper play --db vesper.db --handle ash`.

The player makes every creation and leveling choice here, through menus (D17).
Everything else goes to the DM through PlaySession.
"""

import argparse
import random
import shutil
import sys
import textwrap
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from new_vesper.budget.policy import BudgetConfig
from new_vesper.budget.pricing import PRICES, price_of
from new_vesper.budget.report import month_report
from new_vesper.content.loader import Content, load_content
from new_vesper.content.seed import seed
from new_vesper.dm.agent import ModelClient
from new_vesper.dm.config import CallType, DMConfig
from new_vesper.dm.handlers import NEEDS_HANDS, NO_HANDS
from new_vesper.dm.session import PlaySession, SessionError, TurnOutcome
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.rules.currency import format_glitter
from new_vesper.rules.errors import RulesError
from new_vesper.rules.leveling import LevelUpRequest, can_level_up, is_milestone
from new_vesper.rules.stats import STARTING_ARRAY, Stat
from new_vesper.rules.tracks import fade_status, harm_status
from new_vesper.state import characters, players
from new_vesper.state.characters import Character
from new_vesper.state.db import open_database
from new_vesper.state.errors import StateError
from new_vesper.state.events import Actor, Cause

DESIGN_DOC = Path(__file__).resolve().parents[1] / "docs" / "design.md"
START_LOCATION = "hundred-hooks"
HELP = """Type what your character does, or a command:
  /look          your sheet and where you are
  /ask <question>  ask the DM what your character sees or knows (no time passes)
  /go <place>    move somewhere in this district (e.g. /go tarp-row)
  /places        list places you can go
  /level         spend XP on a level
  /budget        how much of your monthly allowance is left
  /help          this list
  /quit          log off"""

Ask = Callable[[str], str]
Say = Callable[[str], None]


class Quit(Exception):
    pass


def _ask(ask: Ask, question: str) -> str:
    try:
        return ask(question).strip()
    except EOFError as exc:
        raise Quit from exc


def choose(ask: Ask, say: Say, title: str, options: Sequence[tuple[str, str]]) -> str:
    """A numbered menu; returns the chosen option's key."""
    say(title)
    for number, (_, label) in enumerate(options, 1):
        say(f"  {number}. {label}")
    while True:
        answer = _ask(ask, "> ")
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        say(f"Pick a number from 1 to {len(options)}.")


def create_character(conn, content: Content, player_id: int, ask: Ask, say: Say) -> Character:
    say("A new character. There are no classes: an origin, five stats, two knacks, a Bond.")
    origin = choose(
        ask,
        say,
        "Origin:",
        [(o.id, f"{o.name}: {o.trait}") for o in content.origins.values()],
    )
    tags = content.origins[origin].tags
    stats: dict[Stat, int] = {}
    remaining = list(STARTING_ARRAY)
    for value in STARTING_ARRAY:
        open_stats = [s for s in Stat if s not in stats]
        stat = choose(
            ask,
            say,
            f"Which stat gets {value:+d}? (left to place: {remaining})",
            [(s.value, s.value.title()) for s in open_stats],
        )
        stats[Stat(stat)] = value
        remaining.remove(value)
    usable = [
        k for k in content.knacks.values() if not (NEEDS_HANDS in k.tags and NO_HANDS in tags)
    ]
    first = choose(
        ask,
        say,
        "First knack:",
        [(k.id, f"{k.name} ({k.stat.value}): {k.trigger}") for k in usable],
    )
    second = choose(
        ask,
        say,
        "Second knack:",
        [(k.id, f"{k.name} ({k.stat.value}): {k.trigger}") for k in usable if k.id != first],
    )
    while True:
        name = _ask(ask, "Name: ")
        pronouns = _ask(ask, "Pronouns (e.g. she/her, he/him, they/them): ")
        bond = _ask(
            ask,
            "Bond, in a line: someone your character matters to "
            "(e.g. Emily, my sister who runs a noodle cart): ",
        )
        try:
            sheet = new_sheet(stats, (first, second))
            return characters.create_character(
                conn,
                player_id,
                name,
                origin,
                bond,
                sheet,
                Cause(Actor.PLAYER, player_id),
                location_id=START_LOCATION,
                pronouns=pronouns,
            )
        except (RulesError, StateError) as exc:
            say(f"That didn't work: {exc}")


def show_sheet(character: Character, content: Content, say: Say) -> None:
    sheet = character.sheet
    place = content.locations.get(character.location_id or "")
    pronouns = f" ({character.pronouns})" if character.pronouns else ""
    say(f"{character.name}{pronouns}, level {sheet.level} ({sheet.xp} XP) - {character.origin_id}")
    say("  " + "  ".join(f"{s.value.title()} {sheet.stats[s]:+d}" for s in Stat))
    say(
        f"  Harm {sheet.harm}/6 ({harm_status(sheet.harm)})  "
        f"Fade {sheet.fade}/6 ({fade_status(sheet.fade)})"
    )
    say(f"  Knacks: {', '.join((*sheet.knacks, *sheet.advanced_knacks))}")
    if sheet.scars:
        say(f"  Scars: {', '.join(sheet.scars)}")
    say(f"  Purse: {format_glitter(character.currency)}   Bond: {character.bond}")
    if place is not None:
        say(f"  At: {place.name}{' (haven)' if place.is_haven else ''}")


def level_menu(session: PlaySession, content: Content, ask: Ask, say: Say) -> None:
    me = session.character
    if not can_level_up(me.sheet):
        say("Not enough XP yet.")
        return
    choice = choose(
        ask,
        say,
        "Level up. Pick one:",
        [
            ("new_knack", "A new knack"),
            ("stat_boost", "+1 to a stat"),
            ("heal_scar", "Heal a scar"),
        ],
    )
    fields: dict[str, str | None] = {}
    if choice == "new_knack":
        options = [(k.id, k.name) for k in content.knacks.values() if k.id not in me.sheet.knacks]
        fields["knack"] = choose(ask, say, "Which knack?", options)
    elif choice == "stat_boost":
        fields["stat"] = choose(ask, say, "Which stat?", [(s.value, s.value.title()) for s in Stat])
    else:
        if not me.sheet.scars:
            say("You have no scars to heal.")
            return
        fields["scar"] = choose(ask, say, "Which scar?", [(s, s) for s in me.sheet.scars])
    milestone = milestone_id = None
    if is_milestone(me.sheet.level + 1):
        milestone = choose(
            ask,
            say,
            "Milestone level. Also pick:",
            [
                ("advanced_knack", "An advanced knack"),
                ("origin_evolution", "An origin evolution"),
            ],
        )
        say("(Advanced knacks and evolutions aren't written yet; this will likely be refused.)")
        milestone_id = _ask(ask, "Its id: ")
    try:
        after = session.level(
            LevelUpRequest(
                choice,
                milestone=milestone,
                milestone_id=milestone_id,
                **fields,  # type: ignore[arg-type]
            )
        )
        say(f"You are level {after.sheet.level}.")
    except SessionError as exc:
        say(f"Can't level: {exc}")


def fall_or_endure_menu(session: PlaySession, ask: Ask, say: Say) -> bool:
    """Returns False if the character fell."""
    say("Your Harm is full. The dice don't decide this. You do.")
    choice = choose(
        ask,
        say,
        "Fall or Endure?",
        [
            ("endure", "Endure: survive, with a permanent scar or condition"),
            ("fall", "Fall: die performing a final act that changes the world"),
        ],
    )
    if choice == "fall":
        session.fall_or_endure("fall")
        say("Your story ends here. The city will remember how.")
        return False
    while True:
        scar = _ask(ask, "Name the scar in a few words (e.g. chrome-jaw): ")
        slug = "-".join(scar.lower().split())[:64]
        try:
            session.fall_or_endure("endure", slug)
            say(f"You endure. Scar: {slug}.")
            return True
        except SessionError as exc:
            say(f"Try another name: {exc}")


def terminal_width() -> int:
    """The width to wrap prose at: the terminal's, capped for readability."""
    return min(shutil.get_terminal_size((88, 24)).columns, 100) - 1


def wrap(text: str) -> str:
    """Wrap prose to the terminal, keeping paragraphs and never splitting words."""
    width = terminal_width()
    paragraphs = text.split("\n")
    return "\n".join(
        textwrap.fill(p, width=width, break_long_words=False, break_on_hyphens=False)
        if p.strip()
        else ""
        for p in paragraphs
    )


def report(outcome: TurnOutcome, say: Say) -> None:
    say("")
    say(wrap(outcome.narration))
    if outcome.changes:
        say(f"  [{'; '.join(outcome.changes)}]")
    if outcome.slipped:
        say("  [Your Fade is full. You have slipped into Old Vesper.]")
    if outcome.can_level_up:
        say("  [You can level up: /level]")
    say("")


def play(
    conn,
    content: Content,
    client: ModelClient,
    handle: str,
    ask: Ask,
    say: Say,
    *,
    design_text: str,
    config: DMConfig,
    rng: random.Random,
    budget: BudgetConfig | None = None,
) -> None:
    seed(conn, content)
    player = players.find_player(conn, handle) or players.create_player(
        conn, handle, Cause(Actor.PLAYER)
    )
    living = [c for c in characters.characters_of(conn, player.id) if not c.sheet.fallen]
    if not living:
        me = create_character(conn, content, player.id, ask, say)
    elif len(living) == 1:
        me = living[0]
    else:
        pick = choose(ask, say, "Play as:", [(str(c.id), c.name) for c in living])
        me = characters.get_character(conn, int(pick))
    while me.pronouns is None:
        answer = _ask(ask, f"{me.name}'s pronouns (e.g. she/her, he/him, they/them): ")
        try:
            me = characters.set_pronouns(conn, me.id, answer, Cause(Actor.PLAYER, player.id))
        except StateError as exc:
            say(f"That didn't work: {exc}")
    session = PlaySession(
        conn, content, client, design_text, rng, me.id, config=config, budget=budget
    )
    try:
        recap, notes, opening = session.start()
    except SessionError as exc:
        say(str(exc))
        return
    say(session.budget_status().allowance_message())
    if recap:
        say(wrap(f"While you were gone: {recap}"))
    for note in notes:
        say(f"  [{note}]")
    report(opening, say)
    if opening.quiet:
        session.end()
        return
    say("(/help for commands)")
    try:
        while True:
            line = _ask(ask, "> ")
            if not line:
                continue
            try:
                if line in ("/quit", "/exit"):
                    break
                if line == "/help":
                    say(HELP)
                elif line == "/look":
                    show_sheet(session.character, content, say)
                elif line == "/places":
                    here = content.locations.get(session.character.location_id or "")
                    for loc in content.locations_in(here.region_id if here else "market"):
                        say(f"  {loc.id}: {loc.name}")
                elif line.startswith("/go"):
                    report(session.go(line[3:].strip()), say)
                elif line == "/level":
                    level_menu(session, content, ask, say)
                elif line.startswith("/ask"):
                    say("")
                    say(wrap(session.ask(line[4:].strip())))
                    say("")
                elif line == "/budget":
                    say(session.budget_status().allowance_message())
                elif line.startswith("/"):
                    say("Unknown command. /help lists them.")
                else:
                    outcome = session.turn(line)
                    report(outcome, say)
                    if outcome.quiet:
                        break
                    if outcome.fall_or_endure_pending and not fall_or_endure_menu(
                        session, ask, say
                    ):
                        break
            except SessionError as exc:
                say(f"({exc})")
    except Quit:
        pass
    finally:
        session.end()
        place = content.locations.get(session.character.location_id or "")
        if place is not None and place.is_haven:
            say("You rest somewhere safe.")
        else:
            say("You lie low until you return.")


def main(
    argv: Sequence[str] | None = None,
    *,
    ask: Ask = input,
    say: Say = print,
    client_factory: Callable[[], ModelClient] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="new-vesper")
    sub = parser.add_subparsers(dest="command", required=True)
    play_cmd = sub.add_parser("play", help="play a scene in the terminal")
    play_cmd.add_argument("--db", default="vesper.db", help="SQLite file (default vesper.db)")
    play_cmd.add_argument("--handle", required=True, help="your player handle")
    play_cmd.add_argument("--seed", type=int, default=None, help="RNG seed, for testing")
    budget_cmd = sub.add_parser("budget", help="operator report: this month's spend")
    budget_cmd.add_argument("--db", default="vesper.db", help="SQLite file (default vesper.db)")
    args = parser.parse_args(argv)
    budget = BudgetConfig.from_env()

    if args.command == "budget":
        conn = open_database(args.db)
        try:
            for line in month_report(conn, budget, datetime.now(UTC)):
                say(line)
        finally:
            conn.close()
        return 0

    config = DMConfig.from_env()
    for call in CallType:
        price_of(config.model_for(call), PRICES)  # refuse to play with an unpriced model

    if client_factory is None:
        import anthropic  # only the real CLI needs the SDK

        client_factory = anthropic.Anthropic
    conn = open_database(args.db)
    try:
        play(
            conn,
            load_content(),
            client_factory(),
            args.handle,
            ask,
            say,
            design_text=DESIGN_DOC.read_text(encoding="utf-8"),
            config=config,
            rng=random.Random(args.seed),
            budget=budget,
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
