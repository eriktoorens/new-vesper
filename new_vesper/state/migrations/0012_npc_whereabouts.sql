-- 0012: where each NPC is (D111). An NPC is in one place at a time; the schedule
-- in content is their agenda, not where the clock puts them.

-- One row per NPC (ids come from content, as in npc_goals). location_id NULL means
-- away from the district. since marks when they arrived or took up the activity.
CREATE TABLE npc_whereabouts (
    npc_id       TEXT PRIMARY KEY,
    location_id  TEXT REFERENCES locations (id),
    activity     TEXT NOT NULL CHECK (length(activity) BETWEEN 1 AND 200),
    since        TEXT NOT NULL
);
