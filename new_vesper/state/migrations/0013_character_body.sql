-- 0013: a character's body (D116): how they're built and how they move, in a line,
-- in the player's words. Narrative only; it changes no rules.
ALTER TABLE characters ADD COLUMN body TEXT CHECK (body IS NULL OR length(body) BETWEEN 1 AND 200);
