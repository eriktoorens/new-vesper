-- 0005: weather as it happened (D51), the daily city tick (D55) and NPC goal progress.

-- One row per district per 3-hour block, written as the block is first seen, so
-- every player shares the same sky. block_start is a UTC timestamp.
CREATE TABLE weather (
    region_id    TEXT NOT NULL REFERENCES regions (id),
    block_start  TEXT NOT NULL,
    weather_id   TEXT NOT NULL,
    PRIMARY KEY (region_id, block_start)
);

-- City days the daily tick has run for (city date, YYYY-MM-DD).
CREATE TABLE city_ticks (
    city_day  TEXT PRIMARY KEY,
    ran_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- How far each NPC has come along their goal. Stage 0 is before the first step.
CREATE TABLE npc_goals (
    npc_id      TEXT PRIMARY KEY,
    stage       INTEGER NOT NULL DEFAULT 0 CHECK (stage >= 0),
    days_since  INTEGER NOT NULL DEFAULT 0 CHECK (days_since >= 0)
);
