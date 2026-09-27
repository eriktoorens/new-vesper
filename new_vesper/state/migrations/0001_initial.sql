-- 0001: initial schema. One file per schema change; never edit an applied file.

CREATE TABLE players (
    id          INTEGER PRIMARY KEY,
    handle      TEXT NOT NULL UNIQUE CHECK (length(handle) BETWEEN 1 AND 40),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Origins replace race and class: one narrative trait plus tags code enforces.
CREATE TABLE origins (
    id     TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    trait  TEXT NOT NULL
);

CREATE TABLE origin_tags (
    origin_id  TEXT NOT NULL REFERENCES origins (id),
    tag        TEXT NOT NULL,
    PRIMARY KEY (origin_id, tag)
);

-- The shared knack catalog, in the fixed template: trigger, stat, 10+ effect,
-- 7-9 effect, limits. Player-proposed knacks wait here unapproved.
CREATE TABLE knacks (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    stat          TEXT NOT NULL CHECK (stat IN ('steel', 'slick', 'wire', 'weird', 'heart')),
    trigger_text  TEXT NOT NULL,
    clean_effect  TEXT NOT NULL,
    cost_effect   TEXT NOT NULL,
    limits        TEXT NOT NULL DEFAULT '',
    roll_bonus    INTEGER NOT NULL DEFAULT 0 CHECK (roll_bonus BETWEEN 0 AND 1),
    advanced      INTEGER NOT NULL DEFAULT 0 CHECK (advanced IN (0, 1)),
    approved      INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1))
);

CREATE TABLE knack_tags (
    knack_id  TEXT NOT NULL REFERENCES knacks (id),
    tag       TEXT NOT NULL,
    PRIMARY KEY (knack_id, tag)
);

-- Light 0-10. At zero the region has fallen into Old Vesper.
CREATE TABLE regions (
    id     TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    light  INTEGER NOT NULL CHECK (light BETWEEN 0 AND 10)
);

-- Places inside a region. Havens (lodging, shrines, Bonds' homes) are safe.
CREATE TABLE locations (
    id         TEXT PRIMARY KEY,
    region_id  TEXT NOT NULL REFERENCES regions (id),
    name       TEXT NOT NULL,
    is_haven   INTEGER NOT NULL DEFAULT 0 CHECK (is_haven IN (0, 1))
);

CREATE TABLE characters (
    id            INTEGER PRIMARY KEY,
    player_id     INTEGER NOT NULL REFERENCES players (id),
    name          TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 60),
    origin_id     TEXT NOT NULL REFERENCES origins (id),
    bond          TEXT NOT NULL CHECK (length(bond) BETWEEN 1 AND 200),
    level         INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    xp            INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
    harm          INTEGER NOT NULL DEFAULT 0 CHECK (harm BETWEEN 0 AND 6),
    fade          INTEGER NOT NULL DEFAULT 0 CHECK (fade BETWEEN 0 AND 6),
    steel         INTEGER NOT NULL CHECK (steel BETWEEN -1 AND 4),
    slick         INTEGER NOT NULL CHECK (slick BETWEEN -1 AND 4),
    wire          INTEGER NOT NULL CHECK (wire BETWEEN -1 AND 4),
    weird         INTEGER NOT NULL CHECK (weird BETWEEN -1 AND 4),
    heart         INTEGER NOT NULL CHECK (heart BETWEEN -1 AND 4),
    boosted_stat  TEXT CHECK (boosted_stat IN ('steel', 'slick', 'wire', 'weird', 'heart')),
    currency      INTEGER NOT NULL DEFAULT 0 CHECK (currency >= 0),
    fallen        INTEGER NOT NULL DEFAULT 0 CHECK (fallen IN (0, 1)),
    slipped       INTEGER NOT NULL DEFAULT 0 CHECK (slipped IN (0, 1)),
    online        INTEGER NOT NULL DEFAULT 0 CHECK (online IN (0, 1)),
    location_id   TEXT REFERENCES locations (id),
    version       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    -- Only the one stat an advanced knack boosted may reach +4.
    CHECK (steel <= 3 OR boosted_stat IS 'steel'),
    CHECK (slick <= 3 OR boosted_stat IS 'slick'),
    CHECK (wire <= 3 OR boosted_stat IS 'wire'),
    CHECK (weird <= 3 OR boosted_stat IS 'weird'),
    CHECK (heart <= 3 OR boosted_stat IS 'heart')
);

CREATE INDEX characters_player ON characters (player_id);
CREATE INDEX characters_location ON characters (location_id);

-- kind: 'knack' for ordinary knacks, 'advanced' for milestone advanced knacks.
CREATE TABLE character_knacks (
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    knack_id      TEXT NOT NULL REFERENCES knacks (id),
    kind          TEXT NOT NULL CHECK (kind IN ('knack', 'advanced')),
    position      INTEGER NOT NULL,
    PRIMARY KEY (character_id, knack_id)
);

CREATE TABLE character_scars (
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    scar_id       TEXT NOT NULL,
    position      INTEGER NOT NULL,
    PRIMARY KEY (character_id, scar_id)
);

CREATE TABLE character_evolutions (
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    evolution_id  TEXT NOT NULL,
    position      INTEGER NOT NULL,
    PRIMARY KEY (character_id, evolution_id)
);

