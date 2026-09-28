# New Vesper — Setting & Rules

Exported from the living design doc on 2026-09-27. The living doc is where design discussion happens; update this file when it changes.

**Decisions D1–D89** (2026-09-27 and 2026-09-28) were made in this repository after the export and are not yet in the living doc. Each is tagged where it applies and listed in the [Decision log](#decision-log). Copy them back to the living doc before the next export.

## Overview

New Vesper is a persistent, shared, text-based RPG where an AI dungeon master runs a rain-soaked megacity in which magic and technology both run on the same fuel: attention. Belief makes things real; being forgotten unmakes them.

- **Format:** persistent shared world, many players, asynchronous play.
- **DM:** a Claude API agent that narrates and adjudicates; code owns all game state.
- **Tone:** grimbright. The world is cruel but not nihilistic. Effort counts, kindness matters, and small victories stay on the page.
- **Inspirations:** Blade Runner (rain, noir, made people), Shadowrun (magic meets corporate tech), The Diamond Age (nanotech enclaves, primers), American Gods (gods fed by belief), Neverwhere (a hidden city of the forgotten), and a splash of Discworld for bureaucratic absurdity.

The core conceit: every power in the city, a corporate god, a spell, a network, a neighborhood, exists only as long as enough people pay attention to it.

## The City

New Vesper is built on top of Old Vesper, a city that was forgotten and is still down there, half-faded. The name you use tells people who you are.

| Name | Who says it | What it means |
| --- | --- | --- |
| New Vesper | Corporations, officials, paperwork | The city above: towers, neon, corporate gods |
| Vesper, "the Vesp" | Locals (the second one when rude) | Home, for better or worse |
| Old Vesper | Anyone who has been below | The Underside: the forgotten city beneath |

**New Vesper** is vertical and wet. Arcologies and brand-temples rise above the cloud line. Street level is markets, noodle stalls, shrines bolted to vending machines, and drones that sell prayers by subscription.

**Old Vesper** is the Underside. Drowned streets, a floating night market, speaking rats, and doors that open only for people who don't exist. The deeper you go, the less real things become: maps stop agreeing, names slip, and the gods down there are thin enough to see through.

**The Market District** is the first playable district: part souk, part Asian night market. Covered lanes of lantern-lit stalls, spice smoke, haggling in a dozen languages, food carts under tarps, and shrine-stalls where you can make an offering to whichever god fits your budget. Stallholders sell noodles, charms, bootleg firmware and secondhand miracles side by side. Its Underside entrance is a drowned subway station beneath the oldest bazaar hall.

**Cultural range:** New Vesper draws on many cultures, not a western default: markets, cuisines, languages, architecture and folk traditions from around the world sit side by side. Its gods are invented for the setting, inspired by many traditions, never lifted from living religions.

## The Fade and Light

The dark in New Vesper is the Fade: whatever nobody remembers stops being real. Streets vanish from maps, then from the world. People go unseen. Old Vesper is what a fully faded city looks like, and New Vesper is heading the same way.

**Light** is tracked per region as a number the code owns. It measures how real, remembered and believed-in a place is.

- **High Light:** stable streets, working doors, NPCs who remember your name.
- **Low Light:** shifting geography, forgetful NPCs, stronger Underside bleed-through, dangerous encounters.
- **Zero Light:** the region falls into Old Vesper.

Players raise Light by making things matter: finding and honoring a forgotten god, telling a true story that spreads, restoring a shrine, keeping a district's people seen. Neglect and certain factions lower it. Because the world is shared, one player's deeds keep a place real for everyone.

**Central mystery:** did someone choose to forget Old Vesper, and who profits from forgetting now?

## Factions and Powers

Every faction wants attention, because attention is power. Names below are placeholders.

| Faction | What they are | What they want |
| --- | --- | --- |
| Corporate gods | Deities born from brand loyalty and subscription. Powerful, polished, hungry. | More believers; control of what the city remembers |
| Old gods | Pre-corporate deities living on dwindling offerings, some half-faded | Survival, remembrance, sometimes revenge |
| The enclaves | Nanotech communities that shape citizens through primers, ritual and code | Their own cohesion; a seat at the table |
| Underside folk | The forgotten and unseen, running the floating market in Old Vesper | To be left alone, or to be remembered again |
| The Registry | City bureaucracy that licenses miracles, permits resurrections and audits belief | Paperwork filed correctly, by everyone, including gods |

**Levity:** the Registry and the Guild of Minor Deities carry the Discworld thread. There is a god of lost umbrellas with a pending grievance, a resurrection permit with a nine-week backlog, and a union dispute over who counts as a patron saint. The humor sits on top of real stakes and never cancels them.

## Core Rules

Every risky action resolves as 2d6 + a stat + a difficulty modifier, rolled by code, with three outcome tiers.

**Stats** (start at −1 to +2; raise by leveling to a cap of +3):

| Stat | Covers |
| --- | --- |
| Steel | Violence, endurance, chrome |
| Slick | Stealth, grace, lies |
| Wire | Tech, hacking, the network |
| Weird | Magic, spirits, bargains with gods |
| Heart | Connection, conviction, being remembered |

**Difficulty ladder:** Routine +1 · Risky +0 · Hard −1 · Desperate −2. The DM chooses a rung; it never invents a number.

**Outcome tiers:**

| Total | Tier | What happens |
| --- | --- | --- |
| 10+ | Clean success | You get what you wanted |
| 7–9 | Success with a cost | You get it, but lose something: supplies, time, trust, or a bit of Light |
| 6 or less | The city moves | The DM makes a move against you from the allowed list |

No roll when there is no risk. The DM calls for a roll only when failure would be interesting.

**Rolls gate consequences (D1).** Each roll gets a single-use roll id. A consequence must cite one, and the tier limits what it can be:

| Tier | Allowed consequence |
| --- | --- |
| 10+ | None |
| 7–9 | One cost from the cost list, at most 1 box of Harm or Fade |
| 6 or less | One move from the allowed list, within its magnitude cap |

Without a roll there is no state change, except rewards reported through `report_trigger`.

**Costs on 7–9 (D2):** take one item; 1 Harm; 1 Fade; region Light −1; or a narrative-only cost that writes no state. Magic has its own cost list (see Magic).

**Why the cap is +3:** 2d6 is a bell curve, so each point shifts the odds a lot. Past +3, rolls stop being interesting. One stat can reach +4 through a level-10 advanced knack.

| Stat | 10+ (clean) | 6 or less (city moves) |
| --- | --- | --- |
| +0 | 17% | 42% |
| +1 | 28% | 28% |
| +2 | 42% | 17% |
| +3 | 58% | 8% |
| +4 | 72% | 3% |

**Allowed moves on 6 or less.** The DM picks one; code caps its size.

- Deal harm
- Add Fade
- Take something
- Separate them
- Reveal an unwelcome truth
- Advance a threat clock
- A faction takes notice
- The dark encroaches (region Light −1)

**Take something (D28):** the item leaves play; the event log records who lost what and why.

**Magnitudes (D6):** Deal harm and Add Fade are 1–3 boxes. The dark encroaches is exactly −1 Light. Every other move is magnitude 1. Threat clocks have 4 segments and are defined in content, per district; the DM can advance a clock by 1 but never creates one.

## Characters

There are no classes. A character is an Origin, five stats, a few Knacks and a Bond, and grows by leveling.

**Origin** replaces race and class. It is narrative, with one trait and a few tags that code enforces.

| Origin | Example trait | Example tags |
| --- | --- | --- |
| Street-born human | Knows someone in every market | streetwise |
| Made person | Built, not born; hard to hurt, easy to doubt | synthetic |
| Enclave-raised | Primer-educated, speaks in protocols | networked |
| Underside-born | Sees things others have forgotten | half-faded |
| Awakened animal | Speaks with its own kind; nobody suspects a cat | no hands, overlooked, animal-speech |

Tags constrain the DM: an awakened cat cannot pick a lock, but walks where nobody asks questions.

**Tags code enforces (D7):** for now only `no-hands`, which blocks knacks tagged `needs-hands`. The other tags guide narration through the prompt until playtest shows a need to enforce them.

**Creation:** assign the array +2, +1, +1, 0, −1 to the five stats; pick an origin; pick two knacks; name one Bond, a person your character matters to.

**Who chooses (D17):** the player makes every creation and leveling choice through CLI menus. The DM never picks stats, knacks or level choices.

**Currency (D18):** decimal coin: 1 glamour = 10 glims = 100 glitter. Glitter is small change, glims are everyday money, glamour is a big deal. Code stores every amount as a whole number of glitter and only displays denominations. New characters start with 5 glims (50 glitter). Currency is earned through loot table entries or specific NPC deals, never invented by the DM.

**Knacks** are the open catalog of things a character does well. Anyone can take any knack the fiction supports; a rat hacker is fine if you can say how.

**Leveling up.** Reaching level N+1 costs 5 + N XP, earned from the advancement triggers. Each level, pick one:

- A new knack
- +1 to a stat (cap +3)
- Heal a scar

Every fifth level also unlocks an **advanced knack** or an **origin evolution**, such as a plaza pigeon becoming the plaza's minor god.

**The +4 stat (D14):** from level 10, a milestone advanced knack may name one stat. That stat's cap becomes +4, and later +1 stat choices can raise it there. Only one stat per character, ever.

**Player-proposed knacks:**

1. The player describes the knack in plain words.
2. A separate DM call, outside any scene, drafts it in a fixed template: trigger, stat, 10+ effect, 7–9 effect, limits, tags.
3. Code checks it against a balance budget: at most +1 to a roll, effects from the allowed list, a use limit per scene or per day for strong effects.
4. The player accepts or revises. Approved knacks join the shared catalog, with human admin approval until the pipeline is trusted.

## Harm, Fade and Advancement

Characters carry two tracks. Dice never kill a character outright; death is always a choice.

Both tracks have 6 boxes. A bad hit deals 1–3, so a track fills after 2–4 serious mistakes, and each threshold is easy to narrate. Veterans get tougher through armor knacks and advancement, not longer tracks.

| Boxes | Harm | Fade |
| --- | --- | --- |
| 1–2 | Bruised | Unnoticed (2) |
| 3–4 | Wounded: −1 to Steel and Slick | Unseen (4): NPCs forget you between scenes |
| 5–6 | Critical: −2 to Steel and Slick; at 6, Fall or Endure | Slipping (6): into Old Vesper |

**Bands (D11, D12):** each status covers its whole row: Unnoticed is 1–2 Fade, Unseen 3–4, Slipping 5–6. Harm penalties to Steel and Slick are −1 while Wounded (3–4) and −2 while Critical (5–6), so the lowest possible roll stat is −3.

**Harm** (flesh and chrome) fills from violence, accidents and backlash. Treatment, rest and repair clear it. When Harm fills, the player chooses:

- **Fall:** die performing a final act that permanently changes the world (a sealed door, a saved block, a named memorial in code).
- **Endure:** survive with a permanent scar or condition, written to the character sheet. Harm then drops to 4: still Wounded (D13).

**Fade** fills from isolation, horror and broken promises. As it rises, the world forgets you: shopkeepers lose your face, cameras stop tracking you, doors stop opening. Low Fade can help a thief; high Fade is dangerous.

- **Recovery:** being seen. Time with other players at a shared place, keeping your word, someone speaking your name.
- **At maximum:** the character slips into Old Vesper and becomes an Underside character. Changed, not dead.
- **In the prototype (D15):** a slipped character moves to the district's Underside entrance (the Drowned Station), gains the `half-faded` tag and keeps playing. Full Old Vesper play comes later.

**Recovery amounts (D8):**

- Logging off at a haven clears 1 Harm and 1 Fade per real day offline.
- A treatment knack clears 1 Harm per use, on a 7 or better, from the character who rolled. Healing someone else comes with multiplayer (D30).
- Another player speaking your character's name clears 1 Fade, once per scene.

**Advancement:** experience comes from a fixed list of triggers that code checks: protecting someone, making a sacrifice, keeping a hard promise, raising a region's Light. Killing things earns nothing on its own. See Characters for what XP buys. The DM can report that a trigger happened; code decides whether it pays out.

**Triggers and payouts (D4):** exactly four triggers: `protect_someone`, `make_a_sacrifice`, `keep_a_hard_promise`, `raise_light`. Each pays 1 XP, at most once per character per scene.

## Magic

Magic is bargaining with attention. There are no spell slots and no mana; every working costs something the world remembers.

- **Rolls:** casting is a Weird roll. Tech-magic, such as hacking a god's prayer network, can use Wire, through a knack tagged tech-magic (D31). Raw magic without a knack uses Weird.
- **Knacks** define what a character can do reliably, such as asking a shrine's god one question. Anyone can attempt raw magic without a knack, at Desperate difficulty.
- **Costs on 7–9** come from a magic list: a tick of Fade, a side effect, or a favor owed to a god.
- **The favor ledger:** code records every favor owed. Gods collect, and debts become story hooks. This is the Tally made mechanical.
- **Who is owed (D10, provisional):** the god of the shrine the character is at, or the god whose power they are tapping. If neither applies, a 7–9 cost must be Fade or a side effect, not a favor. **High priority to revisit:** the player should understand, and have some choice over, where a debt accrues. Candidate alternatives: the district's patron god as a fallback, or an unnamed creditor ("something that noticed") named later as a story hook.

## DM Authority

The AI decides what is being attempted and how the story reads; code decides what actually happens to the world.

One turn runs as a loop:

1. **Player acts:** types an intent.
2. **DM agent** picks the stat and difficulty, and calls `call_for_roll`.
3. **Rules engine** (code) rolls 2d6 and returns the tier.
4. **DM agent** narrates the result and picks a move, calling `apply_consequence`.
5. **State layer** (code) validates the request and writes state.
6. **Player sees** the changed world.

Every state change goes through a tool, and every tool checks the request against the rules before writing.

**Narration (D33):** the DM narrates in third person, present tense, using the character's name and the pronouns on their sheet. Player characters choose pronouns at creation.

**Player input (D34):** plain text is what the character does, in any grammatical person; text in quotation marks is what the character says, word for word. The DM never rewrites, paraphrases or adds to a player character's words, actions, thoughts or feelings; it narrates the world's response.

**Questions to the DM (D35):** `/ask` puts an out-of-character question to the DM. It may only look: no roll, no state change, no time passing, no beat. The DM answers with only what the character can see, hear or reasonably know.

**Owed consequences (D36):** a roll at 7–9 or 6 or less must get its consequence. If the DM tries to end a turn with one still owed, code sends it back to apply it (up to twice).

**Movement (D27):** the player moves with the `/go <place>` command; code checks the place is real and in the same district, closes the scene and opens one there. The DM never moves characters, since that would be a state change without a roll. When a player says they head somewhere, the DM narrates setting off and points to `/go`.

**Who a roll's consequences land on (D26):** Harm and Fade from a roll land only on the character who rolled. Harming another player's character needs an opposed roll, which comes with multiplayer; until then there is no PvP state change at all.

| The DM decides | Code owns |
| --- | --- |
| Whether a roll is needed | The dice |
| Which stat applies | Harm, Fade, stats, inventory |
| Which difficulty rung | Currency, loot tables, XP triggers |
| Which move to make on 6 or less, from the allowed list | Region Light levels |
| Narration, NPC voices, scene description | What exists: items, NPCs, places |

**Initial tool contract:**

- `call_for_roll(stat, difficulty, stakes, knack?, magic?)` returns the total, the tier and a single-use roll id (D1). `knack` names a knack the character holds, so code can apply its bonus, use limit and tags; `magic` marks a casting. A knack tagged magic makes the roll magic (D25).
- `apply_consequence(roll_id, type, target, magnitude)` checks the roll's tier, the allowed list and the magnitude cap, then writes state (D1, D2).
- `grant_from_table(roll_id, table_id)` hands out loot from a table; the DM never invents items. It needs a successful roll (7+), and each roll grants loot at most once (D24).
- `report_trigger(trigger_id, evidence)` flags an XP trigger; code decides the payout.
- `adjust_light(region, direction, size, reason)` moves a region's Light: `direction` is raise or lower, `size` is deed (±1) or major (±2). At most one change per region per scene; a major change needs an XP trigger reported in the same scene (D3).
- `look(entity)` reads current state so narration matches the world.

## Shared Play

Players act freely until their actions touch each other; then they share a scene resolved in beats, not initiative.

**Light scale:** each region runs 0–10. A deed moves it ±1, a major deed ±2. Neglected regions lose 1 per in-game week. The city ticks once per real day.

**Time (D9):** one real day is one in-game day, for everything: knack "per day" limits, the city tick and recovery. An in-game week is 7 real days.

**Day boundary (D29, superseded by D50):** a knack's "per day" limit now resets at midnight on the city clock.

**Solo by default.** Outside shared scenes, each player's action resolves immediately.

**Shared scenes.** When players are in the same place and acting on the same situation, code opens a shared scene.

- The scene runs in **beats**. Each beat collects every present player's intent within a short window, or until everyone has acted.
- The DM resolves the beat's intents together in one narration, ordered by the fiction, not by initiative. Each risky intent still gets its own roll.
- A player who doesn't act in time **holds**: their character keeps a default stance (guard, watch or withdraw) for that beat.
- Each region processes one beat at a time, and the DM reads fresh state before narrating.

**Logging off.**

- **At a haven** (lodging, a shrine, a Bond's home): the character is safe and recovers Harm and Fade.
- **Anywhere else:** the character lies low and leaves the scene at the end of the current beat.
- Offline characters cannot be harmed and their tracks don't change.
- The world keeps moving. On return, the DM gives a short "while you were gone" recap of changes to the character's Bonds, regions and debts.

## Player versus Player

PvP is allowed. The city remembers it, and nobody dies without choosing to.

**Guardrails:**

- **Death stays a choice.** PvP can fill another player's Harm track, but at 6 the victim still chooses Fall or Endure.
- **Havens are safe.** No PvP at lodgings, shrines or Bonds' homes.
- **Preying on the weak makes you forgettable.** Attacking a character several levels below you adds Fade to the attacker, scaled by the gap: 3–4 levels below adds 1 Fade, 5 or more adds 2, for each PvP consequence applied (D16).
- **The city takes notice.** Violence against a player lowers the region's Light and can trigger "a faction takes notice." Victims can file a grievance with the Registry, which posts bounties.
- **Opposed rolls.** Both players roll and the tiers are compared, so the defender always has agency. On equal tiers the defender holds (D5).

**Focus on social conflict.** Betrayal, theft, rival bargains with the same god and races to claim a forgotten shrine carry the drama. Violence is possible but expensive.

**Risks to design for:**

- **Prompt injection between players.** Player text is untrusted input. Code validates every tool call, whatever a player writes or the narration says.
- **Harassment.** Content lines the DM will not narrate, plus mute and block tools for players.
- **Content lines (D19):** the DM does not narrate sexual content, torture in detail, real-world hate groups or slurs, or harm to children. Cruelty is shown through its consequences, not gore.
- **Alt accounts.** Second characters used to farm or gang up; address before public launch.

## Costs and Budget

The DM's tokens are the main running cost; hosting is small. Cost scales with player-hours.

- **Usage ledger:** record every API call's token usage against the player and scene that triggered it, from the first prototype.
- **Monthly cap:** a hard spending limit set by the operator. When the pool runs out, the city goes quiet until the month resets.
- **Per-player allowances:** a monthly hour budget per player, so no one drains the shared pool.
- **Model routing:** cheaper models for routine narration, stronger ones for adjudication.
- **Routing in practice (D20):** one tool-using turn both adjudicates and narrates, so the turn loop runs on Sonnet. Haiku handles beat summaries, "while you were gone" recaps and knack drafting. The model is configurable per call type.
- **Starting cap (D21):** $50 a month for the whole city, as an operator setting. Retune after step 6 measures cost per player-hour.
- **Starting allowance (D22):** $10 per player per month, as an operator setting, enforced on measured spend. Players see it as an estimated number of hours left, from their own measured cost per hour.
- **Enforcement (implements D21, D22):** every call is priced from its token usage (input, output, cache reads and writes) and recorded against its player and scene. The budget is checked before every API call, so spending can pass a limit by at most one call; if a limit is reached mid-turn, the turn ends quietly and any tool writes already made stand. Months are UTC calendar months. A player's hours left are their remaining allowance divided by their own measured cost per hour, where play time is the time between calls, ignoring breaks over 10 minutes.
- **Later options:** a patron pool, bring-your-own API key, or prepaid credits, all built on the same ledger.

## Characters in Detail (D44–D49)

Built in layer 2 (2026-09-28), from D37.

- **Languages (D44):** Registry Standard is the common tongue; everyone in the city speaks it. The market tongues (Wolof, Tagalog, Arabic, Cantonese, Hindi and Portuguese) are common: anyone recognizes them by name. Protocol (the enclaves), Underside Cant (Old Vesper) and animal-speech are rare.
- **Neighborhoods (D45):** each district has a language profile saying how widely each language is spoken (everyone, most, many, some, few) and a note on its cultural flavor, and a place can have its own pocket (Tarp Row leans Cantonese and Arabic). Unnamed people speak what fits the neighborhood, and random encounters will draw their speakers from it. The Market District is the most mixed; other neighborhoods will be more concentrated.
- **A character's languages (D46):** Registry Standard, the origin's language (enclave-raised: Protocol; underside-born: Underside Cant; awakened animal: animal-speech; street-born and made people choose a market tongue), and one more of the player's choice.
- **Age and appearance (D47):** short free text, for narration only, with no rules effect. NPCs have them in content.
- **Maps (D48):** each district has a hand-drawn ASCII map. `/map` marks where the character is with [@]; places they have never played a scene in stay ??? until they go there.
- **Art (D49):** hand-authored ASCII only (plain printable characters, at most 60 columns by 10 lines); the model never draws. A place's vignette shows on a character's first visit and with `/look`; an NPC's portrait shows the first time a character shares a place with them.

## Time, Weather and Routines (D50–D55)

Built in layer 3 (2026-09-28), from D38.

- **The city clock (D50):** New Vesper runs on US Eastern time, in real time. The city's day turns over at city midnight: knack daily limits and the daily tick both use it (this replaces D29's UTC midnight). The budget month stays UTC, since that is accounting rather than fiction.
- **Weather (D51):** each district's weather changes on 3-hour blocks. Each block follows from the one before through the district's transition table, so it drifts (drizzle to steady rain, rarely a storm) instead of swinging. Weather is stored as it happens, so every player shares the same sky. It has no automatic rules effects; the DM may pick a harder rung when weather plainly matters.
- **NPC schedules (D52):** each NPC has a day of 4–6 blocks in content, plus days of the week that differ (Nana Priya's Sunday walk, Tomás's Monday off, Whisker gone below on Thursday nights). Code places every NPC by the clock; an NPC can also be away from the district.
- **Looking for someone who isn't there (D53):** the DM may say where they are likely to be only if someone present would plausibly know; otherwise they are simply not here.
- **NPC goals (D54):** each NPC has a personal goal in stages. The daily tick moves it on a stage every few days. Progress is private: it is not reported in "while you were gone" recaps, but the DM sees what each NPC has been doing lately and lets it show in play.
- **The daily tick (D55):** runs whenever anyone plays, once per city day, catching up on up to 14 missed days. It applies Light neglect (a district whose Light nobody raised for 7 days loses 1) and advances NPC goals.

## Seasons, Moon and Tides (D56–D59)

Added after layer 3 (2026-09-28).

- **The city calendar (D56):** five seasons tied to the real date: the Long Wet (November–February: cold rain, sleet, freezing fog), the Thaw-Rains (March–April: warm rain), the Lantern Months (May–June: mild, festivals, the rare dry spells), the Steam (July–August: muggy heat, thunderstorms) and the Gales (September–October: wind off the harbor, storms). Each season has its own weather odds, so the weather drifts within the season's range.
- **The moon (D57):** code computes the real phase. It colors narration, with two light hooks in content: at the new moon Old Vesper bleeds through and Whisker's ferry runs all night; at the full moon the forgotten are easier to see. NPC schedules can have new-moon and full-moon days, which win over weekdays. No roll modifiers.
- **The harbor (D58):** a quay at the Market's edge, the Tidewater Stairs, and the Mudflats beyond it, with a sea-gate into unmapped tunnels. Tomás buys the night's catch there at dawn.
- **Tides (D59):** code computes the tide (two highs and two lows a day, about 50 minutes later each day, bigger spring tides near new and full moon). Places can be closed by the tide (the Mudflats at high and rising water; the Drowned Station at a spring high tide), and `/go` refuses a flooded place and says when low water is. Places can impose a minimum difficulty rung at some tide states (the turning tide on the Stairs, the incoming tide on the flats), which code enforces the way it forces raw magic to Desperate. The model's constants are tuning values, not astronomy.

## NPC Memory and Attitudes (D60–D66)

Built in layer 4 (2026-09-28), from D39.

- **Three axes (D60):** an NPC's feelings toward a character or another NPC are trust, fondness and fear, each from −3 to +3, with words for each step (fear runs from contempt through unafraid to terrified). NPCs start from content: how they treat strangers, and an authored web of feelings toward each other.
- **Slow change (D61):** the DM proposes a change with the `adjust_attitude` tool; code moves one axis one step, at most once per axis per NPC and target per scene. Both NPCs must be present. This is an explicit exception to D1 (no state change without a roll), agreed in D39.
- **Reasons (D62):** every change is kept with its reason in an append-only log, and every authored feeling has a "why". The DM sees the latest reasons, so an NPC can explain why they feel as they do when asked, or decline to, in character.
- **Memories (D63):** when a scene closes, one cheap summary call writes a line for each NPC who was present about what they would remember of the character; nothing is written if the player did nothing. Each NPC keeps the last 8 lines per character; older ones fold into a single summary line.
- **Rolls (D64):** feelings never add to a roll. The DM uses them to decide whether a roll is needed at all and which rung fits.
- **The NPC web (D65):** NPC-to-NPC feelings are authored in content, seeded once, and then change in play with the same caps and reasons.
- **Personalities (D66):** each NPC has a few traits, speech habits and a sample line, shown to the DM with their feelings and memories. `/who` shows the player who is here and what they are doing.

## Random Encounters (D67–D75)

Built in layer 5 (2026-09-28) and reworked the same day: the DM writes every encounter fresh, so the same encounter never turns rote. A pickpocket can strike twice, but not the same person the same way.

- **The daily pool (D72):** each district's city day holds a random number of encounters, rolled by code the first time anyone is there and shared by everyone: 2–4 at Light 7–10, 3–6 at 4–6, 5–9 at 1–3. A fallen district has none. Unspent encounters don't carry over.
- **The DM decides when (D73):** the DM creates an encounter whenever the story calls for it, writing it fresh to fit the place, hour, weather and tide, with the `create_encounter` tool. Each one spends a slot of its kind from today's pool, at most one per turn; when the pool is empty the district is quiet. Code no longer checks on arrival or every fifth beat (this replaces D67).
- **Kinds (D74):** color, opportunity and trouble (D68). Code rolls each slot's kind by Light: 50/30/20% when bright, 35/30/35 when dimming, 20/25/55 when dark, and in the dark half the trouble is Old Vesper bleeding through. The DM can only spend kinds the pool holds, so falling Light stays dangerous.
- **Variety (D75):** the DM sees what it has already written in the district over the last 3 days and must not repeat it. The authored encounters in content become ideas the DM may draw on, filtered by their conditions (D69), never scripts. There is no per-encounter cooldown any more (this replaces D71).
- **Strangers (D70, still in force):** if the DM gives a stranger's role, code supplies their name, pronouns and a language from the neighborhood's mix (Underside Cant for bleed-through). They are logged, not NPCs.

## Languages (D76–D81)

Built in layer 6 (2026-09-28), from D41. The DM writes what people say; code decides how much of it the character understands.

- **Speech tags (D76):** the DM writes every line spoken aloud by anyone other than the player character as a tag naming the speaker, the language, how it sounds (tone) and what it means (gist), around the exact words. Code checks each tag: the speaker is here (an NPC present, a stranger from this scene, or an unnamed passer-by) and speaks that language. A tag that fails is never shown, since its words could be a translation the character has no right to; the DM is sent back to fix it, up to twice, as with owed consequences (D36). The player character's own words are never tagged (D34).
- **What a character hears (D77):** a line in a language they speak (their own, and Registry Standard) shows word for word. Otherwise they get the language's name if it is common, or "a language they don't know" if it is rare. Languages invented for the setting (Protocol, Underside Cant, animal-speech) come through as gibberish that code makes from each language's sounds; real-world languages come through only as a bracketed note, never as made-up syllables mocking a living language. Without a gist roll, not even the tone comes through.
- **Gist rolls (D78):** `call_for_roll` may name a language. It must be a Heart roll, for a language the character doesn't speak and that someone here speaks (the people present, the neighborhood's languages, a stranger in this scene, or a line already spoken in it), once per language per scene. What it earns holds for the rest of the scene: 10+ the gist and the tone; 7–9 the tone only if the cost is narrative, or the gist too if the cost is a real one (Harm, Fade, an item, or Light); 6 or less nothing, and the DM's move may be the speaker noticing.
- **The language knack (D79):** Ear for Tongues, a Heart knack: +1 on gist rolls, once per scene, and only on gist rolls. It is the ninth starter knack.
- **Speaking aloud (D80):** `/speak <language>` chooses which of the character's languages they speak aloud; the default is Registry Standard. Code tells the DM which NPCs present understand it, and the DM plays those who don't accordingly. NPCs never roll to follow a player character.
- **The speech log (D81):** every tagged line is logged with its speaker, language, words and what the character understood. The beat keeps, and is summarized from, what the player saw; the DM sees the last six lines with their words and what the character made of them.
- **Limits:** code can check tags, not prose. The prompt forbids translating or hinting at a line outside its tag, but a DM that paraphrases in plain narration is not caught mechanically; playtest will show whether this needs more.

