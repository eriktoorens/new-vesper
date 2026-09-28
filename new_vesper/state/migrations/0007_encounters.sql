-- 0007: the encounter log (D67-D71). Used for the district cooldown and the record.
CREATE TABLE encounters (
    id            INTEGER PRIMARY KEY,
    encounter_id  TEXT NOT NULL,
    region_id     TEXT NOT NULL REFERENCES regions (id),
    location_id   TEXT REFERENCES locations (id),
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    scene_id      INTEGER REFERENCES scenes (id),
    kind          TEXT NOT NULL CHECK (kind IN ('color', 'opportunity', 'trouble')),
    stranger      TEXT CHECK (stranger IS NULL OR json_valid(stranger)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX encounters_region_time ON encounters (region_id, created_at);
