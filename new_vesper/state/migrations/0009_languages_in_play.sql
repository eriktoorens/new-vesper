-- 0009: languages in play (D76-D81).

-- The language a character speaks aloud (D80). NULL means Registry Standard.
ALTER TABLE characters ADD COLUMN speaking TEXT REFERENCES languages (id);

-- A gist roll names the language it tries to follow (D78), and a roll remembers
-- which consequence it paid, since a 7-9 gist roll's cost decides what is heard.
ALTER TABLE rolls ADD COLUMN language_id TEXT REFERENCES languages (id);
ALTER TABLE rolls ADD COLUMN consequence_type TEXT;

DROP TRIGGER rolls_use_once;
CREATE TRIGGER rolls_use_once BEFORE UPDATE ON rolls
WHEN NOT (
    NEW.id = OLD.id AND NEW.character_id = OLD.character_id AND NEW.scene_id = OLD.scene_id
    AND NEW.total = OLD.total AND NEW.tier = OLD.tier AND NEW.magic = OLD.magic
    AND NEW.die_1 = OLD.die_1 AND NEW.die_2 = OLD.die_2
    AND NEW.consequence_used >= OLD.consequence_used AND NEW.loot_used >= OLD.loot_used
    AND NEW.language_id IS OLD.language_id
    AND (OLD.consequence_type IS NULL OR NEW.consequence_type IS OLD.consequence_type)
)
BEGIN
    SELECT RAISE(ABORT, 'a roll is fixed once made; it can only be used up');
END;

-- Every line someone other than the player character spoke (D81): what was said,
-- in what language, and what the listening character understood of it.
CREATE TABLE speech_lines (
    id            INTEGER PRIMARY KEY,
    scene_id      INTEGER NOT NULL REFERENCES scenes (id),
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    speaker       TEXT NOT NULL CHECK (length(speaker) BETWEEN 1 AND 80),
    npc_id        TEXT,
    language_id   TEXT REFERENCES languages (id),
    words         TEXT NOT NULL CHECK (length(words) BETWEEN 1 AND 600),
    tone          TEXT CHECK (tone IS NULL OR length(tone) <= 80),
    gist          TEXT CHECK (gist IS NULL OR length(gist) <= 200),
    heard         TEXT NOT NULL CHECK (heard IN ('fluent', 'gist', 'tone', 'none')),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX speech_lines_scene ON speech_lines (scene_id, id);

CREATE TRIGGER speech_lines_append_only BEFORE UPDATE ON speech_lines
BEGIN
    SELECT RAISE(ABORT, 'speech lines are append-only');
END;
