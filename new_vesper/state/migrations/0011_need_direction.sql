-- 0011: which way a need's accrued time counts (D85).

-- Cold and heat climb when exposed and ease when not. Time toward the next step
-- in one direction must not carry over into the other: easing marks time
-- counted toward easing a step rather than climbing one.
ALTER TABLE character_needs ADD COLUMN easing INTEGER NOT NULL DEFAULT 0 CHECK (easing IN (0, 1));
