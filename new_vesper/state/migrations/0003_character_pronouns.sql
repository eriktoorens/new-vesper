-- 0003: player characters' pronouns, so narration never has to guess.
ALTER TABLE characters ADD COLUMN pronouns TEXT CHECK (pronouns IS NULL OR length(pronouns) BETWEEN 1 AND 30);
