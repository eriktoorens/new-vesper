"""Terminal entry point: `new-vesper play --db vesper.db --handle ash`.

The player makes every creation and leveling choice here, through menus (D17).
Everything else goes to the DM through PlaySession.
"""

import argparse
import importlib
import random
import shutil
import sys
import textwrap
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from new_vesper.budget.policy import BudgetConfig
from new_vesper.budget.pricing import PRICES, price_of
from new_vesper.budget.report import month_report
from new_vesper.content.languages import (
    extra_language_options,
    origin_language_options,
    starting_languages,
)
from new_vesper.content.loader import Content, load_content
from new_vesper.content.maps import render_map
from new_vesper.content.seed import seed
from new_vesper.dm.agent import ModelClient
from new_vesper.dm.config import CallType, DMConfig
from new_vesper.dm.handlers import NEEDS_HANDS, NO_HANDS
from new_vesper.dm.session import ONE_LINE, PlaySession, SessionError, TurnOutcome
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.rules.currency import format_glitter
from new_vesper.rules.errors import RulesError
from new_vesper.rules.languages import COMMON_TONGUE
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
  /map           the district map: where you are and where you've been
  /time          the city clock and the weather
  /who           who's here and what they're doing
  /ask <question>  ask the DM what your character sees or knows (no time passes)
  /speak <language>  choose the language your character speaks aloud
  /eat, /drink   buy food or drink where it's sold
  /export        save your story, as your character would tell it
  /export record save your story exactly as you saw it
  /rest          sleep at a haven
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


# How long to wait for the rest of a paste before judging the line alone.
PASTE_WINDOW = 0.05
TYPED_AHEAD = "(What you typed while the city was answering was dropped: act on what you've seen.)"


def stdin_has_more(timeout: float = PASTE_WINDOW) -> bool:
    """Whether more input is already waiting, such as the next line of a paste.

    POSIX terminals only; elsewhere this is always False.
    """
    try:
        import select

        ready, _, _ = select.select([sys.stdin], [], [], timeout)
    except (ImportError, OSError, ValueError):
        return False
    return bool(ready)


def discard_waiting() -> bool:
    """Throw away input that is already waiting. Returns whether there was any."""
    if not stdin_has_more(0):
        return False
    try:
        import termios

        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except (ImportError, OSError, ValueError):
        return False
    return True


def read_action(ask: Ask, waiting: Callable[[], bool], discard: Callable[[], bool]) -> str | None:
    """One player action: one line, typed after they've seen the world's last answer (D99).

    Returns None for a line that came with others, as a multi-line paste does:
    the whole paste is refused, so no part of it reaches the DM and no action
    is taken on a world the player hasn't seen yet.
    """
    line = _ask(ask, "> ")
    if waiting() or "\n" in line or "\r" in line:
        discard()
        return None
    return line


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
    languages = choose_languages(content, origin, ask, say)
    while True:
        name = _ask(ask, "Name: ")
        pronouns = _ask(ask, "Pronouns (e.g. she/her, he/him, they/them): ")
        age, appearance = ask_age_and_looks(ask)
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
                age=age,
                appearance=appearance,
                languages=languages,
            )
        except (RulesError, StateError) as exc:
            say(f"That didn't work: {exc}")


def choose_languages(content: Content, origin: str, ask: Ask, say: Say) -> tuple[str, ...]:
    """Registry Standard, the origin's language, and one more (D37)."""
    names = {lang.id: lang.name for lang in content.languages.values()}
    options = origin_language_options(content, origin)
    if len(options) == 1:
        pick = options[0]
        say(f"You speak Registry Standard, like everyone, and {names[pick]} from your origin.")
    else:
        say("You speak Registry Standard, like everyone.")
        pick = choose(ask, say, "Your origin's language:", [(o, names[o]) for o in options])
    extras = extra_language_options(content, (COMMON_TONGUE, pick))
    extra = choose(
        ask,
        say,
        "One more language:",
        [
            (e, f"{names[e]} ({'common' if content.languages[e].common else 'rare'})")
            for e in extras
        ],
    )
    return starting_languages(content, origin, pick, extra)