## Bodily Needs (D83–D89)

Built in layer 7 (2026-09-28), from D82. Code owns every need; the DM shows them in the story and never changes them.

- **Five needs (D83):** hunger, thirst, tiredness, cold and heat, each tracked by code from 0 to 3, with words for each step (hunger: fed, peckish, hungry, starving; thirst: slaked, thirsty, parched, dehydrated; tiredness: rested, tired, exhausted, dead on their feet; cold: warm enough, chilled, cold, freezing; heat: cool enough, hot, overheated, heatstruck).
- **Effects (D84):** a need at 2 takes −1, and at 3 (its worst) −2, from two stats:

  | Need | Stats |
  | --- | --- |
  | Hunger | Steel, Heart |
  | Thirst | Steel, Wire |
  | Tiredness | Slick, Wire |
  | Cold | Steel, Slick |
  | Heat | Steel, Heart |

  Penalties stack with each other and with Harm's, but a roll's stat never goes below −3, the lowest the Harm rules allow (D11). Weird is never worn down. Harm and Fade come only at the worst level: reaching it costs 1 box, and so does each further step spent there. Tiredness costs Fade (the city loses track of the sleepless); the others cost Harm. A full Harm track still ends in the player's choice, Fall or Endure.
- **Time (D85):** needs are counted on the city clock, only while the character is online. Thirst climbs a step every 3 hours, hunger every 4, tiredness every 6. Cold and heat climb a step per hour of exposure and ease a step per half hour out of it. These are tuning values, compressed from real life, for playtest.
- **Exposure (D86):** a place is sheltered (the weather doesn't reach you: the Hundred Hooks, the Weighhouse), exposed (the default) or cold whatever the weather (the Drowned Station). Outside, some weather is cold (freezing fog, cold rain, sleet, gales) or hot (muggy heat), and otherwise the season decides: the Long Wet is cold, the Steam hot. Clothing and gear don't count yet.
- **Relief (D87):** `/eat` and `/drink` buy what the place sells, at a price in content, paid in glitter (noodles on Tarp Row, tea at the Hooks, free rainwater at the Umbrella Shrine), and clear hunger or thirst. `/rest` at a haven clears tiredness. Cold and heat ease out of the weather. None needs a roll. When the player character eats, drinks or sleeps in the story, the DM narrates them starting and points to the command, as with `/go` (D27). A meal an NPC gives away, and food carried as an item, come later.
- **Offline (D88):** time offline never counts; needs pick up where they were. Logging off at a haven clears them all.
- **Different people, different needs (D89):** each origin lists its needs. Made people neither eat nor drink, and feel no cold, but tire and overheat; everyone else has all five. New kinds of people (D42) declare their own.

## Planned: A Living World (D37–D43)

Direction agreed after the first playtest (2026-09-28). Each layer's details are decided when it is built, and every mechanic stays code-owned: the DM proposes, code decides.

- **Character details (D37):** every player character and NPC has an age, pronouns, appearance and the languages they speak. NPCs get them in content; players choose them at creation.
- **Time and weather (D38):** the city clock runs in real time, in one city time zone. Weather comes from per-district tables that code rolls. NPCs follow schedules in content (Nana Priya eats, shops, sleeps), code places them by the clock, and the daily city tick moves their goals along.
- **NPC memory and attitudes (D39):** code stores each NPC's attitude toward each character and short notes on past interactions. The DM proposes changes through a tool, and code caps how far an attitude moves per scene. NPC-to-NPC attitudes live in content. NPCs get traits, speech habits and a sample line for distinct voices.
- **Random encounters (D40):** code rolls on arriving somewhere and every few beats (about 5), from per-district tables; the odds rise as region Light falls. The DM narrates what code drew.
- **Languages (D41):** code tracks who speaks what and what language each line is spoken in. Speech a character does not understand reaches them as gibberish. Common languages can be recognized by name. Getting the gist of an unknown language is a Heart roll: 10+ the gist and tone, 7–9 the tone only or the gist at a cost, 6 or less gibberish and perhaps the speaker notices. A language knack gives +1 to those rolls, with a use limit per the knack budget. (Built: D76–D81.)
- **Setting-native kinds (D42):** new kinds of people are invented for New Vesper and added as origins, like made people and awakened animals, rather than classic fantasy races.
- **Order (D43):** playtest fixes, then character details, then time, weather and schedules, then NPC memory and attitudes, then encounters, then languages, then bodily conditions (D82), then setting-native kinds, with a playtest after each.

## Open Questions and Next Steps

The first build is a playable CLI prototype: one player, one district, the full rules loop.

**Open questions:**

- [ ] Starter knack catalog: about 20 knacks across the five stats. (9 shipped for the Market District.)
- [ ] Advanced knacks and origin evolutions for level 5 and up.
- [ ] **High priority:** who a favor is owed to, with player understanding and choice (D10 is provisional).
- [ ] How gods collect on favors, mechanically.
- [x] Market District layout: key stalls, NPCs, shrines, the drowned station.
- [ ] Beat window length, and whether it adapts to how many players are present.
- [ ] Alt accounts: how many characters a player may have.
- [x] Revisit the knack day boundary (D29): city midnight (D50).
- [x] The city's time zone (D38): US Eastern (D50).
- [x] The languages of the Market District, and which count as common (D44, D45).
- [ ] Multiplayer step (D32): shared scenes, opposed-roll PvP with its guards, healing others, being named by another player.
- [x] Bodily conditions: hunger, thirst, heat and cold, sleep and the like. Built in layer 7 (D83–D89). Still open: clothing and gear against the weather, food as items and meals given by NPCs, whether resting should take time, and tuning the rates after a playtest.

**Prototype plan:**

1. Python CLI with SQLite state: characters, regions, items, events.
2. Rules engine: the 2d6 resolver, tiers, tracks, XP triggers, all unit-tested.
3. DM agent on the Claude API with the tool contract above and a setting prompt built from this doc.
4. One playable scene end to end, then playtest and tune the prompt.
5. Multiplayer, after the single-player playtest (D32).

## Decision log

D1–D23 were decided 2026-09-27, in the repository, from the open questions raised after the rules, state and content steps. Each decision was then reviewed individually with the designer; D11, D16, D18, D21 and D22 changed in that review, and D10 is marked for revisiting. D24–D32 were decided 2026-09-28 from the calls made while building the DM agent, each reviewed individually; D29 is marked for revisiting. D33–D43 came from the first playtest the same day, D44–D49 from building character details, D50–D55 from time and weather, D56–D59 from seasons, moon and tides, D60–D66 from NPC memory and attitudes, D67–D75 from random encounters (D72–D75 replacing parts of D67–D71 the same day), D76–D81 from languages, D82 from the designer after layer 6, and D83–D89 from bodily needs (the effects in D84 chosen by the designer).

| ID | Topic | Decision |
| --- | --- | --- |
| D1 | Rolls gate consequences | Single-use roll id; consequences cite it; 10+ none, 7–9 one cost, 6− one move; no roll, no state change except `report_trigger` rewards |
| D2 | 7–9 costs | Take one item, 1 Harm, 1 Fade, region Light −1, or narrative-only |
| D3 | `adjust_light` | Adds direction (raise/lower) and size (deed ±1 / major ±2); one change per region per scene; major needs an XP trigger in the same scene |
| D4 | XP triggers | Exactly four; 1 XP each; once per character per scene |
| D5 | Opposed-roll ties | Defender holds |
| D6 | Move magnitudes | Harm and Fade 1–3; encroach −1; others 1; threat clocks 4 segments, defined in content, advanced by 1, never created by the DM |
| D7 | Enforced tags | Only `no-hands` (blocks `needs-hands` knacks) for now |
| D8 | Recovery | Haven: 1 Harm and 1 Fade per real day offline; treatment knack: 1 Harm per use; named by another player: 1 Fade once per scene |
| D9 | Time | 1 real day = 1 in-game day; a week is 7 real days |
| D10 | Favor owed to whom | **Provisional, high priority to revisit.** Shrine's god or the god being tapped; otherwise Fade or a side effect. Player should understand and choose where debt accrues |
| D11 | Harm penalties | −1 to Steel and Slick at 3–4 Harm, −2 at 5–6 |
| D12 | Fade bands | Row ranges: Unnoticed 1–2, Unseen 3–4, Slipping 5–6 |
| D13 | After Endure | Harm drops to 4 |
| D14 | The +4 stat | Level-10+ milestone advanced knack names one stat; its cap becomes +4; one stat ever |
| D15 | Slipping (prototype) | Move to the Underside entrance, gain `half-faded`, keep playing |
| D16 | Preying on the weak | Attacker gains Fade per PvP consequence: +1 at 3–4 levels above the target, +2 at 5+ |
| D17 | Who chooses | The player, through CLI menus, for creation and leveling |
| D18 | Currency | 1 glamour = 10 glims = 100 glitter; stored in glitter; start with 5 glims; earned from loot entries or NPC deals |
| D19 | Content lines | No sexual content, detailed torture, real-world hate groups or slurs, or harm to children |
| D20 | Model routing | Turn loop on Sonnet; Haiku for summaries, recaps and knack drafting; configurable per call type |
| D21 | Monthly cap | $50 per month, operator setting |
| D22 | Per-player allowance | $10 per player per month on spend, shown to players as estimated hours left |
| D23 | Where decisions live | Written into this file and tagged; to be copied back to the living doc |
| D24 | Loot needs a roll | `grant_from_table(roll_id, table_id)`: a 7+ roll, one grant per roll |
| D25 | `call_for_roll` fields | Optional `knack` (held knack; bonus, limits, tags) and `magic` (a casting) |
| D26 | Consequence targets | Harm and Fade land on the roller only; PvP waits for opposed rolls |
| D27 | Movement | Player's `/go` command; the DM never moves characters |
| D28 | Taken items | Leave play; the log records it |
| D29 | Knack day boundary | Superseded by D50: city midnight |
| D30 | Treatment knacks | Heal the roller only, 1 Harm on 7+ |
| D31 | Casting with Wire | Only through a tech-magic knack |
| D32 | Prototype scope | Single-player through budget and playtest; multiplayer is its own later step |
| D33 | Narration | Third person, present tense, by name and the sheet's pronouns; players choose pronouns |
| D34 | Player input | Plain text is action (any person); quotes are exact speech; the DM never rewrites or adds to them |
| D35 | `/ask` | Out-of-character question: look only, no roll, state change, time or beat |
| D36 | Owed consequences | A 7–9 or 6− roll must get its consequence; code sends the DM back (up to twice) |
| D37 | Character details | Age, pronouns, appearance, languages for players and NPCs (built: D44–D49) |
| D38 | Time and weather | Real-time city clock, weather, NPC schedules, daily tick (built: D50–D55) |
| D39 | NPC memory | Attitudes and interaction notes in code; DM proposes, code caps (built: D60–D66) |
| D40 | Encounters | Code rolls on arrival and every 5th beat; odds rise as Light falls (built: D67–D71) |
| D41 | Languages | Tracked; unknown speech as gibberish; Heart roll for the gist; language knack +1 (built: D76–D81) |
| D42 | New kinds of people (planned) | Setting-native kinds as origins, not classic fantasy races |
| D43 | Build order | Fixes; details; time/weather/schedules; NPC memory; encounters; languages; kinds |
| D44 | Languages | Registry Standard for everyone; market tongues common; Protocol, Underside Cant, animal-speech rare |
| D45 | Neighborhood languages | Per-district spread (everyone to few) and culture note; per-place pockets |
| D46 | A character's languages | Registry Standard + origin's language + one of choice |
| D47 | Age and appearance | Short free text, narrative only |
| D48 | Maps | Hand-drawn per district; [@] for here; unvisited places stay ??? |
| D49 | Art | Hand-authored ASCII vignettes and NPC portraits; the model never draws |
| D50 | City clock | US Eastern, real time; the city day turns at city midnight (replaces D29); budget month stays UTC |
| D51 | Weather | 3-hour blocks that drift through a transition table; stored and shared; no automatic effects |
| D52 | NPC schedules | 4–6 blocks a day plus weekday variations; code places NPCs by the clock |
| D53 | Absent NPCs | Hints only when someone present would plausibly know |
| D54 | NPC goals | Staged goals advanced by the tick; private, shown through play |
| D55 | Daily tick | Runs when anyone plays; up to 14 days of catch-up; neglect after 7 days; NPC goals |
| D56 | City calendar | Five seasons on the real date, each with its own weather odds |
| D57 | Moon | Real phase; flavor plus new- and full-moon hooks and schedules; no roll modifiers |
| D58 | Harbor | The Tidewater Stairs quay and the Mudflats with a sea-gate, in the Market |
| D59 | Tides | Computed; can close places and impose a minimum rung, enforced by code |
| D60 | Attitude axes | Trust, fondness, fear, each −3 to +3; start from content |
| D61 | Attitude change | `adjust_attitude`: one step per axis per NPC and target per scene; exception to D1 |
| D62 | Reasons | Every change and authored feeling has a reason; the NPC can explain or decline |
| D63 | Memories | One line per present NPC when a scene closes; last 8 kept, older folded |
| D64 | Rolls | Feelings never add to rolls; they shape whether to roll and the rung |
| D65 | NPC web | Authored, seeded once, then changes in play with the same caps |
| D66 | Personalities | Traits, speech habits, a sample line; `/who` for the player |
| D67 | Encounter odds | Superseded by D72–D73: a daily pool, and the DM decides when |
| D68 | Encounter kinds | Color, opportunity, trouble; weighted by Light through the pool (D74) |
| D69 | Conditions | Place, part of day, weather, tide, season and moon filters; now on encounter ideas |
| D70 | Strangers | One-off, generated by code at the DM's request with a neighborhood language |
| D71 | Pacing | Superseded by D73 and D75: one per turn, no cooldown, recent ones shown to avoid repeats |
| D72 | Encounter pool | Per district per city day, rolled by Light: 2–4, 3–6 or 5–9; shared; no carry-over |
| D73 | DM creates encounters | Fresh each time via `create_encounter`, spending the pool; at most one per turn |
| D74 | Kinds in the pool | Rolled by Light band; dark trouble half Underside; the DM spends only what the pool holds |
| D75 | Variety | Recent district encounters shown so the DM doesn't repeat; content entries are ideas only |
| D76 | Speech tags | The DM tags every line others speak with speaker, language, tone and gist; code checks speaker and language; a bad tag is never shown and the DM is sent back (up to twice) |
| D77 | What is heard | Own languages word for word; common languages named, rare ones not; invented languages as code-made gibberish, real ones as a bracketed note; no tone without a gist roll |
| D78 | Gist rolls | `call_for_roll` names a language: Heart, unspoken by the character, heard here, once per language per scene; 10+ gist and tone, 7–9 tone or gist for a real cost, 6− nothing; lasts the scene |
| D79 | Language knack | Ear for Tongues: Heart, +1 on gist rolls only, once per scene |
| D80 | Speaking aloud | `/speak` picks one of the character's languages (default Registry Standard); the DM is told which NPCs understand it; NPCs never roll |
| D81 | Speech log | Every line logged with what the character understood; beats keep what the player saw; the DM sees the last six lines |
| D82 | Build order | Bodily conditions (hunger, thirst, heat and cold, sleep) are layer 7, before setting-native kinds (now layer 8) (built: D83–D89) |
| D83 | Bodily needs | Hunger, thirst, tiredness, cold, heat; each 0–3, tracked by code, with words per step |
| D84 | Need effects | −1 at 2 and −2 at 3 to two stats each; stacks, but a roll stat stays ≥ −3; at the worst, 1 Harm (Fade for tiredness) on reaching it and per further step |
| D85 | Need time | Counted only online on the city clock: thirst 3 h, hunger 4 h, tiredness 6 h per step; cold and heat 1 h exposed, easing 1 per 30 min |
| D86 | Exposure | Places are sheltered, exposed or always cold; weather (else season) is cold or hot |
| D87 | Relief | `/eat` and `/drink` buy what a place sells, in glitter; `/rest` at a haven; no roll; the DM points to the command |
| D88 | Needs offline | Frozen offline; logging off at a haven clears them |
| D89 | Needs by origin | Each origin lists its needs; made people only tiredness and heat |
