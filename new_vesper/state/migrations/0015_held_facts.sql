-- 0015: what an NPC knows about a character (D121), as the first slice of D106's
-- belief field: a holder, a subject, a claim, and how the holder came by it.
-- For now holders are NPCs and subjects are characters; the kinds leave room.

CREATE TABLE held_facts (
    id           INTEGER PRIMARY KEY,
    holder_kind  TEXT NOT NULL CHECK (holder_kind IN ('npc')),
    holder_id    TEXT NOT NULL,
    about_kind   TEXT NOT NULL CHECK (about_kind IN ('character')),
    about_id     TEXT NOT NULL,
    fact         TEXT NOT NULL CHECK (length(fact) BETWEEN 1 AND 160),
    learned      TEXT NOT NULL CHECK (learned IN ('heard', 'saw')),
    scene_id     INTEGER REFERENCES scenes (id),
    folded       INTEGER NOT NULL DEFAULT 0 CHECK (folded IN (0, 1)),
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX held_facts_by_pair ON held_facts (holder_kind, holder_id, about_kind, about_id);

-- Older facts folded into one line once there are too many to show.
CREATE TABLE held_fact_summaries (
    holder_kind  TEXT NOT NULL,
    holder_id    TEXT NOT NULL,
    about_kind   TEXT NOT NULL,
    about_id     TEXT NOT NULL,
    summary      TEXT NOT NULL CHECK (length(summary) BETWEEN 1 AND 600),
    PRIMARY KEY (holder_kind, holder_id, about_kind, about_id)
);
