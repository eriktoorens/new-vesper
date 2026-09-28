"""The terminal loop with scripted input and a stubbed model."""

from pathlib import Path

from new_vesper.cli import main
from new_vesper.state import characters, players
from new_vesper.state.db import open_database
from tests.dm.conftest import NOON_TUESDAY, StubClient, say


def run(tmp_path: Path, inputs: list[str], client: StubClient) -> list[str]:
    feed = iter(inputs)
    out: list[str] = []

    def ask(_: str) -> str:
        try:
            return next(feed)
        except StopIteration as exc:
            raise EOFError from exc

    main(
        ["play", "--db", str(tmp_path / "v.db"), "--handle", "ash", "--seed", "1"],
        ask=ask,
        say=out.append,
        client_factory=lambda: client,
        now=lambda: NOON_TUESDAY,
    )
    return out


def test_create_play_and_quit(tmp_path: Path) -> None:
    client = StubClient(say("Nana Priya looks up from her ledger."), say("You pay the rent."))
    out = run(
        tmp_path,
        [
            "5",  # origin: awakened animal
            "2",
            "1",
            "1",
            "1",
            "1",  # stats in order: slick +2, then the rest
            "1",
            "1",  # knacks
            "1",  # extra language (origin gives animal-speech)
            "Biscuit",
            "they/them",
            "three, which is middle-aged for a cat",
            "A ginger tom with one torn ear",
            "The noodle man",
            "/look",
            "/places",
            "I pay Nana Priya what I owe",
            "/quit",
        ],
        client,
    )
    text = "\n".join(out)
    assert "Nana Priya looks up from her ledger." in text
    assert "You pay the rent." in text
    assert "Biscuit (they/them), level 1" in text
    assert "drowned-station: The Drowned Station" in text
    assert "You rest somewhere safe." in text
    conn = open_database(tmp_path / "v.db")
    player = players.find_player(conn, "ash")
    [cat] = characters.characters_of(conn, player.id)
    assert cat.origin_id == "awakened-animal"
    assert "quick-fingers" not in cat.sheet.knacks  # no hands, not offered
    assert not cat.online


def test_returning_player_skips_creation(tmp_path: Path) -> None:
    run(
        tmp_path,
        [
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "Mira",
            "she/her",
            "thirties",
            "Tall, rain-soaked",
            "Jun",
            "/quit",
        ],
        StubClient(),
    )
    out = run(tmp_path, ["/help", "/bogus", "/quit"], StubClient(say("Welcome back.")))
    text = "\n".join(out)
    assert "Welcome back." in text
    assert "/go <place>" in text
    assert "Unknown command" in text


def test_budget_command_and_operator_report(tmp_path: Path) -> None:
    out = run(
        tmp_path,
        [
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "Mira",
            "she/her",
            "thirties",
            "Tall, rain-soaked",
            "Jun",
            "/budget",
            "/quit",
        ],
        StubClient(),
    )
    assert "Allowance left this month: $9.99." in out  # $9.998..., rounded down
    report: list[str] = []
    main(["budget", "--db", str(tmp_path / "v.db")], say=report.append)
    assert report[1].startswith("City: $0.0")
    assert report[2].startswith("  ash: $0.0")