def ask_age_and_looks(ask: Ask) -> tuple[str, str]:
    age = _ask(ask, "Age, in a few words (e.g. mid-twenties, built three winters ago): ")
    looks = _ask(ask, "Appearance, in a line (what people notice first): ")
    return age, looks


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
    if character.age:
        say(f"  Age: {character.age}")
    if character.appearance:
        say(wrap(f"  Looks: {character.appearance}"))
    if character.languages:
        spoken = [content.languages[lang].name for lang in character.languages]
        aloud = content.languages[character.speaking].name
        say(f"  Speaks: {', '.join(spoken)}  (speaking aloud: {aloud})")
    if place is not None:
        say(f"  At: {place.name}{' (haven)' if place.is_haven else ''}")
        for need, offer in sorted(place.provisions.items()):
            kind = "Food" if need.value == "hunger" else "Drink"
            price = format_glitter(offer.price) if offer.price else "free"
            say(f"  {kind} here: {offer.what}, {price}")


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
    for block in outcome.art:
        say(block)
        say("")
    if outcome.status:
        say(f"[{outcome.status}]")
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
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    waiting: Callable[[], bool] | None = None,
    discard: Callable[[], bool] | None = None,
) -> None:
    """The terminal game.

    ``waiting`` says whether more input has already arrived; ``discard`` throws
    it away and says whether there was any. Both default to the real terminal.
    """
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
    while me.age is None or me.appearance is None or not me.languages:
        say(f"The city wants to know a little more about {me.name}.")
        languages = choose_languages(content, me.origin_id, ask, say)
        age, looks = ask_age_and_looks(ask)
        try:
            me = characters.set_details(
                conn,
                me.id,
                Cause(Actor.PLAYER, player.id),
                age=age,
                appearance=looks,
                languages=languages,
            )
        except StateError as exc:
            say(f"That didn't work: {exc}")
    session = PlaySession(
        conn,
        content,
        client,
        design_text,
        rng,
        me.id,
        config=config,
        budget=budget,
        now=now,
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
    live = ask is input and sys.stdin.isatty()
    waiting = waiting or (stdin_has_more if live else (lambda: False))
    discard = discard or (discard_waiting if live else (lambda: False))
    try:
        while True:
            if discard():
                say(TYPED_AHEAD)
            line = read_action(ask, waiting, discard)
            if line is None:
                say(f"({ONE_LINE})")
                continue
            if not line:
                continue
            try:
                if line in ("/quit", "/exit"):
                    break
                if line == "/help":
                    say(HELP)
                elif line == "/who":
                    people = session.who()
                    say("\n".join(f"  {p}" for p in people) if people else "  Nobody you know.")
                elif line == "/time":
                    say(f"[{session.status_line()}]")
                elif line == "/look":
                    art = session.location_art()
                    if art:
                        say(art)
                    say(f"[{session.status_line()}]")
                    show_sheet(session.character, content, say)
                elif line == "/map":
                    me = session.character
                    here = content.locations.get(me.location_id or "")
                    if here is None:
                        say("You're nowhere on any map.")
                    else:
                        visited = characters.visited_locations(conn, me.id)
                        for row in render_map(content, here.region_id, here.id, visited):
                            say(row)
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
                elif line.startswith("/speak"):
                    choice = line[len("/speak") :].strip()
                    me = session.character
                    if choice:
                        me = session.speak(choice)
                    known = ", ".join(content.languages[lang].name for lang in sorted(me.speaks))
                    say(f"  [{me.name} speaks {content.languages[me.speaking].name} aloud.]")
                    if not choice:
                        say(f"  [They know: {known}. /speak <language> to change.]")
                elif line.startswith("/export"):
                    kind = line[len("/export") :].strip() or "telling"
                    if kind == "telling":
                        say("  [Writing it down...]")
                    say(f"  [Saved: {session.export(kind)}]")
                elif line in ("/eat", "/drink", "/rest"):
                    action = {"/eat": session.eat, "/drink": session.drink, "/rest": session.rest}
                    say(f"  [{action[line]()}]")
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


# Lines kept for the up arrow within a session.
HISTORY_LENGTH = 500


def enable_line_editing(load: Callable[[], Any] | None = None) -> bool:
    """Arrow keys, history and the usual shortcuts when typing at the prompt.

    ``input()`` only edits lines if the readline module is loaded; without it,
    a Mac terminal allows nothing but backspace. Windows has no readline, but its
    console already edits lines. Returns whether line editing is on.
    """
    try:
        module = load() if load is not None else importlib.import_module("readline")
    except ImportError:
        return False
    module.set_history_length(HISTORY_LENGTH)
    return True


def export_story(
    args: argparse.Namespace,
    say: Say,
    config: DMConfig,
    budget: BudgetConfig,
    client_factory: Callable[[], ModelClient],
    now: Callable[[], datetime],
) -> int:
    """`new-vesper export`: the story of any character, living or fallen (D104)."""
    conn = open_database(args.db)
    try:
        player = players.find_player(conn, args.handle)
        everyone = characters.characters_of(conn, player.id) if player else []
        if args.character:
            everyone = [c for c in everyone if c.name.casefold() == args.character.casefold()]
        if not everyone:
            say("No such character.")
            return 1
        me = max(everyone, key=lambda c: c.id)
        content = load_content()
        seed(conn, content)
        client = None if args.record else client_factory()
        session = PlaySession(
            conn,
            content,
            client,  # type: ignore[arg-type]
            DESIGN_DOC.read_text(encoding="utf-8"),
            random.Random(),
            me.id,
            config=config,
            budget=budget,
            now=now,
        )
        try:
            path = session.export("record" if args.record else "telling", Path(args.out))
        except SessionError as exc:
            say(str(exc))
            return 1
        say(f"Saved: {path}")
        return 0
    finally:
        conn.close()


def main(
    argv: Sequence[str] | None = None,
    *,
    ask: Ask = input,
    say: Say = print,
    client_factory: Callable[[], ModelClient] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    parser = argparse.ArgumentParser(prog="new-vesper")
    sub = parser.add_subparsers(dest="command", required=True)
    play_cmd = sub.add_parser("play", help="play a scene in the terminal")
    play_cmd.add_argument("--db", default="vesper.db", help="SQLite file (default vesper.db)")
    play_cmd.add_argument("--handle", required=True, help="your player handle")
    play_cmd.add_argument("--seed", type=int, default=None, help="RNG seed, for testing")
    budget_cmd = sub.add_parser("budget", help="operator report: this month's spend")
    budget_cmd.add_argument("--db", default="vesper.db", help="SQLite file (default vesper.db)")
    export_cmd = sub.add_parser("export", help="save a character's story, even one who has fallen")
    export_cmd.add_argument("--db", default="vesper.db", help="SQLite file (default vesper.db)")
    export_cmd.add_argument("--handle", required=True, help="the player's handle")
    export_cmd.add_argument("--character", help="which character, by name (default: newest)")
    export_cmd.add_argument(
        "--record", action="store_true", help="exactly as seen, instead of as told (free)"
    )
    export_cmd.add_argument("--out", default="stories", help="folder (default stories)")
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
    if args.command == "export":
        return export_story(args, say, config, budget, client_factory, now)
    if ask is input and sys.stdin.isatty():
        enable_line_editing()
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
            now=now,
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
