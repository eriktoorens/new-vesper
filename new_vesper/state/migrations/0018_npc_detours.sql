-- 0018: an NPC off their agenda because they want to be (D133). Until detour_until
-- they stay where a want took them; then they rejoin their day.
ALTER TABLE npc_whereabouts ADD COLUMN detour_until TEXT;
