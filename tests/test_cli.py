"""The terminal loop with scripted input and a stubbed model."""

from pathlib import Path

from new_vesper.cli import main
from new_vesper.state import characters, players
from new_vesper.state.db import open_database
from tests.dm.conftest import StubClient, say


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
            "Biscuit",
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
    assert "Biscuit, level 1" in text
    assert "drowned-station: The Drowned Station" in text
    assert "You rest somewhere safe." in text
    conn = open_database(tmp_path / "v.db")
    player = players.find_player(conn, "ash")
    [cat] = characters.characters_of(conn, player.id)
    assert cat.origin_id == "awakened-animal"
    assert "quick-fingers" not in cat.sheet.knacks  # no hands, not offered
    assert not cat.online


def test_returning_player_skips_creation(tmp_path: Path) -> None:
    run(tmp_path, ["1", "1", "1", "1", "1", "1", "1", "1", "Mira", "Jun", "/quit"], StubClient())
    out = run(tmp_path, ["/help", "/bogus", "/quit"], StubClient(say("Welcome back.")))
    text = "\n".join(out)
    assert "Welcome back." in text
    assert "/go <place>" in text
    assert "Unknown command" in text
