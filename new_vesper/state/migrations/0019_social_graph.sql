-- 0019: the social graph (D127-D130, D141-D144). Alliances between two NPCs' wants,
-- who knows the other's part in a tension or alliance, grudges, and amends.

-- Two NPCs' wants that pull together, like a tension in reverse (D130, D141).
CREATE TABLE npc_want_alliances (
    id        INTEGER PRIMARY KEY,
    want_a    INTEGER NOT NULL REFERENCES npc_wants (id),
    want_b    INTEGER NOT NULL REFERENCES npc_wants (id),
    note      TEXT NOT NULL CHECK (length(note) BETWEEN 1 AND 160),
    scene_id  INTEGER REFERENCES scenes (id),
    CHECK (want_a < want_b),
    UNIQUE (want_a, want_b)
);

-- An NPC who knows the other party's part in a tension or alliance (D128, D141).
CREATE TABLE npc_bond_knows (
    id        INTEGER PRIMARY KEY,
    kind      TEXT NOT NULL CHECK (kind IN ('tension', 'alliance')),
    want_a    INTEGER NOT NULL REFERENCES npc_wants (id),
    want_b    INTEGER NOT NULL REFERENCES npc_wants (id),
    npc_id    TEXT NOT NULL,
    how       TEXT NOT NULL CHECK (length(how) BETWEEN 1 AND 160),
    scene_id  INTEGER REFERENCES scenes (id),
    CHECK (want_a < want_b),
    UNIQUE (kind, want_a, want_b, npc_id)
);

-- A grudge one NPC holds against another (D129, D143): the steps it dropped on each
-- axis, whether it was a betrayal, and how it ended. One standing grudge per pair.
CREATE TABLE npc_grudges (
    id                 INTEGER PRIMARY KEY,
    holder_npc         TEXT NOT NULL,
    target_npc         TEXT NOT NULL,
    trust_steps        INTEGER NOT NULL DEFAULT 0 CHECK (trust_steps >= 0),
    fondness_steps     INTEGER NOT NULL DEFAULT 0 CHECK (fondness_steps >= 0),
    betrayal           INTEGER NOT NULL DEFAULT 0 CHECK (betrayal IN (0, 1)),
    reason             TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 300),
    status             TEXT NOT NULL DEFAULT 'held'
                       CHECK (status IN ('held', 'on_condition', 'faded', 'amended')),
    renewed_at         TEXT NOT NULL,
    condition_want_id  INTEGER REFERENCES npc_wants (id),
    refused_until      TEXT,
    scene_id           INTEGER REFERENCES scenes (id),
    ended_scene_id     INTEGER REFERENCES scenes (id),
    CHECK (holder_npc <> target_npc),
    CHECK (trust_steps + fondness_steps >= 1)
);
CREATE UNIQUE INDEX npc_grudges_standing ON npc_grudges (holder_npc, target_npc)
    WHERE status IN ('held', 'on_condition');

-- Every amends roll between NPCs (D142), at most one per pair per scene.
CREATE TABLE npc_amends (
    id          INTEGER PRIMARY KEY,
    grudge_id   INTEGER NOT NULL REFERENCES npc_grudges (id),
    offer       TEXT NOT NULL CHECK (length(offer) BETWEEN 1 AND 160),
    condition   TEXT NOT NULL CHECK (length(condition) BETWEEN 1 AND 160),
    die_one     INTEGER NOT NULL CHECK (die_one BETWEEN 1 AND 6),
    die_two     INTEGER NOT NULL CHECK (die_two BETWEEN 1 AND 6),
    fondness    INTEGER NOT NULL CHECK (fondness BETWEEN -3 AND 3),
    total       INTEGER NOT NULL,
    outcome     TEXT NOT NULL CHECK (outcome IN ('accepted', 'on_condition', 'refused')),
    scene_id    INTEGER REFERENCES scenes (id),
    UNIQUE (grudge_id, scene_id)
);