-- Item instances. Kinds come from content loot tables; the DM never invents them.
-- An item is held by a character, lies at a location, or neither (destroyed).
CREATE TABLE items (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL,
    name          TEXT NOT NULL,
    character_id  INTEGER REFERENCES characters (id),
    location_id   TEXT REFERENCES locations (id),
    destroyed     INTEGER NOT NULL DEFAULT 0 CHECK (destroyed IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (character_id IS NULL OR location_id IS NULL),
    CHECK (destroyed = 0 OR (character_id IS NULL AND location_id IS NULL))
);

CREATE INDEX items_character ON items (character_id);

-- The favor ledger: every favor owed to a god. Gods collect.
CREATE TABLE favors (
    id            INTEGER PRIMARY KEY,
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    god_id        TEXT NOT NULL,
    reason        TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'owed' CHECK (status IN ('owed', 'collected')),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    collected_at  TEXT
);

-- A favor is written once and may only move from owed to collected.
CREATE TRIGGER favors_no_delete BEFORE DELETE ON favors
BEGIN
    SELECT RAISE(ABORT, 'the favor ledger is append-only');
END;

CREATE TRIGGER favors_collect_only BEFORE UPDATE ON favors
WHEN NOT (
    OLD.status = 'owed' AND NEW.status = 'collected'
    AND NEW.id = OLD.id AND NEW.character_id = OLD.character_id
    AND NEW.god_id = OLD.god_id AND NEW.reason = OLD.reason
    AND NEW.created_at = OLD.created_at
)
BEGIN
    SELECT RAISE(ABORT, 'a favor may only move from owed to collected');
END;

CREATE TABLE scenes (
    id           INTEGER PRIMARY KEY,
    region_id    TEXT NOT NULL REFERENCES regions (id),
    location_id  TEXT REFERENCES locations (id),
    shared       INTEGER NOT NULL DEFAULT 0 CHECK (shared IN (0, 1)),
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    summary      TEXT NOT NULL DEFAULT '',
    opened_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    closed_at    TEXT
);

CREATE TABLE scene_participants (
    scene_id      INTEGER NOT NULL REFERENCES scenes (id),
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    PRIMARY KEY (scene_id, character_id)
);

-- Beats. region_id is copied from the scene so one open beat per region can
-- be enforced by index.
CREATE TABLE beats (
    id           INTEGER PRIMARY KEY,
    scene_id     INTEGER NOT NULL REFERENCES scenes (id),
    region_id    TEXT NOT NULL REFERENCES regions (id),
    number       INTEGER NOT NULL CHECK (number >= 1),
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    narration    TEXT NOT NULL DEFAULT '',
    summary      TEXT NOT NULL DEFAULT '',
    opened_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved_at  TEXT,
    UNIQUE (scene_id, number)
);

CREATE UNIQUE INDEX beats_one_open_per_region ON beats (region_id) WHERE status = 'open';

CREATE TRIGGER beats_region_matches_scene BEFORE INSERT ON beats
WHEN NEW.region_id IS NOT (SELECT region_id FROM scenes WHERE id = NEW.scene_id)
BEGIN
    SELECT RAISE(ABORT, 'beat region must match its scene');
END;

-- One intent per present player per beat. Intent text is untrusted player
-- input, stored as data only. A player who doesn't act holds a stance.
CREATE TABLE beat_intents (
    beat_id       INTEGER NOT NULL REFERENCES beats (id),
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    intent        TEXT CHECK (intent IS NULL OR length(intent) <= 2000),
    hold_stance   TEXT CHECK (hold_stance IN ('guard', 'watch', 'withdraw')),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (beat_id, character_id),
    CHECK ((intent IS NULL) <> (hold_stance IS NULL))
);

-- The append-only event log. Every successful state write adds a row.
CREATE TABLE events (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL,
    actor         TEXT NOT NULL CHECK (actor IN ('dm', 'player', 'system')),
    player_id     INTEGER REFERENCES players (id),
    character_id  INTEGER REFERENCES characters (id),
    region_id     TEXT REFERENCES regions (id),
    scene_id      INTEGER REFERENCES scenes (id),
    payload       TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(payload)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX events_character ON events (character_id);
CREATE INDEX events_region ON events (region_id);

CREATE TRIGGER events_no_update BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'the event log is append-only');
END;

CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'the event log is append-only');
END;

-- Token usage for every API call, against the player and scene that caused it.
CREATE TABLE usage_ledger (
    id                  INTEGER PRIMARY KEY,
    player_id           INTEGER REFERENCES players (id),
    scene_id            INTEGER REFERENCES scenes (id),
    call_type           TEXT NOT NULL,
    model               TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens       INTEGER NOT NULL CHECK (output_tokens >= 0),
    cache_read_tokens   INTEGER NOT NULL DEFAULT 0 CHECK (cache_read_tokens >= 0),
    cache_write_tokens  INTEGER NOT NULL DEFAULT 0 CHECK (cache_write_tokens >= 0),
    cost_micro_usd      INTEGER NOT NULL CHECK (cost_micro_usd >= 0),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX usage_player_time ON usage_ledger (player_id, created_at);
CREATE INDEX usage_time ON usage_ledger (created_at);

CREATE TRIGGER usage_no_update BEFORE UPDATE ON usage_ledger
BEGIN
    SELECT RAISE(ABORT, 'the usage ledger is append-only');
END;

CREATE TRIGGER usage_no_delete BEFORE DELETE ON usage_ledger
BEGIN
    SELECT RAISE(ABORT, 'the usage ledger is append-only');
END;
