-- 0008: the DM writes encounters (D73); code holds each district's daily pool (D72, D74).

-- One row per encounter a district's city day holds. Spent when the DM uses it.
CREATE TABLE encounter_pool (
    region_id     TEXT NOT NULL REFERENCES regions (id),
    city_day      TEXT NOT NULL,
    slot          INTEGER NOT NULL CHECK (slot >= 0),
    kind          TEXT NOT NULL CHECK (kind IN ('color', 'opportunity', 'trouble')),
    underside     INTEGER NOT NULL DEFAULT 0 CHECK (underside IN (0, 1)),
    encounter_id  INTEGER REFERENCES encounters (id),
    PRIMARY KEY (region_id, city_day, slot)
);

-- What the DM wrote, so later encounters can avoid repeating it.
ALTER TABLE encounters ADD COLUMN text TEXT CHECK (text IS NULL OR length(text) <= 300);
ALTER TABLE encounters ADD COLUMN underside INTEGER NOT NULL DEFAULT 0
    CHECK (underside IN (0, 1));
