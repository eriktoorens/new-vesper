-- 0010: bodily needs (D83-D89): hunger, thirst, tiredness, cold and heat.

-- One row per character and need. Time is counted only while the character is
-- online: updated_at marks the last moment counted (D85, D88).
CREATE TABLE character_needs (
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    need          TEXT NOT NULL CHECK (need IN ('hunger', 'thirst', 'tired', 'cold', 'heat')),
    level         INTEGER NOT NULL DEFAULT 0 CHECK (level BETWEEN 0 AND 3),
    accrued       INTEGER NOT NULL DEFAULT 0 CHECK (accrued >= 0),
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (character_id, need)
);
