-- 0014: NPC moods (D119) and what each NPC wants in a scene (D120).

-- An NPC's mood through a city day: code rolls the first, and the Narrator may
-- shift it within a scene. The latest row for the day is the mood now.
CREATE TABLE npc_moods (
    id          INTEGER PRIMARY KEY,
    npc_id      TEXT NOT NULL,
    city_day    TEXT NOT NULL,
    mood        TEXT NOT NULL CHECK (length(mood) BETWEEN 1 AND 60),
    source      TEXT NOT NULL CHECK (source IN ('rolled', 'narrator')),
    reason      TEXT CHECK (reason IS NULL OR length(reason) <= 300),
    scene_id    INTEGER REFERENCES scenes (id),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX npc_moods_by_day ON npc_moods (npc_id, city_day);

-- What an NPC wants right now, in one scene: set by the Narrator, changed at most once.
CREATE TABLE scene_wants (
    scene_id  INTEGER NOT NULL REFERENCES scenes (id),
    npc_id    TEXT NOT NULL,
    want      TEXT NOT NULL CHECK (length(want) BETWEEN 1 AND 160),
    reason    TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 300),
    changes   INTEGER NOT NULL DEFAULT 0 CHECK (changes BETWEEN 0 AND 1),
    PRIMARY KEY (scene_id, npc_id)
);
