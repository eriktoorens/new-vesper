-- 0002: rolls (D1), threat clocks (D6) and per-character tags (D15).

-- Every roll code makes. A roll can back at most one consequence and one
-- loot grant; both flags only ever go from 0 to 1.
CREATE TABLE rolls (
    id                INTEGER PRIMARY KEY,
    character_id      INTEGER NOT NULL REFERENCES characters (id),
    scene_id          INTEGER NOT NULL REFERENCES scenes (id),
    stat              TEXT NOT NULL CHECK (stat IN ('steel', 'slick', 'wire', 'weird', 'heart')),
    difficulty        TEXT NOT NULL
                      CHECK (difficulty IN ('routine', 'risky', 'hard', 'desperate')),
    knack_id          TEXT REFERENCES knacks (id),
    magic             INTEGER NOT NULL CHECK (magic IN (0, 1)),
    stakes            TEXT NOT NULL,
    die_1             INTEGER NOT NULL CHECK (die_1 BETWEEN 1 AND 6),
    die_2             INTEGER NOT NULL CHECK (die_2 BETWEEN 1 AND 6),
    stat_value        INTEGER NOT NULL,
    modifier          INTEGER NOT NULL,
    bonus             INTEGER NOT NULL CHECK (bonus BETWEEN 0 AND 1),
    total             INTEGER NOT NULL,
    tier              TEXT NOT NULL CHECK (tier IN ('clean', 'cost', 'city_moves')),
    consequence_used  INTEGER NOT NULL DEFAULT 0 CHECK (consequence_used IN (0, 1)),
    loot_used         INTEGER NOT NULL DEFAULT 0 CHECK (loot_used IN (0, 1)),
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (total = die_1 + die_2 + stat_value + modifier + bonus)
);

CREATE INDEX rolls_character_knack ON rolls (character_id, knack_id, created_at);

CREATE TRIGGER rolls_no_delete BEFORE DELETE ON rolls
BEGIN
    SELECT RAISE(ABORT, 'rolls cannot be deleted');
END;

CREATE TRIGGER rolls_use_once BEFORE UPDATE ON rolls
WHEN NOT (
    NEW.id = OLD.id AND NEW.character_id = OLD.character_id AND NEW.scene_id = OLD.scene_id
    AND NEW.total = OLD.total AND NEW.tier = OLD.tier AND NEW.magic = OLD.magic
    AND NEW.die_1 = OLD.die_1 AND NEW.die_2 = OLD.die_2
    AND NEW.consequence_used >= OLD.consequence_used AND NEW.loot_used >= OLD.loot_used
)
BEGIN
    SELECT RAISE(ABORT, 'a roll is fixed once made; it can only be used up');
END;

-- Threat clocks: defined in content per district; the DM advances, never creates.
CREATE TABLE threat_clocks (
    id         TEXT PRIMARY KEY,
    region_id  TEXT NOT NULL REFERENCES regions (id),
    name       TEXT NOT NULL,
    segments   INTEGER NOT NULL CHECK (segments BETWEEN 1 AND 12),
    filled     INTEGER NOT NULL DEFAULT 0,
    CHECK (filled BETWEEN 0 AND segments)
);

-- Tags a character gains in play (e.g. half-faded after slipping), on top of
-- the tags their origin gives them.
CREATE TABLE character_tags (
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    tag           TEXT NOT NULL,
    PRIMARY KEY (character_id, tag)
);