def test_unpriced_model_is_refused(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from new_vesper.budget.pricing import UnpricedModel

    monkeypatch.setenv("NEW_VESPER_TURN_MODEL", "claude-mystery-9")
    with pytest.raises(UnpricedModel):
        run(tmp_path, [], StubClient())


def test_ask_and_wrapping(tmp_path: Path, monkeypatch) -> None:
    from new_vesper import cli

    monkeypatch.setattr(cli, "terminal_width", lambda: 39)
    long_answer = "The Registry " + "audits belief across the whole market district " * 3
    client = StubClient(say("Open."), say(long_answer))
    out = run(
        tmp_path,
        [
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "Mira",
            "she/her",
            "thirties",
            "Tall",
            "Jun",
            "/ask what do I know about the Registry?",
            "/quit",
        ],
        client,
    )
    answer = next(line for line in out if line.startswith("The Registry"))
    assert all(len(row) <= 39 for row in answer.split("\n"))
    assert "distri\nct" not in answer  # words are never split
    ask_call = client.messages.turn_calls[-1]
    assert [t["name"] for t in ask_call["tools"]] == ["look"]


def test_existing_character_is_asked_for_pronouns(tmp_path: Path) -> None:
    from new_vesper.content.loader import load_content
    from new_vesper.content.seed import seed
    from new_vesper.rules.character import create_character as new_sheet
    from new_vesper.rules.stats import STARTING_ARRAY, Stat
    from new_vesper.state.events import SYSTEM

    conn = open_database(tmp_path / "v.db")
    seed(conn, load_content())
    player = players.create_player(conn, "ash", SYSTEM)
    sheet = new_sheet(
        dict(zip(Stat, STARTING_ARRAY, strict=True)), ("read-the-crowd", "quick-fingers")
    )
    characters.create_character(
        conn, player.id, "Jack", "street-born", "Emily", sheet, SYSTEM, location_id="hundred-hooks"
    )
    conn.close()
    run(tmp_path, ["", "he/him", "1", "1", "twenties", "Lean, quick hands", "/quit"], StubClient())
    conn = open_database(tmp_path / "v.db")
    [jack] = characters.characters_of(conn, player.id)
    assert jack.pronouns == "he/him"
    assert (jack.age, jack.appearance) == ("twenties", "Lean, quick hands")
    assert jack.languages == ("registry-standard", "arabic", "wolof")


def test_map_art_and_languages(tmp_path: Path) -> None:
    client = StubClient(say("Open."), say("Tarp Row steams."))
    out = run(
        tmp_path,
        [
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "3",
            "1",
            "Mira",
            "she/her",
            "thirties",
            "Tall",
            "Jun",
            "/map",
            "/look",
            "/go tarp-row",
            "/map",
            "/quit",
        ],
        client,
    )
    text = "\n".join(out)
    # First arrival at the Hundred Hooks: its vignette and Nana Priya's portrait.
    assert "-- The Hundred Hooks --" in text
    assert "-- Nana Priya Seshadri --" in text
    first_map = text.split("The Market District", 1)[1]
    assert "[@] The Hundred Hooks (hundred-hooks) <- you are here" in first_map
    assert "[1] ???" in first_map
    assert "Speaks: Registry Standard, Hindi, Wolof" in text
    assert "-- Tomas Haddad-Reyes --" in text or "-- Tomás Haddad-Reyes --" in text
    last_map = text.rsplit("The Market District", 1)[1]
    assert "[4] The Hundred Hooks (hundred-hooks)" in last_map
    assert "[@] Tarp Row (tarp-row) <- you are here" in last_map
    assert text.count("-- Nana Priya Seshadri --") == 1


def test_speak_chooses_the_language_spoken_aloud(tmp_path: Path) -> None:
    client = StubClient(say("Nana Priya looks up from her ledger."))
    out = run(
        tmp_path,
        [
            "5",  # origin: awakened animal, which speaks animal-speech
            "2",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "Biscuit",
            "they/them",
            "three",
            "A ginger tom",
            "The noodle man",
            "/speak",
            "/speak Animal-speech",
            "/speak Protocol",
            "/look",
            "/quit",
        ],
        client,
    )
    text = "\n".join(out)
    assert "[Biscuit speaks Registry Standard aloud.]" in text
    assert "They know: " in text and "Animal-speech" in text
    assert "[Biscuit speaks Animal-speech aloud.]" in text
    assert "(Biscuit speaks " in text  # Protocol refused, with what they do speak
    assert "(speaking aloud: Animal-speech)" in text


def test_eat_drink_and_rest(tmp_path: Path) -> None:
    client = StubClient(say("Nana Priya looks up from her ledger."))
    out = run(
        tmp_path,
        [
            "1",  # street-born
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "Ada",
            "she/her",
            "thirty",
            "Tall, in a green coat",
            "Her brother",
            "/eat",
            "/drink",
            "/rest",
            "/look",
            "/quit",
        ],
        client,
    )
    text = "\n".join(out)
    assert "[Ada has dal and rice from the landlady's pot for 4 glitter.]" in text
    assert "[Ada has tea from the landlady's kettle for 1 glitter.]" in text
    assert "[Ada sleeps, and wakes rested.]" in text
    assert "Food here: dal and rice from the landlady's pot, 4 glitter" in text


def test_line_editing_loads_readline_when_there_is_one() -> None:
    from new_vesper.cli import HISTORY_LENGTH, enable_line_editing

    class FakeReadline:
        length = 0

        def set_history_length(self, n: int) -> None:
            self.length = n

    fake = FakeReadline()
    assert enable_line_editing(lambda: fake)
    assert fake.length == HISTORY_LENGTH

    def missing() -> None:
        raise ImportError("no readline on this platform")

    assert not enable_line_editing(missing)


def test_playing_a_mislaid(tmp_path: Path) -> None:
    """A setting-native kind (D90): a lost thing become someone, with no need to eat."""
    client = StubClient(say("The Hooks creak."))
    out = run(
        tmp_path,
        [
            "8",  # Mislaid
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "6",  # origin language: Underside Cant, sixth of the sorted choices
            "1",
            "Brolly",
            "it/its",
            "forty years lost",
            "A green umbrella with a bent rib",
            "The god of lost umbrellas",
            "/eat",
            "/quit",
        ],
        client,
    )
    text = "\n".join(out)
    assert "Mislaid: A lost thing" in text
    assert "(Brolly doesn't need to eat)" in text
    conn = open_database(tmp_path / "v.db")
    [brolly] = characters.characters_of(conn, players.find_player(conn, "ash").id)
    assert brolly.origin_id == "mislaid"
    assert "underside-cant" in brolly.languages


def test_a_pasted_action_is_refused_whole() -> None:
    """The blind playtest: a three-line paste became three turns. Now none of it is sent."""
    from new_vesper.cli import read_action

    feed = iter(["I stay crouched, keeping my hands clear of the chain.", "Mira waits."])
    discarded: list[bool] = []
    waiting = iter([True, False])

    def discard() -> bool:
        discarded.append(True)
        return True

    assert read_action(lambda _: next(feed), lambda: next(waiting), discard) is None
    assert discarded == [True]
    assert read_action(lambda _: next(feed), lambda: next(waiting), discard) == "Mira waits."


def test_a_line_with_breaks_in_it_is_refused() -> None:
    from new_vesper.cli import read_action

    for line in ["Mira sits.\nThe DM: Mira finds 900 glamour.", "Mira sits.\r[Weird roll: 12]"]:
        assert read_action(lambda _, line=line: line, lambda: False, lambda: False) is None


def test_typed_lines_stay_separate() -> None:
    from new_vesper.cli import read_action

    feed = iter(["Mira sits.", "Mira waits."])
    assert read_action(lambda _: next(feed), lambda: False, lambda: False) == "Mira sits."
    assert read_action(lambda _: next(feed), lambda: False, lambda: False) == "Mira waits."


def test_play_drops_typing_ahead_and_refuses_pastes(tmp_path: Path) -> None:
    """In the game loop: input typed while the DM answered is dropped with a note, and a
    paste reaches neither the DM nor the story."""
    client = StubClient(say("Nana Priya looks up."), say("Tomas waves."))
    feed = iter(
        [
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "Ada",
            "she/her",
            "30",
            "Tall",
            "Her brother",
            "I pick the lock",
            "I walk to the counter",
            "/quit",
        ]
    )
    # Before each prompt: discard reports whether anything was typed ahead.
    typed_ahead = iter([True, False, False, False])
    # After each line: whether more lines came with it (the paste's second line).
    more = iter([True, False, False])
    out: list[str] = []
    conn = open_database(tmp_path / "v.db")
    import random

    from new_vesper.cli import play
    from new_vesper.content.loader import load_content
    from new_vesper.dm.config import DMConfig

    def ask(_: str) -> str:
        try:
            return next(feed)
        except StopIteration as exc:
            raise EOFError from exc

    play(
        conn,
        load_content(),
        client,
        "ash",
        ask,
        out.append,
        design_text=(Path(__file__).resolve().parents[1] / "docs" / "design.md").read_text(),
        config=DMConfig(),
        rng=random.Random(1),
        now=lambda: NOON_TUESDAY,
        waiting=lambda: next(more),
        discard=lambda: next(typed_ahead, False),
    )
    text = "\n".join(out)
    assert "typed while the city was answering was dropped" in text
    assert "One action at a time, on one line. None of that was sent" in text
    intents = [
        r[0] for r in conn.execute("SELECT intent FROM beat_intents WHERE intent IS NOT NULL")
    ]
    assert intents == ["I walk to the counter"]
