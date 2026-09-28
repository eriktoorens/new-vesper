"""Languages in the state layer (D78-D81): gist rolls, the speech log, speaking aloud."""

import sqlite3

import pytest

from new_vesper.rules.languages import COMMON_TONGUE, Heard
from new_vesper.rules.resolver import Difficulty, resolve
from new_vesper.rules.stats import Stat
from new_vesper.state import characters, rolls, scenes, speech, world
from new_vesper.state.characters import Character
from new_vesper.state.errors import StateError
from new_vesper.state.events import SYSTEM, list_events
from tests.rules.conftest import FixedDice


@pytest.fixture
def tongues(conn: sqlite3.Connection) -> None:
    world.add_language(conn, COMMON_TONGUE, "Registry Standard", True, SYSTEM)
    world.add_language(conn, "wolof", "Wolof", True, SYSTEM)


def gist_roll(conn: sqlite3.Connection, char: Character, scene_id: int) -> rolls.Roll:
    result = resolve(-1, Difficulty.RISKY, FixedDice([4, 4]))
    return rolls.record_roll(
        conn,
        char.id,
        scene_id,
        Stat.HEART,
        Difficulty.RISKY,
        result,
        "follow the haggling",
        SYSTEM,
        language_id="wolof",
    )


def test_a_gist_roll_keeps_its_language_and_the_cost_it_paid(
    conn: sqlite3.Connection, mira: Character, tongues: None
) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    roll = gist_roll(conn, mira, scene.id)
    assert roll.language_id == "wolof" and roll.consequence_type is None
    assert rolls.gist_rolls(conn, mira.id, scene.id) == [roll]
    used = rolls.use_roll(conn, roll.id, rolls.RollUse.CONSEQUENCE, "add_fade")
    assert used.consequence_type == "add_fade"
    assert list_events(conn, character_id=mira.id, kind="roll")[-1].payload["language"] == "wolof"
    for sql in (
        "UPDATE rolls SET consequence_type = 'narrative_cost' WHERE id = ?",
        "UPDATE rolls SET language_id = NULL WHERE id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (roll.id,))


def test_ordinary_rolls_are_not_gist_rolls(conn: sqlite3.Connection, mira: Character) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    result = resolve(1, Difficulty.RISKY, FixedDice([3, 4]))
    rolls.record_roll(conn, mira.id, scene.id, Stat.SLICK, Difficulty.RISKY, result, "s", SYSTEM)
    assert rolls.gist_rolls(conn, mira.id, scene.id) == []


def test_the_speech_log_is_append_only(
    conn: sqlite3.Connection, mira: Character, tongues: None
) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    line = speech.record_line(
        conn,
        scene.id,
        mira.id,
        speaker="a fishmonger",
        npc_id=None,
        language_id="wolof",
        words="Fresh from the flats!",
        tone="loud",
        gist=" ",
        heard=Heard.NONE,
    )
    assert (line.tone, line.gist, line.heard) == ("loud", None, Heard.NONE)
    assert speech.lines_in_scene(conn, scene.id, mira.id) == [line]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE speech_lines SET heard = 'fluent' WHERE id = ?", (line.id,))


@pytest.mark.parametrize(
    "bad",
    [{"words": ""}, {"words": "x" * 601}, {"speaker": ""}, {"tone": "t" * 81}, {"words": 7}],
)
def test_bad_speech_lines_refused(
    conn: sqlite3.Connection, mira: Character, tongues: None, bad: dict[str, object]
) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    fields: dict[str, object] = {
        "speaker": "a fishmonger",
        "npc_id": None,
        "language_id": "wolof",
        "words": "Fresh!",
        "tone": None,
        "gist": None,
        "heard": Heard.NONE,
    }
    with pytest.raises(StateError):
        speech.record_line(conn, scene.id, mira.id, **(fields | bad))  # type: ignore[arg-type]


def test_speaking_aloud_defaults_to_the_common_tongue(
    conn: sqlite3.Connection, mira: Character, tongues: None
) -> None:
    assert mira.speaking == COMMON_TONGUE and mira.speaks == {COMMON_TONGUE}
    with pytest.raises(StateError, match="doesn't speak"):
        characters.set_speaking(conn, mira.id, "wolof", SYSTEM)
    mira = characters.set_details(
        conn, mira.id, SYSTEM, age="30", appearance="tall", languages=("wolof",)
    )
    assert characters.set_speaking(conn, mira.id, "Wolof".lower(), SYSTEM).speaking == "wolof"
    assert list_events(conn, character_id=mira.id)[-1].kind == "speaking_changed"
