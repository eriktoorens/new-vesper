-- 0017: what each NPC wants now, and wants in tension (D124, D126). Replaces D122.

-- An NPC's current wants: one set per NPC, shared by every player. Each changes
-- only for a reason from a scene, and ends as met or dropped (the row stays).
CREATE TABLE npc_wants (
    id              INTEGER PRIMARY KEY,
    npc_id          TEXT NOT NULL,
    want            TEXT NOT NULL CHECK (length(want) BETWEEN 1 AND 160),
    about           TEXT CHECK (about IS NULL OR length(about) BETWEEN 1 AND 80),
    reason          TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 300),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'met', 'dropped')),
    ended_reason    TEXT CHECK (ended_reason IS NULL OR length(ended_reason) <= 300),
    scene_id        INTEGER REFERENCES scenes (id),
    ended_scene_id  INTEGER REFERENCES scenes (id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX npc_wants_by_npc ON npc_wants (npc_id, status);

-- Two wants that pull against each other: one NPC's own, or two NPCs'.
CREATE TABLE npc_want_tensions (
    id        INTEGER PRIMARY KEY,
    want_a    INTEGER NOT NULL REFERENCES npc_wants (id),
    want_b    INTEGER NOT NULL REFERENCES npc_wants (id),
    note      TEXT NOT NULL CHECK (length(note) BETWEEN 1 AND 160),
    scene_id  INTEGER REFERENCES scenes (id),
    CHECK (want_a < want_b),
    UNIQUE (want_a, want_b)
);
