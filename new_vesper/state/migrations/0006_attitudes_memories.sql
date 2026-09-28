-- 0006: NPC attitudes (D60-D61, D65), the reasons they changed, and NPC memories (D63).

-- How an NPC feels about a character or another NPC. NPC ids come from content.
CREATE TABLE attitudes (
    holder_npc   TEXT NOT NULL,
    target_kind  TEXT NOT NULL CHECK (target_kind IN ('character', 'npc')),
    target_id    TEXT NOT NULL,
    trust        INTEGER NOT NULL DEFAULT 0 CHECK (trust BETWEEN -3 AND 3),
    fondness     INTEGER NOT NULL DEFAULT 0 CHECK (fondness BETWEEN -3 AND 3),
    fear         INTEGER NOT NULL DEFAULT 0 CHECK (fear BETWEEN -3 AND 3),
    PRIMARY KEY (holder_npc, target_kind, target_id),
    CHECK (NOT (target_kind = 'npc' AND target_id = holder_npc))
);

-- Every change, with its reason, so an NPC can always say why. Append-only.
CREATE TABLE attitude_changes (
    id           INTEGER PRIMARY KEY,
    holder_npc   TEXT NOT NULL,
    target_kind  TEXT NOT NULL CHECK (target_kind IN ('character', 'npc')),
    target_id    TEXT NOT NULL,
    axis         TEXT NOT NULL CHECK (axis IN ('trust', 'fondness', 'fear')),
    before       INTEGER NOT NULL CHECK (before BETWEEN -3 AND 3),
    after        INTEGER NOT NULL CHECK (after BETWEEN -3 AND 3),
    reason       TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 300),
    scene_id     INTEGER REFERENCES scenes (id),
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (abs(after - before) = 1)
);

CREATE INDEX attitude_changes_pair ON attitude_changes (holder_npc, target_kind, target_id);

CREATE TRIGGER attitude_changes_no_update BEFORE UPDATE ON attitude_changes
BEGIN
    SELECT RAISE(ABORT, 'attitude changes are append-only');
END;

CREATE TRIGGER attitude_changes_no_delete BEFORE DELETE ON attitude_changes
BEGIN
    SELECT RAISE(ABORT, 'attitude changes are append-only');
END;

-- What an NPC remembers of a character: one line per scene, written when it closes.
CREATE TABLE npc_memories (
    id            INTEGER PRIMARY KEY,
    npc_id        TEXT NOT NULL,
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    scene_id      INTEGER REFERENCES scenes (id),
    note          TEXT NOT NULL CHECK (length(note) BETWEEN 1 AND 300),
    folded        INTEGER NOT NULL DEFAULT 0 CHECK (folded IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX npc_memories_pair ON npc_memories (npc_id, character_id, id);

-- Older memories folded into one line per NPC and character.
CREATE TABLE npc_memory_summaries (
    npc_id        TEXT NOT NULL,
    character_id  INTEGER NOT NULL REFERENCES characters (id),
    summary       TEXT NOT NULL CHECK (length(summary) BETWEEN 1 AND 600),
    PRIMARY KEY (npc_id, character_id)
);
