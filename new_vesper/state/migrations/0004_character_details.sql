-- 0004: character details (D37): age, appearance and the languages a character speaks.

-- Languages are defined in content and seeded here, so characters can reference them.
CREATE TABLE languages (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    common  INTEGER NOT NULL CHECK (common IN (0, 1))
);

ALTER TABLE characters ADD COLUMN age TEXT CHECK (age IS NULL OR length(age) BETWEEN 1 AND 60);
ALTER TABLE characters ADD COLUMN appearance TEXT
    CHECK (appearance IS NULL OR length(appearance) BETWEEN 1 AND 300);

CREATE TABLE character_languages (
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    language_id   TEXT NOT NULL REFERENCES languages (id),
    PRIMARY KEY (character_id, language_id)
);
