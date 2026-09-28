import json
import sqlite3

from new_vesper.content.loader import Content
from new_vesper.dm.session import PlaySession
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    SeqRng,
    StubClient,
    make_character,
    say,
)


class Always:
    """Encounter dice: every check succeeds, and draws take the first option."""

    def randint(self, a: int, b: int) -> int:
        return a


def state_of(client: StubClient, n: int) -> dict:
    message = client.messages.turn_calls[n]["messages"][0]["content"]
    return json.loads(message.split("<scene_state>")[1].split("</scene_state>")[0])


def test_arrival_encounter_reaches_the_dm(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False, location="tarp-row")
    client = StubClient(say("Steam and shouting."))
    play = PlaySession(
        conn,
        content,
        client,
        DESIGN_TEXT,
        SeqRng(),
        char.id,
        now=lambda: NOON_TUESDAY,
        encounter_rng=Always(),
    )
    play.start()
    state = state_of(client, 0)
    assert state["encounter"]["kind"] in {"color", "opportunity", "trouble"}
    message = client.messages.turn_calls[0]["messages"][0]["content"]
    assert "An encounter happens now" in message and "arrived here" in message


def test_every_fifth_beat_checks(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False, location="tarp-row")

    class Counting(Always):
        def __init__(self) -> None:
            self.checks = 0

        def randint(self, a: int, b: int) -> int:
            if (a, b) == (1, 100):
                self.checks += 1
                return 100  # never happens: just count the checks
            return a

    dice = Counting()
    play = PlaySession(
        conn,
        content,
        StubClient(),
        DESIGN_TEXT,
        SeqRng(),
        char.id,
        now=lambda: NOON_TUESDAY,
        encounter_rng=dice,
    )
    play.start()  # beat 1, with an arrival check
    for n in range(8):
        play.turn(f"I wait, {n}")  # beats 2-9: beat 5 checks
    assert dice.checks == 2


def test_encounters_off_without_dice(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False, location="tarp-row")
    client = StubClient(say("Quiet."))
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    assert "encounter" not in state_of(client, 0)
    assert conn.execute("SELECT COUNT(*) FROM encounters").fetchone()[0] == 0
