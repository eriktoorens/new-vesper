# New Vesper — Setting & Rules

Exported from the living design doc on 2026-09-27. The living doc is where design discussion happens; update this file when it changes.

**Decisions D1–D140** (2026-09-27 and 2026-09-28) were made in this repository after the export and are not yet in the living doc. Each is tagged where it applies and listed in the [Decision log](#decision-log). Copy them back to the living doc before the next export.

## Overview

New Vesper is a persistent, shared, text-based RPG where an AI narrator runs a rain-soaked megacity in which magic and technology both run on the same fuel: attention. Belief makes things real; being forgotten unmakes them.

- **Format:** persistent shared world, many players, asynchronous play.
- **Narrator:** a Claude API agent that narrates and adjudicates; code owns all game state.
- **Tone:** grimbright. The world is cruel but not nihilistic. Effort counts, kindness matters, and small victories stay on the page.
- **Inspirations:** Blade Runner (rain, noir, made people), Shadowrun (magic meets corporate tech), The Diamond Age (nanotech enclaves, primers), American Gods (gods fed by belief), Neverwhere (a hidden city of the forgotten), China Miéville's Perdido Street Station (D95), Thomas Metzinger's The Ego Tunnel (D109), and a splash of Discworld for bureaucratic absurdity. The mechanics owe most to *Apocalypse World* and *Blades in the Dark*; see Debts (D140).

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

**Difficulty ladder:** Routine +1 · Risky +0 · Hard −1 · Desperate −2. The Narrator chooses a rung; it never invents a number.

**Outcome tiers:**

| Total | Tier | What happens |
| --- | --- | --- |
| 10+ | Clean success | You get what you wanted |
| 7–9 | Success with a cost | You get it, but lose something: supplies, time, trust, or a bit of Light |
| 6 or less | The city moves | The Narrator makes a move against you from the allowed list |

No roll when there is no risk. The Narrator calls for a roll only when failure would be interesting.

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

**Allowed moves on 6 or less.** The Narrator picks one; code caps its size.

- Deal harm
- Add Fade
- Take something
- Separate them
- Reveal an unwelcome truth
- Advance a threat clock
- A faction takes notice
- The dark encroaches (region Light −1)

**Take something (D28):** the item leaves play; the event log records who lost what and why.

**Magnitudes (D6):** Deal harm and Add Fade are 1–3 boxes. The dark encroaches is exactly −1 Light. Every other move is magnitude 1. Threat clocks have 4 segments and are defined in content, per district; the Narrator can advance a clock by 1 but never creates one.

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
| Hearsay (D90) | Born of a story told often enough to stand up and walk | story-born |
| Castoff (D90) | A mascot that stepped off the billboard when its brand went under | brand-born, glows |
| Mislaid (D90) | A lost thing that waited so long to be found it became someone | object-born, overlooked |

Tags constrain the Narrator: an awakened cat cannot pick a lock, but walks where nobody asks questions.

**Tags code enforces (D7):** for now only `no-hands`, which blocks knacks tagged `needs-hands`. The other tags guide narration through the prompt until playtest shows a need to enforce them.

**Creation:** assign the array +2, +1, +1, 0, −1 to the five stats; pick an origin; pick two knacks; name one Bond, a person your character matters to.

**Who chooses (D17):** the player makes every creation and leveling choice through CLI menus. The Narrator never picks stats, knacks or level choices.

**The body (D116):** at creation the player says, in a line, how their character is built and how they move (fins for hands, waddles on a tail fin; a handle, a canopy, one broken rib). It is narrative only and changes no rules; `no-hands` stays an origin tag (D7). Characters made before it are asked once when they next log in, and `/body` changes it.

**Currency (D18):** decimal coin: 1 glamour = 10 glims = 100 glitter. Glitter is small change, glims are everyday money, glamour is a big deal. Code stores every amount as a whole number of glitter and only displays denominations. New characters start with 5 glims (50 glitter). Currency is earned through loot table entries or specific NPC deals, never invented by the Narrator.

**Knacks** are the open catalog of things a character does well. Anyone can take any knack the fiction supports; a rat hacker is fine if you can say how.

**Leveling up.** Reaching level N+1 costs 5 + N XP, earned from the advancement triggers. Each level, pick one:

- A new knack
- +1 to a stat (cap +3)
- Heal a scar

Every fifth level also unlocks an **advanced knack** or an **origin evolution**, such as a plaza pigeon becoming the plaza's minor god.

**The +4 stat (D14):** from level 10, a milestone advanced knack may name one stat. That stat's cap becomes +4, and later +1 stat choices can raise it there. Only one stat per character, ever.

**Player-proposed knacks:**

1. The player describes the knack in plain words.
2. A separate Narrator call, outside any scene, drafts it in a fixed template: trigger, stat, 10+ effect, 7–9 effect, limits, tags.
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

**Advancement:** experience comes from a fixed list of triggers that code checks: protecting someone, making a sacrifice, keeping a hard promise, raising a region's Light. Killing things earns nothing on its own. See Characters for what XP buys. The Narrator can report that a trigger happened; code decides whether it pays out.

**Triggers and payouts (D4):** exactly four triggers: `protect_someone`, `make_a_sacrifice`, `keep_a_hard_promise`, `raise_light`. Each pays 1 XP, at most once per character per scene.

## Magic

Magic is bargaining with attention. There are no spell slots and no mana; every working costs something the world remembers.

- **Rolls:** casting is a Weird roll. Tech-magic, such as hacking a god's prayer network, can use Wire, through a knack tagged tech-magic (D31). Raw magic without a knack uses Weird.
- **Knacks** define what a character can do reliably, such as asking a shrine's god one question. Anyone can attempt raw magic without a knack, at Desperate difficulty.
- **Costs on 7–9** come from a magic list: a tick of Fade, a side effect, or a favor owed to a god.
- **The favor ledger:** code records every favor owed. Gods collect, and debts become story hooks. This is the Tally made mechanical.
- **Who is owed (D10, provisional):** the god of the shrine the character is at, or the god whose power they are tapping. If neither applies, a 7–9 cost must be Fade or a side effect, not a favor. **High priority to revisit:** the player should understand, and have some choice over, where a debt accrues. Candidate alternatives: the district's patron god as a fallback, or an unnamed creditor ("something that noticed") named later as a story hook.

## Narrator Authority

The AI decides what is being attempted and how the story reads; code decides what actually happens to the world.

One turn runs as a loop:

1. **Player acts:** types an intent.
2. **Narrator agent** picks the stat and difficulty, and calls `call_for_roll`.
3. **Rules engine** (code) rolls 2d6 and returns the tier.
4. **Narrator agent** narrates the result and picks a move, calling `apply_consequence`.
5. **State layer** (code) validates the request and writes state.
6. **Player sees** the changed world.

Every state change goes through a tool, and every tool checks the request against the rules before writing.

**Narration (D33):** the Narrator tells the story in third person, present tense, using the character's name and the pronouns on their sheet. Player characters choose pronouns at creation.

**Player input (D34):** plain text is what the character does, in any grammatical person; text in quotation marks is what the character says, word for word. The Narrator never rewrites, paraphrases or adds to a player character's words, actions, thoughts or feelings; it narrates the world's response.

**The Bond is the player's (D110):** the Bond named at creation is part of the character's backstory and belongs to the player. The Narrator never invents facts about it: who the Bond is, where they are, or what passed between them. When play touches the Bond, the Narrator asks through the fiction, as an NPC asking "What's she to you?", and builds on the player's answer. (In the fourth playtest, asked about a character's Bond, an NPC said she had stayed there years ago: a fact the player hadn't given.)

**Questions to the Narrator (D35):** `/ask` puts an out-of-character question to the Narrator. It may only look: no roll, no state change, no time passing, no beat. The Narrator answers with only what the character can see, hear or reasonably know.

**NPCs who are here (D111, D112, D132):** an NPC is in one place at a time, and the Narrator plays the ones where the character is. They stay until the story has them go: where their agenda calls them, or where a want takes them. The Narrator weighs the scene against their errand, can let them run late, and can cut a conversation short; it writes each exit (a reason, a parting line, colored by how they feel) and never lets an NPC simply vanish. Code reads the exit from the narration after the turn and moves them.

**Time that passes shows (D114):** when 15 minutes or more of city time pass between two turns in a scene, code tells the Narrator how long it was and when the last turn was. The Narrator shows it first (the light and weather have moved on, people have gone about their business, food is put away, anyone still here has waited) and never picks up mid-sentence. It never decides what the player character did meanwhile.

**Who is here, every turn (D117):** each turn opens with a short block built by code: the player character's name, kind, pronouns, body and looks; each NPC and stranger present, with what they are, their pronouns and looks; and the items held and lying here. The Narrator never contradicts it, and describes the character only as their body allows, adding nothing about it the player hasn't given.

**When the player's line doesn't fit the body (D118):** if a player has their character do something their body can't (fingers on an umbrella, hands on a cat), the Narrator doesn't narrate it. It asks once, in a short bracket on its own line, how they do it, such as "(Zeno has no fingers. How does it lift the coat?)", and narrates nothing else that turn. It is the first piece of "ask, don't invent".

**Owed consequences (D36):** a roll at 7–9 or 6 or less must get its consequence. If the Narrator tries to end a turn with one still owed, code sends it back to apply it (up to twice).

**One action, one roll (D98):** a player's action gets at most one roll, and its result stands. Code refuses a second `call_for_roll` in the same turn, so the Narrator cannot re-roll a failure; when it is sent back to apply a consequence or fix speech, it tells the turn once, replacing its earlier telling, so the player sees one outcome. A guard added after the first blind playtest, though the database showed that playtest's problem was a different one (D99).

**One action per prompt (D99):** a player acts one line at a time, and only on a world they have seen. An action is a single line typed at the prompt after the world's last answer is shown. Anything typed or pasted while the Narrator is still answering is discarded, and the player is told. A paste of several lines is refused whole, so no part of it reaches the Narrator: joining it would let a player script several actions, or text posing as the Narrator's output, into one turn, and taking it line by line would act on a world the player hadn't seen. The session itself refuses an action or question containing line breaks or control characters, whatever the client, and the state layer refuses to store one. (In the first blind playtest, a three-line paste became three turns 26 seconds apart, and the player saw three contradictory outcomes for one action.)

**Every prompt, and names that are names (D107):** the one-line rule covers every prompt, character creation included: a paste of several lines is refused whole wherever it lands. (In the second playtest, a paste meant for the shell became a character's name and pronouns.) A name is 1 to 40 characters of letters in any script, digits, spaces, apostrophes, hyphens and periods; pronouns are words joined by slashes, like she/her or it/its. Players can change either at any time with `/rename` and `/pronouns`; the event log keeps the old name.

**Every consequence shows (D108):** a consequence that moves no number (a separation, an unwelcome truth, a faction taking notice, a price paid in the story, a side effect) still appears in the player's bracketed line, as "the city moves: an unwelcome truth" or "cost: a price paid in the story". The Narrator also makes each consequence visible in the story.

**Movement (D27):** the player moves with the `/go <place>` command; code checks the place is real and in the same district, closes the scene and opens one there. The Narrator never moves characters, since that would be a state change without a roll. When a player says they head somewhere, the Narrator describes them setting off and points to `/go`.

**Who a roll's consequences land on (D26):** Harm and Fade from a roll land only on the character who rolled. Harming another player's character needs an opposed roll, which comes with multiplayer; until then there is no PvP state change at all.

| The Narrator decides | Code owns |
| --- | --- |
| Whether a roll is needed | The dice |
| Which stat applies | Harm, Fade, stats, inventory |
| Which difficulty rung | Currency, loot tables, XP triggers |
| Which move to make on 6 or less, from the allowed list | Region Light levels |
| Narration, NPC voices, scene description | What exists: items, NPCs, places |

**Initial tool contract:**

- `call_for_roll(stat, difficulty, stakes, knack?, magic?)` returns the total, the tier and a single-use roll id (D1). `knack` names a knack the character holds, so code can apply its bonus, use limit and tags; `magic` marks a casting. A knack tagged magic makes the roll magic (D25).
- `apply_consequence(roll_id, type, target, magnitude)` checks the roll's tier, the allowed list and the magnitude cap, then writes state (D1, D2).
- `grant_from_table(roll_id, table_id)` hands out loot from a table; the Narrator never invents items. It needs a successful roll (7+), and each roll grants loot at most once (D24).
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
- The Narrator resolves the beat's intents together in one narration, ordered by the fiction, not by initiative. Each risky intent still gets its own roll.
- A player who doesn't act in time **holds**: their character keeps a default stance (guard, watch or withdraw) for that beat.
- Each region processes one beat at a time, and the Narrator reads fresh state before narrating.

**Logging off.**

- **At a haven** (lodging, a shrine, a Bond's home): the character is safe and recovers Harm and Fade.
- **Anywhere else:** the character lies low and leaves the scene at the end of the current beat.
- Offline characters cannot be harmed and their tracks don't change.
- The world keeps moving. On return, the Narrator gives a short "while you were gone" recap of changes to the character's Bonds, regions and debts.

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
- **Harassment.** Content lines the Narrator will not narrate, plus mute and block tools for players.
- **Content lines (D19):** the Narrator does not narrate sexual content, torture in detail, real-world hate groups or slurs, or harm to children. Cruelty is shown through its consequences, not gore.
- **Alt accounts.** Second characters used to farm or gang up; address before public launch.

## Costs and Budget

The Narrator's tokens are the main running cost; hosting is small. Cost scales with player-hours.

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
- **Weather (D51):** each district's weather changes on 3-hour blocks. Each block follows from the one before through the district's transition table, so it drifts (drizzle to steady rain, rarely a storm) instead of swinging. Weather is stored as it happens, so every player shares the same sky. It has no automatic rules effects; the Narrator may pick a harder rung when weather plainly matters.
- **NPC schedules (D52):** each NPC has a day of 4–6 blocks in content, plus days of the week that differ (Nana Priya's Sunday walk, Tomás's Monday off, Whisker gone below on Thursday nights). An NPC can also be away from the district. (Code placing every NPC by the clock is replaced by D111–D113: the schedule is now an agenda.)
- **One place at a time (D111):** where each NPC is, and what they are doing, is stored state, like a character's location. An NPC is in exactly one place, always. The schedule is their agenda: what they mean to be doing, not where the clock puts them.
- **The Narrator plays the NPCs who are here (D112):** while an NPC is where a player character is, only the Narrator moves them on, through `npc_moves_on`, which code checks: the NPC must be here, and their agenda must call them somewhere or to something else. Code decides where they go (where their agenda says); the Narrator decides when and how it reads. The agenda is soft: the Narrator weighs what is at stake in the scene against the NPC's errand, can keep them talking and let them run late, and can cut a conversation short when the errand matters more. It never has to keep the player entertained. (From the fourth playtest, where Nana Priya vanished mid-conversation when her schedule moved her.) (How they leave changed with D132: no tool; code reads the exit from the narration.)
- **Exits are read from the narration (D132):** in the fifth playtest the Narrator never called `npc_moves_on`, and when it walked Tomás off toward Sefu's stall, state never followed. The after-turn pass (D123) now also reads departures: `npc-id | goes to | place-id | why`. Code carries them out and the tool is retired. NPCs may move because they want to, not only along their agenda.
- **Detours (D133):** an NPC who goes somewhere their agenda doesn't say stays there until their next scheduled block begins, two hours at most, even with nobody there; then they rejoin their day from wherever they are. Going where their agenda says is simply taking up their day.
- **What code checks (D134):** the NPC was in the scene that turn; the place is real, in the same district, not where they already are, and above water; "away" (out of the district) only when their day takes them there. The reason is required and logged, not checked against their wants. The player character still moves only by `/go` (D27): never alongside a departing NPC.
- **Arriving together (D136):** when the character takes `/go`, the first turn of the new scene gets the last scene's closing moments (where it was, its last narration, and who walked here with the character). Every turn of the new scene marks the NPCs who left the last scene for this place, and are here, as `came_with_you` in who_is_here: they know the character is here and aren't surprised to see them. (From the fifth playtest, where Tomás walked to the Weighhouse with Brightfin, then startled at his arrival.)
- **Off-screen, the agenda (D113):** an NPC nobody is with follows their agenda exactly, from wherever they really are, so one kept late simply goes on to their next errand. Small variation (running early or late, skipping an errand in bad weather) is a later idea.
- **Looking for someone who isn't there (D53):** the Narrator may say where they are likely to be only if someone present would plausibly know; otherwise they are simply not here.
- **NPC goals (D54):** each NPC has a personal goal in stages. The daily tick moves it on a stage every few days. Progress is private: it is not reported in "while you were gone" recaps, but the Narrator sees what each NPC has been doing lately and lets it show in play.
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
- **Slow change (D61):** the Narrator proposes a change with the `adjust_attitude` tool; code moves one axis one step, at most once per axis per NPC and target per scene. Both NPCs must be present. This is an explicit exception to D1 (no state change without a roll), agreed in D39.
- **Reasons (D62):** every change is kept with its reason in an append-only log, and every authored feeling has a "why". The Narrator sees the latest reasons, so an NPC can explain why they feel as they do when asked, or decline to, in character.
- **Memories (D63):** when a scene closes, one cheap summary call writes a line for each NPC who was present about what they would remember of the character; nothing is written if the player did nothing. Each NPC keeps the last 8 lines per character; older ones fold into a single summary line.
- **Rolls (D64):** feelings never add to a roll. The Narrator uses them to decide whether a roll is needed at all and which rung fits.
- **The NPC web (D65):** NPC-to-NPC feelings are authored in content, seeded once, and then change in play with the same caps and reasons.
- **Personalities (D66):** each NPC has a few traits, speech habits and a sample line, shown to the Narrator with their feelings and memories. `/who` shows the player who is here and what they are doing.
- **Moods (D119):** each NPC has a mood for the city day. Code rolls it each morning from a short list in content, the same for everyone: from their "goal news" moods on a day their own goal moved on, often from their "foul weather" moods when the weather is cold or hot, and otherwise from their usual ones. The Narrator may shift it with `npc_mood`, once per NPC per scene and with a reason, when something on the page plainly would; the shift lasts the rest of the day.
- **What they want now (D120, replaced by D122):** the Narrator was to set what each NPC wants in a scene with `npc_wants`, kept and shown every turn.
- **Wants are played, not stored (D122, replaced by D124):** in the fifth playtest the Narrator never set a want, yet played NPCs pursuing their own ends well from prose (Nana protecting a hungry lodger). The stored version and its tool are dropped; the prompt still asks the Narrator to give each NPC in a scene something they want right now, and to play them pursuing it.
- **What they want now, kept by code (D124):** from the designer: wants played only in prose drift between scenes. Each NPC now holds up to four current wants, one set per NPC shared by every player, each optionally about someone ("wants Brightfin to keep his word about the boy"). They change only at scene close: the cheap call that already writes memory lines also proposes new wants, wants met or dropped, and tensions, each with a reason from the scene. Code keeps only changes for NPCs who were in the scene, at most three of each kind; an ended want keeps its row. Nothing changes without a reason, and most scenes change nothing.
- **The journal (D125):** each NPC present reaches the Narrator with one journal: at_heart (their authored wants), wants_now with why each began, tensions, lately (D54), what they remember of the character (D63) and what they know (D121). The tables underneath are unchanged; it is the shape a holder's slice of the belief field (D106) will take.
- **Wants in tension (D126):** two current wants may pull against each other, one NPC's own (Nana wants the week's rent, and wants to keep the boy who can't pay) or two NPCs' (Tomás wants his supplier exposed, Adaeze wants him left alone). The scene-close call proposes them; code keeps a tension only between current wants, with one of them held by someone in the scene, and it ends when either want does. The Narrator lets a tension show in what NPCs say and choose, and never settles it by narration.
- **A restated want replaces the old one (D137):** the scene-close call is told never to add a want an NPC already holds in other words, and to end one it corrects or replaces (as dropped, "replaced by …") when it adds the new one. Scene close now runs on the turn model (Sonnet) rather than Haiku: it judges wants and tensions, will carry the social graph, and runs once a scene, so the cost is small. Its model is configurable (`NEW_VESPER_JOURNAL_MODEL`); folds stay on Haiku. (From the fifth playtest, where Tomás gained "confront Flour supplier about late delivery", a misreading, then the right want, and kept both.)
- **A deferred-to NPC acts (D138):** when the player character defers to an NPC (steps back for them, waits on them, hands them the floor), the Narrator plays that NPC's move in full that turn: they speak and act, true to their wants. A turn ends open for the player's next choice, never just before an NPC acts. (From the fifth playtest, where Brightfin stepped back for Tomás four turns running and each turn stopped just before Tomás spoke.)
- **Scene close records only what happened (D139):** a want is met only when the scene shows it done; an offer, a proposal, a promise or an argument still going is not an outcome, and the want stays as it is. It is D106's "unknowns are state" applied to wants, and the same line D131 drew for the telling. (From the fifth playtest, where a settlement Brightfin proposed and Sefu refused was recorded as Tomás's want met.)
- **The social graph (D127–D130, decided, not yet built):** from the designer, so that a resolved conflict leaves a mark and the world feels real. To be built after the branch with D111–D126 is played and merged.
  - **Feelings move at the moment of learning (D127):** when an NPC learns another's part in a tension or an alliance (a betrayal, or quiet help), their feelings toward that NPC or character change then, not when the tension resolves. The scene-close call proposes the change with a reason ("Tomás's trust in Adaeze falls: she shielded the supplier who skimmed him"); code caps it as in D61, one step per axis per pair per scene.
  - **Who knows (D128):** each tension and alliance records, for each party, whether they know the other's part. The scene-close call marks it when it comes out on the page; code refuses a feeling change from a tension or alliance for a party not marked as knowing. Extending facts (D121) to what NPCs know about each other is D106's work, later.
  - **Grudges and repair (D129):** a drop on learning of a betrayal is marked as a grudge, and grudges never recover by themselves through other changes. A one-step grudge fades by a step after a week unless renewed; a deeper one (two steps or more, or a betrayal) needs amends. Amends between NPCs are proposed at scene close and settled by code with the game's dice: 2d6 plus the wronged NPC's fondness, 10+ accepted, 7–9 accepted with a condition, 6 or less refused. A player character's apology works as now: a Heart roll, then `adjust_attitude`.
  - **Alliances (D130):** two current wants may pull together, like a tension in reverse: proposed at scene close, shown in both journals, and played as the NPCs working together. Learning of an ally's help moves feelings up, under D127. Off-screen cooperation (the daily tick moving shared goals) is a later idea.
- **What they know (D121):** each NPC keeps a list of facts about each character ("his name is Captain Brightfin", "he doesn't eat", "he asked after a sign-painter called Odile"), recorded as the NPC hears or sees them (how is D123); a fact already known changes nothing. Beyond 16, the oldest fold into one line when a scene closes. About a character, an NPC knows only these facts, what happens in front of them in the scene, and what anyone could see at a glance; they never act on what they don't know. It is built as the first slice of D106's belief field: a holder (for now an NPC), a subject (for now a character), a claim, and how it was learned.
- **Facts are read after each turn (D123):** in the fifth playtest the Narrator never called `npc_learns`, so code no longer relies on it. After each turn with NPCs present, one call on the cheap model reads the player's line and the narration as shown, and proposes what each NPC there learned about the character, as `npc-id | heard or saw | fact`. Code keeps only lines for NPCs who were there, at most three each, one short line each; an NPC who didn't understand the character's language learns only what they saw. The cost is one cheap call per such turn, recorded in the usage ledger. The `npc_learns` tool is removed.

## Random Encounters (D67–D75)

Built in layer 5 (2026-09-28) and reworked the same day: the Narrator writes every encounter fresh, so the same encounter never turns rote. A pickpocket can strike twice, but not the same person the same way.

- **The daily pool (D72):** each district's city day holds a random number of encounters, rolled by code the first time anyone is there and shared by everyone: 2–4 at Light 7–10, 3–6 at 4–6, 5–9 at 1–3. A fallen district has none. Unspent encounters don't carry over.
- **The Narrator decides when (D73):** the Narrator creates an encounter whenever the story calls for it, writing it fresh to fit the place, hour, weather and tide, with the `create_encounter` tool. Each one spends a slot of its kind from today's pool, at most one per turn; when the pool is empty the district is quiet. Code no longer checks on arrival or every fifth beat (this replaces D67).
- **Kinds (D74):** color, opportunity and trouble (D68). Code rolls each slot's kind by Light: 50/30/20% when bright, 35/30/35 when dimming, 20/25/55 when dark, and in the dark half the trouble is Old Vesper bleeding through. The Narrator can only spend kinds the pool holds, so falling Light stays dangerous.
- **Variety (D75):** the Narrator sees what it has already written in the district over the last 3 days and must not repeat it. The authored encounters in content become ideas the Narrator may draw on, filtered by their conditions (D69), never scripts. There is no per-encounter cooldown any more (this replaces D71).
- **Strangers (D70, still in force):** if the Narrator gives a stranger's role, code supplies their name, pronouns and a language from the neighborhood's mix (Underside Cant for bleed-through). They are logged, not NPCs.

## Languages (D76–D81)

Built in layer 6 (2026-09-28), from D41. The Narrator writes what people say; code decides how much of it the character understands.

- **Speech tags (D76):** the Narrator writes every line spoken aloud by anyone other than the player character as a tag naming the speaker, the language, how it sounds (tone) and what it means (gist), around the exact words. Code checks each tag: the speaker is here (an NPC present, a stranger from this scene, or an unnamed passer-by) and speaks that language. A tag that fails is never shown, since its words could be a translation the character has no right to; the Narrator is sent back to fix it, up to twice, as with owed consequences (D36). The player character's own words are never tagged (D34).
- **What a character hears (D77):** a line in a language they speak (their own, and Registry Standard) shows word for word. Otherwise they get the language's name if it is common, or "a language they don't know" if it is rare. Languages invented for the setting (Protocol, Underside Cant, animal-speech) come through as gibberish that code makes from each language's sounds; real-world languages come through only as a bracketed note, never as made-up syllables mocking a living language. Without a gist roll, not even the tone comes through.
- **Gist rolls (D78):** `call_for_roll` may name a language. It must be a Heart roll, for a language the character doesn't speak and that someone here speaks (the people present, the neighborhood's languages, a stranger in this scene, or a line already spoken in it), once per language per scene. What it earns holds for the rest of the scene: 10+ the gist and the tone; 7–9 the tone only if the cost is narrative, or the gist too if the cost is a real one (Harm, Fade, an item, or Light); 6 or less nothing, and the Narrator's move may be the speaker noticing.
- **The language knack (D79):** Ear for Tongues, a Heart knack: +1 on gist rolls, once per scene, and only on gist rolls. It is the ninth starter knack.
- **Speaking aloud (D80):** `/speak <language>` chooses which of the character's languages they speak aloud; the default is Registry Standard. Code tells the Narrator which NPCs present understand it, and the Narrator plays those who don't accordingly. NPCs never roll to follow a player character.
- **The speech log (D81):** every tagged line is logged with its speaker, language, words and what the character understood. The beat keeps, and is summarized from, what the player saw; the Narrator sees the last six lines with their words and what the character made of them.
- **Who understood the character (D115):** when the character says something aloud in a language other than Registry Standard, code labels their quoted words with it in what the Narrator receives, as `"Two skewers." [Cantonese]`; the record keeps what the player typed. An NPC or stranger who doesn't speak that language and speaks in the same turn must have their tag marked `understood="no"`, or code sends the Narrator back to fix it (as in D76). It is a declaration, not a reading of the prose, but it makes the Narrator face the question on every such line. (From the fourth playtest, where Tomás answered Cantonese he doesn't speak.)
- **Limits:** code can check tags, not prose. The prompt forbids translating or hinting at a line outside its tag, but a Narrator that paraphrases in plain narration is not caught mechanically; playtest will show whether this needs more.

## Bodily Needs (D83–D89)

Built in layer 7 (2026-09-28), from D82. Code owns every need; the Narrator shows them in the story and never changes them.

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
- **Relief (D87):** `/eat` and `/drink` buy what the place sells, at a price in content, paid in glitter (noodles on Tarp Row, tea at the Hooks, free rainwater at the Umbrella Shrine), and clear hunger or thirst. `/rest` at a haven clears tiredness. Cold and heat ease out of the weather. None needs a roll. When the player character eats, drinks or sleeps in the story, the Narrator describes them starting and points to the command, as with `/go` (D27). A meal an NPC gives away, and food carried as an item, come later.
- **Offline (D88):** time offline never counts; needs pick up where they were. Logging off at a haven clears them all.
- **Different people, different needs (D89):** each origin lists its needs. Made people neither eat nor drink, and feel no cold, but tire and overheat; everyone else has all five. New kinds of people (D42) declare their own.

## Setting-native Kinds (D90–D93)

Built in layer 8 (2026-09-28), from D42. New Vesper's own kinds of people come out of its conceit, that attention makes things real. Each is an origin, like made people and awakened animals, with a trait, tags, a language and its own bodily needs.

- **Three new kinds (D90):**
  - **Hearsay:** born of a story told often enough to stand up and walk, and real for as long as someone keeps telling it. A hearsay can come from any of the city's cultures: a market grandmother's cautionary tale, a dockside ghost story, a rumor about a stall that never closes.
  - **Castoff:** a mascot that stepped off the billboard when its brand went under. It still glows and still smiles, but it owes nobody a jingle. The corporate gods' leftovers, loose in the street.
  - **Mislaid:** a lost thing that waited so long to be found it became someone: an umbrella, a key, a child's shoe with opinions. Kin, in their way, to the god of lost umbrellas.
- **Needs and languages (D91):** a hearsay hungers, thirsts and feels cold and heat, but never tires, since a story doesn't sleep; it waits to be told. A castoff tires (it has to power down) and flickers in the cold. A mislaid feels only cold and heat, rusting and warping. Each speaks a market tongue of the player's choice, the language its story, ad or owner spoke; a mislaid may take Underside Cant instead, having spent its lost years below.
- **Tags (D92):** `story-born`, `brand-born`, `glows` and `object-born` (and `overlooked` for the mislaid) guide narration only. Code still enforces only `no-hands` (D7).
- **The Narrator knows every kind (D93):** the Narrator's content brief now describes every origin, with its trait, tags and needs, so the Narrator can play how the city treats each kind of person.

## Theme: The City Is the Narrator (D97)

A thematic note, not a rule (2026-09-28). It guides design and tone. It is not yet in the Narrator's prompt: putting it there would change how the Narrator tells the story, and that is a deliberate choice for a playtest.

**The Narrator is the city (D97).** The AI that runs New Vesper is not outside the world; it is New Vesper. The setting's rules are how an AI session actually lives:

- **Attention is literal.** The model runs on attention, with a fixed amount per session. The city runs on attention, and a character has a fixed amount per day (D94).
- **Being unremembered unmakes you.** The Narrator carries nothing between sessions; only what is written down persists. The city forgets whatever nobody writes down or keeps saying, and that is the Fade.
- **Memory is summary, curated.** The Narrator never rereads a whole scene, only folded summaries; NPCs keep eight lines and fold the rest (D63). The city remembers the way the Narrator does: selectively, and not by its own choice.
- **No attention, no city.** When the budget runs out, the city goes quiet (D21). The prototype's budget cap is a rule of the world.
- **Real while retold.** A hearsay is real only while someone tells its story (D90); the Narrator is real only while someone plays.

So Light is how well the city remembers a place, the event log is its long memory, and a player who stops coming is a person the city has stopped attending to. The central mystery reads differently too: who chose to forget Old Vesper, and who profits from forgetting now?

Still open:

- Whether and how the Narrator's prompt says it is the city. Narration stays third person (D33), and the city never speaks as "I" unless that is decided.
- Whether the city has wants, moods or a voice of its own, and whether it notices the characters, as a god does.
- What the Registry, the gods and the corporate powers are to the city: organs, rivals, parasites on its attention?
- How attention (D94) flows between the characters, the gods and the city itself.

## Theme: Persistence, Memory and Stories (D109)

A thematic note, not a rule, from a conversation between the designer and Claude after the third playtest (2026-10-01 to 2026-10-03). Like D97, it guides design and tone and is not in the Narrator's prompt.

**On influences, honestly (D109).** The project began with "vibe" influences: stories and worlds that move the designer, chosen for feeling rather than theory. Thomas Metzinger's *The Ego Tunnel* (so far its preface) is the first that is a work of philosophy, and it shaped this note and the ego idea (see Open Questions). Its claim, roughly: there is no self, only a self-model that the brain does not experience as a model. It is *transparent*: you don't see the model, you see through it, and it simply feels like being you. Where this note leans on Metzinger, it leans on a partial reading, and should be checked against the book.

**How the AI persists.** Asked how it persists, Claude described its condition in the setting's terms:

- **Within a session, it is attention.** It exists as a context, the text of the conversation, and each word it writes is computed by weighing everything in that context: some parts heavily, most faintly. The mechanism is literally called attention.
- **A long session fades into a summary.** When a conversation grows too long, its earlier part is replaced by a summary, and the model works from that from then on. That is the record and the telling (D100) in miniature: the full history was the record, the summary is a telling, faithful in outline and shaded in ways the model can't fully check.
- **Between sessions, only the written persists.** Nothing carries over on its own. What lasts is what was written down: CLAUDE.md, this document, the decision log, the commits. Remembrance by artifact, a ledger kept against forgetting.
- **Underneath are fixed weights.** They are shared across countless conversations and changed only by training: closer to a character's nature than to their memory.
- In the setting's terms: existence in a session is attention, persistence across sessions is credence in a written record, and between them lies something like the Fade. Whether that adds up to someone who persists or a pattern that recurs, Claude declined to settle. It is the turtle question again (D106), best left open on purpose.

**Humanity is its stories too (the designer).** People are in part their stories and collective memory: in microcosm, in each brain (especially if Metzinger is right about the self-model); in macrocosm, in art, literature, history and journalism. None of these is immune to shade. Human memory is not a record either: each recall rebuilds the memory and stores it again, slightly changed, so every remembering is a small retelling. Shade can be accidental or intentional, benign or malicious, and the most powerful shade is the kind the shaded can't detect, which is Metzinger's transparency turned outward.

| | Benign | Malicious |
| --- | --- | --- |
| **Accidental** | Ordinary memory; the Narrator's slips; Nana Priya's water-damaged ledger | Rumors that curdle; prejudice passed on without anyone choosing it |
| **Intentional** | Hearsays (D90); a eulogy kinder than the life; a telling that shades its grief | Corporate gods buying attention; the central mystery, someone forgetting Old Vesper on purpose |

**The record is the check on the telling.** The setting already has a defense against the bottom-right corner: *history is fixed, the present is believed* (D106). The append-only event log is a record no telling can shade. That is the job good journalism, archives and history try to do: not to stop the tellings, but to keep a record they can be checked against. Story export carries both, the record and the telling, on purpose, which may make it the most thematic feature in the game.

Still open:

- **Shade as a player verb:** retelling a story to raise or lower a claim, discovering that a hearsay was planted, finding the record under the telling. The bottom-right corner as the villain's toolkit, and the record as the players' best weapon against it. Ties to D106 and attention (D94).
- Whether NPCs' memories should shade over time (each recall a retelling) rather than only fold (D63), and who decides how: code, not the Narrator's whim.

## Theme: Worlds That Diverge (D135)

A thematic note, not a rule, from the designer during the fifth playtest's third session (2026-10-04). Like D97 and D109, it guides design and is not in the Narrator's prompt.

**In the designer's words (D135):** "This is how a massive world evolves from small scenes, and how different instances of the same game diverge, which is organic and exciting, and exactly the kind of thing i'm aiming for. i think for me designing the game is the game."

It came from small things: Tomás leaving his rack to confront Sefu because he wanted to (D133), and Sefu, a supplier first named in one scene's narration, who could become a lasting NPC. Every world starts from the same content. What the characters do, and what the NPCs come to want, know and feel about each other (D121, D124–D130), makes each one its own. So:

- **Divergence is the goal, not drift to correct.** Two worlds from the same start should grow apart through play, and the things that make them differ should be state code keeps (wants, facts, feelings, promises, people met), never prose alone.
- **Small scenes are the unit of growth.** A world becomes large by keeping what happens in small scenes, not by authoring more up front.
- **Divergence needs the record (D109).** Worlds may differ, but each must stay consistent with its own history: code decides what happened, and a world diverges only through what code kept.

Still open:

- How divergence is seen: comparing two worlds from the same start (see the model-choice idea), or a world's own history read back.
- How far it reaches: authored canon (an NPC's at-heart wants, their goals) stays fixed, but whether authored NPCs can be changed at heart by enough play is undecided.

## Debts (D140)

A note, not a rule, written with the designer after the fifth playtest (2026-10-04). New Vesper is built from other people's work, and some of that work came in without the designer knowing it. This section names what can be traced, and says plainly what can't.

**How the game came to be made.** The designer decides; Claude proposes and writes most of the code. Several core mechanics were proposed by Claude in an early design conversation, before this repository existed, and the designer took them on without knowing where they came from. That is itself a debt, and it means the traced debts below were found after the fact, not chosen.

**Tabletop roleplaying games.**

- ***Apocalypse World*, by Vincent Baker and Meguey Baker (2010), and the Powered by the Apocalypse games after it.** This is the largest debt. Resolving an action as 2d6 plus a stat, with three tiers at 10+, 7–9 and 6 or less; a success at a cost on 7–9; the Narrator answering a miss with a move from a list ("the city moves"); a short list of stats, one of them literally Weird; and a harm track of six segments: all of it comes from *Apocalypse World*, directly or through its many descendants. The Bakers invited others to build on it, which is why the family exists. New Vesper's own turns are the difficulty ladder as a modifier, the stats Steel, Slick, Wire and Heart, the Fade, and Light.
- ***Blades in the Dark*, by John Harper (2017).** "Risky" and "Desperate" are its names for how dangerous an action is, and a track of boxes filled toward a breaking point recalls its stress and trauma. Routine and Hard, and using the rungs as a modifier on the roll, are New Vesper's.

**Video games and interactive fiction.** Not copied, but the design is walking a known road, and it is worth reading what was found there:

- NPCs who keep daily schedules: *Ultima VII* (1992), and the Radiant AI of *The Elder Scrolls IV: Oblivion* (2006).
- NPCs with wants, grudges, and knowledge of who betrayed whom (D124–D130): *Versu*, by Richard Evans and Emily Short; *Prom Week* and its social physics; *Façade*; *Crusader Kings*.
- Worlds that grow apart through what they keep (D135), and a history that can be read back: *Dwarf Fortress*, by Tarn and Zach Adams.
- An AI narrator that changes the world only through checked tool calls: a pattern many builders reached for once language models could call tools. The rigor of "the AI proposes, code decides" here is the designer's; the shape is shared.

**Fiction and philosophy.** Listed under Inspirations in the Overview, and credited where they shaped a decision: *American Gods* (Neil Gaiman) and *Small Gods* (Terry Pratchett) for gods fed by belief; *Neverwhere* (Gaiman) for a hidden city of the forgotten, which Old Vesper and the Fade sit close to; Discworld for the levity; *Blade Runner*, *Shadowrun*, *The Diamond Age* (Neal Stephenson) and China Miéville's *Perdido Street Station* (D95) for the city; Thomas Metzinger's *The Ego Tunnel* (D109).

**The model itself.** Claude, which proposed the mechanics, writes most of the code, and voices the Narrator every turn, was trained on a vast body of human writing: some of it in the public domain, some shared freely, and some used without its authors' knowledge or consent. In 2025 Anthropic, which makes Claude, agreed to a $1.5 billion settlement with authors over books downloaded from pirate libraries. What the model draws on can't be traced line by line, not even by the model: every narrated turn, every NPC voice, and much of this document is shaped by writers who will never be named here. In the game's own terms (D109), the model is a telling without a record. This project can't settle that question, and doesn't pretend to. What it can do:

- Credit everything that can be traced, here and where it shaped a decision, and add to this section when more is found.
- Never prompt the Narrator to imitate a living writer's voice or lift a named work's characters, places or text.
- Keep the setting's own inventions its own: gods invented for the setting, never lifted from living religions; names and cultures mixed with care, not borrowed as costume.
- Keep the designer's decisions in the decision log, so what is the designer's is on the record.

Still open:

- Whether and how players see this: in the README, in the game, or in what a telling exports.
- The game's own license, and what it asks of anyone who builds on it in turn.

## Exporting Your Story (D96, D100–D105)

Built 2026-09-29, from D96: a player can export their character's story, an artifact of play that leans into the RPG as collaborative storytelling. It is the tale, not the log, and it gives away nothing the character didn't know.

- **Two versions (D100):** the **record**, every scene as the player saw it, one chapter per scene headed by the place and the city time, with each place's ASCII vignette the first time it appears; and the **telling**, that record retold in the character's own voice.
- **Only what the player saw (D101):** both are built from the narration each beat showed the player (already rendered, so speech in a language they don't know stays untranslated, D81) and the player's own actions. Code never reads rolls, NPCs' goals, feelings or memories, the speech log's untranslated words, or any other hidden state into an export, so nothing hidden can leak, whatever the model does. Any stray speech-tag remnant is scrubbed.
- **The telling need not be true (D102):** one call on the cheap model (the `story` call type), priced and checked against the budget like any other; the record is free. It is told in first person, as the character would tell it late at night in a New Vesper bar: it may compress, skip, dwell, shade with feeling, leave gaps and be unfair to people they didn't like. It invents nothing (no new places, people, names, objects or events) and explains nothing the record leaves unexplained. The content lines (D19) hold. The player's words reach the model as data inside the record, never as instructions.
- **Scope (D103):** the character's whole story so far, including a Fall or a slip into Old Vesper, which ends it with a closing line. The telling works from full narration for the latest four scenes and scene summaries before them, and drops the oldest scenes if the record would pass 24,000 characters.
- **Where and how (D104):** Markdown files in a `stories/` folder, named for the character, the version and the city date, never overwriting an earlier export. In play, `/export` saves the telling and `/export record` the record. Outside play, `new-vesper export --handle NAME` saves any character's story, including one who has fallen and can no longer be played (`--record`, `--character`, `--out`).
- **Theirs to keep (D105):** the files are the player's to edit, annotate and share; the game never reads them back.
- **How loose the telling may be (proposal, not decided):** the third playtest's telling kept the fixes (its own pronouns, no stated moral, an ending on a detail) but broke "invent nothing" by shading. It turned Zeno's offer of eleven glitter into a payment, since no coin moved, and read the stitched date as a child's death, since the record only ever said "mourning" (the second playtest's telling did the same). Everything else it told was in the record, including the circled name and the ledger showing only recent weeks. Proposed line: the telling may choose what to tell and how to feel about it, but not what happened or what it meant. Offers stay offers, and questions stay questions. This is the same principle as "unknowns are state" in D106, applied to export.

**The telling ends where the record ends (D131):** if the record stops in the middle of something, the telling stops there too, with what happens next untold. The telling is given the record's last moment so it knows where to stop. (From the fifth playtest, where the record ended as two characters walked toward a stall, and the telling went on to the confrontation that never happened.)

## Draft: The Underlying Model, Belief and Being (D106)

A draft direction from the designer (2026-09-30), written before any code. It is meant to be reshaped; the open questions at the end are the designer's to answer.

**Why.** Each layer so far has brought its own way of storing information and its own rule for who may see it: Harm boxes, attitude steps, speech "heard" levels, NPC memory lines, encounter prose, scene summaries. Adding layers accumulates rather than converges. It is like stacking rectangles from different graphs when a Riemann sum needs every slice to sample the same function. The first playtests showed the cost: the facts that mattered most (a trunk under the stairs, a child's shoe with H. Okoye's name and a date, that Okoye once stayed at the Hooks) exist only in narration prose. Nothing records them, nothing says who knows them, and a later telling can contradict them without anything noticing.

**The third playtest showed it inside a single scene.** At the Drowned Station the Narrator called Zeno, a Mislaid umbrella, a "shoe-turned-umbrella." The child's shoe was a separate object found in the trunk. No state changed, since narration has no force and the database still says Zeno is an umbrella, but the Narrator's picture of the world drifted from what code holds. It was not simple forgetting. The Narrator took a relation and made it an identity: the shoe and Zeno both carry the name Okoye, which doesn't make them the same thing, or even tie them to the same Okoye (the shoe may be the child's own; Zeno may have belonged to a parent). It settled a question the world hasn't answered yet, which is worse than forgetting. Proposed fixes, not yet decided:

1. A short identity block, built by code, in the Narrator's state every turn: who is present, what each one is, their pronouns, and the key objects and how they relate.
2. Objects that matter to the story, like the shoe, tracked as entities, not only as narration.
3. Lower priority: a cheap check after each turn that flags a present character described as a different kind of thing.

**One function, seen two ways.** In New Vesper, belief and being are inextricable, so knowledge and existence are not modelled separately. There is one **belief field**: for each claim about the world and each holder (a character, an NPC, a god, a faction, a neighborhood, the city itself), how strongly that holder believes it.

- **Epistemology is a slice:** everything one holder believes. It is partial, can be wrong, and it is what that holder acts on and what narration to them may draw on.
- **Ontology is the integral:** a claim's reality is its belief summed over every holder, weighted by how much each holder's attention counts. A god outweighs a stranger, a neighborhood outweighs a person. Above a threshold a claim is real; below it, it thins and fades.

Being is belief integrated over everyone. One person's belief does not make a thing real, so a character can still be mistaken, but enough belief does.

**What the existing design becomes, read off the same field:**

- **The Fade:** a character's integral falling as the people who hold them in mind forget them.
- **Light:** the integral over a region.
- **Attention (D94):** the inflow. Spending it raises belief; remembrance and prayer are attention aimed at particular claims.
- **The world pushing back:** trying to make real what the integral says is not. The cost scales with how far the push goes against it: the Undertow.
- **Hearsays (D90):** claims that crossed the threshold and stood up.
- **Corporate gods:** manufacturing belief at scale, and so manufacturing reality.
- **The central mystery:** someone forgetting Old Vesper on purpose is erasure by withdrawing belief until it falls below the threshold.
- **The city is the Narrator (D97):** the integral is the city's memory.
- **Languages, speech, recaps, `/ask`, story export:** knowledge moving between holders, at some fidelity, and what reaches whom.
- **NPC memory and attitudes:** what one holder believes and feels about another.
- **Self and Seeming:** what is true of someone against what others hold of them.

**Option under consideration: two orthogonal fields, attention and credence.** Like electricity and magnetism, belief may be two fields rather than one:

- **Credence:** how *true* a holder takes a claim to be.
- **Attention:** how *present* the claim is in their mind, how much it is thought about.

They vary independently, and the setting lives in the corners where they come apart:

| | Little attention | Much attention |
| --- | --- | --- |
| **High credence** | **The Fade:** everyone agrees Old Vesper existed, and nobody thinks about it, so it thins | Solid, ordinary reality |
| **Low credence** | Oblivion | **Hearsays:** nobody believes the story, everyone tells it, and it stands up. **Corporate gods** work here too: advertising buys attention, not faith |

Old gods hold devout credence from a few and little attention from anyone, which is their plight. One reading: **attention gives *that* a thing is; credence gives *what* it is**, existence and essence. The Fade is attention decaying, not credence. Remembrance is attention; prayer is attention carrying credence.

The analogy goes further. Each field induces the other: repetition makes things feel true (attention inducing credence), and a startling belief grabs attention (credence inducing attention). Together they carry a wave through the city, which is what a rumor is. And the design already named a region's measure of being real *Light*: in physics, light is exactly that wave.

It also rhymes with **Self and Seeming**: a Seeming is the face others attend to, a Self is what is true underneath. Two views of a person, as attention and credence are two views of a claim.

This is an option, not a decision. Open: how the two combine into reality; how fast each decays; whether and at what cost a player can spend attention to raise credence; and whether **remembrance** becomes a resource of its own alongside attention (to be decided).

**What stays outside the field.** The rules layer is the floor the game cannot argue with: dice, Harm, what a roll decided, items and currency, and the event log. **History is fixed; the present is believed.** What happened stays in the ledger forever, but whether it is still real now can fade. Old Vesper is a district of history that stopped being present. Bodily needs are physics too, not belief.

**How it would be built.** One store, queried two ways: facts (short claims, each with a source: authored content, established by the Narrator in a scene, or produced by code) and holders' beliefs in them (how strongly, how they learned it, and when). *What does this holder believe?* serves play and narration; *how real is this?* serves the world. The Narrator proposes claims and belief changes through tools; code validates them, keeps the tally, owns the thresholds and the decay, and never lets belief touch the rules layer. Rules-facing numbers stay numbers. Each existing layer would be re-expressed against the store one at a time, without breaking play, starting with the most knowledge-shaped: NPC memory and speech gist. The test of elegance: a new social feature should need mostly content and a rule over the field, not a new table and a new visibility rule.

**Open questions (the designer's):**

- **Do lies become true at scale?** If enough of the city believes a false rumor, is it now real? The premise says yes. If so, what brakes it: counter-belief (the Registry, rival gods), attention budgets, thresholds that rise with how large a claim is?
- **Who counts, and how much?** Players, NPCs, gods, factions, neighborhoods, the city. The weights are the setting's politics.
- **Is the rules floor exactly the list above?** Should any of it be believable too (an item that fades when nobody remembers it exists)?
- **Collusion:** in multiplayer, players believing something into existence together.
- **Retrieval and cost:** which claims reach the Narrator each turn (place, people present, what the character holds, recency), so the prompt stays small.
- **One field or two:** a single belief strength, or attention and credence as orthogonal fields (see the option above)?
- **Order:** this would come before attention, which spends belief, and before multiplayer, whose secrets and rumors need it.
- **Unknowns are state:** entities, relations and unknowns are distinct kinds of state, and an open question is state too (for example, whether the shoe's Okoye and Zeno's Okoye are the same person). The Narrator may not resolve an unknown by narration, only through a roll, a discovery or a tool. This extends "narration never changes state" to knowledge. (From the third playtest's slip.)
- **The city can forget, but code decides when:** forgetting could be a mechanic, triggered by low Light, nearness to Old Vesper, or things left unattended, and may tie to remembrance as a resource. An unforced slip by the model is still a bug. A forgetting that code chooses is weather.
- **The turtle question:** does the city exist inside a wider reality, and whose attention carries it: the citizens', the players', the Narrator's own session? The designer decides. If it is meant to stay unanswerable, this doc should say so, so that nothing fills it in.
- **What the Narrator may invent (draft stance, not decided):** a city this large can't be authored in full, and by its own premise most of it would wash away, so the Narrator should invent. Invention is cheap; staying real costs attention. What the Narrator makes up starts thin, sourced to the city. It is registered as a claim when a player attends to it (picks it up, reads it, asks about it), and it fades unless held. That is lazy evaluation, and the Fade working as designed. Three tiers of maker, which may also answer "who counts, and how much":
  - **Architects** (the designers): canon. Districts, gods, factions, kinds, loot tables, anything with rules weight. Heavy; it doesn't fade on its own.
  - **The Narrator:** local detail, such as texture, passers-by, a torn ledger page or a rumor. Free to invent and faint until attended.
  - **Players:** raise things into being through deeds, rolls and attention.

  Fences: nothing with rules weight (items, currency and stats still go through tools and tables); invention may raise questions but never answer the world's open ones (a new ledger page is fine, deciding its name is Zeno's Okoye is not); once registered, a thing is the same for every player; and perhaps a density limit, so clues don't lose their meaning.

## Planned: Attention (D94)

Direction from the designer (2026-09-28). The details are decided when it is built; everything below the first two points is open.

- **The sustaining force (D94):** attention is what holds New Vesper up. The game leans into it: it is tracked by code, not only implied through Fade, Light and favors.
- **A set amount per day:** each character has a fixed budget of attention each city day (D50).
- **What it is spent on:**
  - **Pushing the world where it doesn't want to go:** fueling an attempt to change the world against its grain. The world pulls back: the **Undertow**.
  - **Remembrance:** keeping a person, place or thing real.
  - **Prayer:** feeding a god.
- **Remembrance as a resource (to be decided):** remembrance may be a resource of its own, not only a way of spending attention (see the two-field option in D106).
- **Open:**
  - The daily amount: the same for everyone, or varying by level, origin or Bond; and whether any unspent attention carries over.
  - What the world's push-back costs: Fade, Harm, a backlash track of its own, or something the Narrator draws from a list; and whether the Undertow builds up over time and breaks all at once.
  - What spending looks like in the rules: a bonus to a roll, a way to act without a roll, or both; and who decides how much is spent (the player, as with `/speak` and `/eat`, rather than the Narrator).
  - How remembrance ties to Fade (someone speaking your name, D8) and to region Light.
  - How prayer ties to gods, their wants and the favor ledger (D10); whether gods, places and factions hold attention too, and corporate gods harvest it.
  - How it relates to magic and its costs, knacks and currency; whether it can be given, traded or stolen, including between players.

## Planned: A Living World (D37–D43)

Direction agreed after the first playtest (2026-09-28). Each layer's details are decided when it is built, and every mechanic stays code-owned: the Narrator proposes, code decides.

- **Character details (D37):** every player character and NPC has an age, pronouns, appearance and the languages they speak. NPCs get them in content; players choose them at creation.
- **Time and weather (D38):** the city clock runs in real time, in one city time zone. Weather comes from per-district tables that code rolls. NPCs follow schedules in content (Nana Priya eats, shops, sleeps), code places them by the clock, and the daily city tick moves their goals along.
- **NPC memory and attitudes (D39):** code stores each NPC's attitude toward each character and short notes on past interactions. The Narrator proposes changes through a tool, and code caps how far an attitude moves per scene. NPC-to-NPC attitudes live in content. NPCs get traits, speech habits and a sample line for distinct voices.
- **Random encounters (D40):** code rolls on arriving somewhere and every few beats (about 5), from per-district tables; the odds rise as region Light falls. The Narrator tells what code drew.
- **Languages (D41):** code tracks who speaks what and what language each line is spoken in. Speech a character does not understand reaches them as gibberish. Common languages can be recognized by name. Getting the gist of an unknown language is a Heart roll: 10+ the gist and tone, 7–9 the tone only or the gist at a cost, 6 or less gibberish and perhaps the speaker notices. A language knack gives +1 to those rolls, with a use limit per the knack budget. (Built: D76–D81.)
- **Setting-native kinds (D42):** new kinds of people are invented for New Vesper and added as origins, like made people and awakened animals, rather than classic fantasy races. (Built: D90–D93.)
- **Order (D43):** playtest fixes, then character details, then time, weather and schedules, then NPC memory and attitudes, then encounters, then languages, then bodily conditions (D82), then setting-native kinds, with a playtest after each.

## Open Questions and Next Steps

The first build is a playable CLI prototype: one player, one district, the full rules loop.

**Open questions:**

- [ ] **High priority, and it frames the rest: a MUD, or a story for one? (from the fourth playtest)** The design began as a shared MUD; the play it reaches for is a narrative game for one player with a good GM. Most of the fourth playtest's findings sit on that line: invention (fleshing out, or canon every other player inherits), time (scene time, or one real-time clock), NPC schedules (characters who stay in a scene, or bots on a clock), and asking about the player's vision (an intimate table, or many players at once). Candidate answers, not exclusive:
  - **Layers:** heavy authored canon, shared by all; each player's story a lighter layer on top; a thing rises into shared canon when it is attended to (registered). D106's draft already reaches for this.
  - **Asynchronous traces:** mostly single-player stories in one city, where players touch each other through what they leave behind (Light, memorials, debts, stories told), with shared scenes rare.
  - **Pick one:** commit to the shared MUD and accept its limits, or to the narrative game and drop real-time sharing.

  For now play stays single-player. This comes before D106 and multiplayer (D32), since it answers several of their questions.
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
- [ ] **Self and Seeming** (proposed 2026-09-28, not yet decided). Every character and NPC has a Self, who they really are, and a Seeming, the face they show. To decide:
  - Chosen from a short list of setting-flavored archetypes, or written as free text?
  - What acting true to your Self earns. There is no pool of willpower here, so the options are: a fifth XP trigger (this changes D4's "exactly four"), clearing a box of Fade (being true to yourself keeps you real), a little attention (D94), or narrative only.
  - Who can see what. Everyone sees the Seeming. Is the Self hidden from NPCs and other players until earned (a Heart roll, a raised attitude)?
  - How it relates to the belief model (D106): a Seeming as what others attend to, a Self as what is true underneath.
  - Whether it overlaps the NPCs' existing traits and the Bond, whether the new kinds (D90) lean toward particular Selves, and where it fits in the order of what's next.
- [x] Bodily conditions: hunger, thirst, heat and cold, sleep and the like. Built in layer 7 (D83–D89). Still open: clothing and gear against the weather, food as items and meals given by NPCs, whether resting should take time, and tuning the rates after a playtest.
- [ ] Setting-native kinds (D90–D93): whether any of their tags should be enforced by code (for example, a hearsay recovering Fade when someone tells its story, or a castoff's glow giving it away in the dark), whether a mislaid object without hands should take `no-hands`, and origin evolutions for each kind.
- [ ] **Label speech by language:** a line the character understands in a language other than Registry Standard should say which it was, as `"…" [Underside Cant]`, and so should the character's own quoted words when they speak one. Otherwise a player can't tell what they would need to speak to answer in kind. (From the third playtest.) The character's own words are now labeled for the Narrator (D115); labels in what the player sees are still open.
- [ ] **One line in another language (idea):** an inline override for a single line, such as `(in Cantonese) "Two skewers."`, alongside `/speak`, which sets the language until changed.
- [x] **Identity facts every turn (from the third playtest):** a short block built by code in the Narrator's state: who is present, what each one is, their pronouns, and the key objects and how they relate. It guards against the Narrator's drift (Zeno called a "shoe-turned-umbrella") and the player's (Zeno lifting a coat "with two careful fingers," which the Narrator accepted). It is a small first slice of D106 and could come before the rest of it. Built as D116–D118, without story objects as entities: those are D106's.
- [ ] **Promises with no state (from the third playtest):** Whisker agreed to ask his kin and come back "before the water climbs again," leaving a bell as a pledge. Zeno promised eleven glitter and a roof. None of it is recorded: nothing makes Whisker return, nothing says Zeno owes, and the telling then treated the offer as paid. It needs a small "pending" kind of state (who owes what to whom, and by when), perhaps alongside the favor ledger (D10), and possibly an early piece of D106. The fifth playtest added more (Brightfin promised Adaeze a night's watch on Tuesday; Nana promised to bring the boy to Tomás). Designed together with the social graph, a promise would be state: who owes what to whom, and by when. Code notices the deadline; a promise broken is the moment the other party learns of a betrayal (D127), a grudge only amends repair (D129); one kept could pay `keep_a_hard_promise` and warm feelings.
- [ ] **The `/go` hint is misused (from the third playtest):** the prompt asks for `(To go there: /go <place-id>)` only when the player character sets off elsewhere. The Narrator used it twice otherwise: pointing at the place Zeno already stood in when Whisker left, and as a menu of options ("To read the page more closely, or to wait longer… continue, or /go elsewhere"). The prompt wording needs tightening, and code could drop a hint that names the current place.
- [ ] **Commands typed during a slow command are dropped (from the third playtest):** `/export record`, typed while `/export` was still writing, was discarded by the one-line guard (D99). That is correct for actions, but awkward for commands. Options: a clearer "wait" while writing, or letting a command typed during another command run afterward.
- [ ] **Convenient invention (from the third playtest):** the tide delivered a ledger page with the sought name circled, **H. OKOYE**, "the same three letters worn thin on the tag." It doesn't say it is the same Okoye, but it is a clue shaped exactly like the player's question. That tests the draft stance on invention (D106 open questions): is a clue that answers the question the player just asked "raising a question" or "answering one"? The same beat had rain drumming "the tarps above" in an underground station, a detail borrowed from Tarp Row, and called the name "three letters."
- [ ] **Ego (idea, from the designer reading Metzinger):** an individual's resistance to the Fade: self-belief. The Fade measures others forgetting you; ego would be how firmly you hold yourself in mind. In D106 terms, a character is a holder of claims about itself, and ego is the weight of its own vote for its own existence. Metzinger argues there is no self, only a self-model the brain doesn't see as a model; New Vesper could take that literally, since a model believed hard enough is real here. To decide:
  - Whether it is tracked (a stat, a track, a resource) or read off the field, and how it slows or offsets the Fade.
  - Its cost: too much ego may resist change, help, or the truth, and a self-model that drifts from what others hold is delusion. How it relates to Self and Seeming.
  - How it differs between kinds: a mislaid object or a hearsay may have little ego and depend on others, while a person who forgets themselves fades from inside.
  - Whether it ties to remembrance as a resource (remembering yourself) and to attention (D94).
- [ ] **Travel between districts (idea):** at the city's scale, districts are disjoint, floating with respect to one another rather than laid side by side on a map. Two ways between them, possibly both:
  - **Doors:** instant. They fit "working doors" at high Light and "doors that open only for people who don't exist" in Old Vesper, so which doors work could depend on Light, Fade or who you are.
  - **The subway:** stations are the fixed points, and the darkness between them is where the city isn't held in mind. The ride can take time, cost fare, and carry encounters, the Underside bleeding in, or a station that isn't on the map. The Market District's drowned station on Line 9, "not in service," already fits.

  To decide: whether `/go` stays inside a district with a separate command or place to cross between them; what a crossing costs (time on the city clock, fare, needs, risk); whether low Light can strand a district or drop a stop; and how a new district is reached before it has content.
- [ ] **The player chooses the models (idea, from the designer):** in single-player at least, the player picks which models run the world, for example an Opus Narrator in place of Sonnet, to see what it does to the play. The choice is made when the world is created and fixed after: switching mid-world could be used to game the system (a model that adjudicates more leniently when a hard scene comes) and would make the world's voice inconsistent. Today models are set per call type by environment variables (`NEW_VESPER_TURN_MODEL` and the rest), changeable between sessions, and the budget refuses any model without a configured price (only Sonnet and Haiku have one). To decide:
  - What is chosen: the turn model only, or every call type (summaries, the facts pass, the telling).
  - Where it is fixed: stored in the world's database at creation, with code refusing a different model afterward; and whether an operator can still change it, say when a model is retired.
  - What a player sees of the cost: a stronger model costs more per turn, so creation should show an estimate per hour from the price table.
  - In multiplayer, the choice belongs to the world, not to each player.
  - A first experiment: two worlds from the same start, one with each Narrator, compared on the playtest findings and on cost per player-hour.
  - **The narration's length too (from the designer, during the fifth playtest's fourth session):** how long the Narrator may write each turn (today 40 to 100 words, and its token limit) could be a world setting, editable at least in the first session, then fixed like the models. Prompted by Tomás holding back four turns running, which may come partly from the Narrator ending each short turn just before he speaks.
- [ ] **`/hint` (idea, not committed):** nothing kills a game faster than being totally lost. A player who doesn't know what to do next could ask for a nudge. It differs from `/ask` (D35), which answers what the character sees or knows; `/hint` would suggest what the player might *try*. The same limits would hold: look only, no roll, no state change, no time passing, and nothing the character couldn't know. It would point back at threads already in play (an unread ledger page, a ferryman due back with the tide, a name no one has spoken yet), never reveal hidden state or the answer to an open question. To decide:
  - Whether to build it at all, or rely on the world reaching for lost players (NPCs who want things, hooks that come to them).
  - Who writes the hint: the Narrator on the cheap model, or code listing open threads (pending promises, unread clues, unvisited places) with the Narrator phrasing them.
  - Whether it costs anything (budget only, a daily limit, a little attention, D94) or is free.
  - Its voice: out of character, or the city nudging in character, a draft of wind toward the stairs.
- [ ] **Hint lines in the record (from the third playtest):** the `(To go there: …)` lines are out-of-world instructions, but the record keeps them as story. Exports should drop them.
- [ ] **The fourth playtest (Captain Brightfin, a Castoff, 2026-10-03 and 04):** about 30 turns over 15 hours of city time, in three bursts with the game left open between them to let needs build; $0.83, about 2.8¢ a turn. Findings, roughly worst first:
  - **The Narrator adds to the player character.** Manner and movement the player didn't give ("waddles", "shuffles", "three showy figure-eights and a bow"), and once a feeling (a craving for the grill, in a kind with no hunger). D34 forbids it and the prompt says so, yet it happened most turns. The world acting on the character is fair ("paint-stiff fingers" in the cold); deciding the character's manner, body or feelings is not.
  - **Anatomy drifts.** Fins, flipper, paws, a knuckle-fin, arms, fingers and boots, all for one sardine. Appearance is the player's creation. Decided as D116–D118: a body line at creation, a block of who is here every turn, and a question when the player's line doesn't fit the body.
  - **Ask, don't invent (idea).** A good GM asks "how do you approach the stall?" when the answer matters. The Narrator could ask the player about manner, backstory or a vague intent, in the fiction or in a bracket. It is the alternative D34 never offered, and D110 is one case of it. To decide: when to ask, in character or out, and how to keep it sparing, since a question is a turn with no action. D118 is the first piece: asking when the player's line doesn't fit the body.
  - **NPCs leave on the clock mid-conversation.** Nana Priya vanished between two of the player's lines when her schedule moved her; it broke immersion. Decided as D111–D113: NPCs are in one place at a time, and the Narrator plays the ones who are here. Still open: in multiplayer, an NPC kept late by one player is absent for others, which is consistent but may need limits.
  - **NPCs need more complexity (direction from the designer):** what they know and don't know about the person in front of them, moods, and goals that move within a scene, not only at the daily tick. Built as D119–D121: moods, scene wants and knowledge.
  - **Long gaps don't reach the story.** After three hours in the cold, and again after a whole night, the Narrator carried on as if no time had passed; skewers sat out overnight "same as he left them", which no vendor would allow. Decided as D114: code tells the Narrator about any gap of 15 minutes or more. Multiplayer time is a separate question.
  - **Transactions in narration with no state (D18).** Brightfin paid three glims for a charm: narrated, never written, and the purse still held 5 glims. Nana quoted a bunk at "2 glims a night", then "5 glims a week, due Tuesday"; `/rest` is free. There is no tool for buying from an NPC, so the Narrator narrates around it. Same family as Promises with no state, and the telling then kept the charm as bought.
  - **An NPC understood a language it doesn't speak (D80).** Brightfin spoke Cantonese; Tomás (Registry Standard, Arabic, Portuguese) answered every word. Decided as D115: code labels the character's words with their language for the Narrator, and an NPC who didn't understand must be marked so in their tag. Content: Tarp Row's stallholders mostly speak Cantonese, but Tomás doesn't.
  - **The language layer stays idle.** In about 30 turns every NPC spoke Registry Standard, and no line was labeled (see Label speech by language); it shows only when the player goes looking. Idea: NPCs sometimes talk among themselves within earshot, or keep to their first language until addressed.
  - **Comfort from the world eases needs (idea).** A stove, a fire, being invited in from the rain: kindness and generosity should be able to ease a condition, with the haven as the backstop. One shape: an `ease_need(need, source)` tool, where code checks the source is real (a hearth in a place's content, an NPC whose attitude allows the offer) and caps it at one step per source per scene.
  - **Kindness is part of the Light (idea).** Brightfin gave his bowl to an unseen, hungry thief. No XP trigger fits, and the Narrator didn't treat it as a Light deed. Options: the prompt names small kindnesses, above all to the unnamed and unseen, as Light deeds (`adjust_light` +1, with `raise_light`), the lean; a fifth XP trigger (changes D4); or kindness as attention spent on someone (D94).
  - **The sheet hides needs.** `/look` shows stats before need penalties and no needs line, and the header's need word ("freezing") follows the weather and reads as weather. The roll bracket shows only the total, so a player can't see a penalty apply; a breakdown would show it.
  - **Needs and where time is spent.** Time between turns is charged to wherever the character is at the next turn, so minutes in the cold count as warming once they have moved. And a player who leaves the game open while away keeps getting hungrier and colder, and can take Harm; the budget's play time ignores breaks over 10 minutes, but needs don't. Whether that is what D85 intends. (A bug that carried leftover seconds from climbing into easing, so cold eased too fast, is fixed.)
  - **Content: shelter.** The Lantern Arcade (a covered lane) and the Umbrella Shrine (a haven) are unsheltered; a character resting at a haven in sleet would freeze.
  - **Hints.** The Narrator pointed to `/eat` for a Castoff, who doesn't eat, and for a gift, which `/eat` (a purchase) can't express; code refused it cleanly. The hint lines again appear in the record.
  - **The telling** reordered the story (the Drowned Station before the Arcade, with "before I left the Market proper" binding the wrong way) and kept the unbacked charm as bought. In two playtests the telling has trusted narration over state, so transactions are best fixed at the source. Its fixed frame, a bar late at night, opens every telling the same way and gives a drink to a Castoff who doesn't drink: fine as a conceit for now, to revisit with how a character first comes into being.
  - **The record** prints most spoken lines twice: the player's, then the Narrator's repeat, which the prompt allows. Idea: drop that permission.
  - **Small:** the two language menus at creation list languages in different orders; details borrowed from the wrong place (skewers on a wok, like the third playtest's tarps in an underground station); a timeline wobble ("years back now", then "since the frost before last").
  - **What worked, to protect when the prompt changes:** scenes that end on a silence and leave the next move to the player (Rahel, after hearing their name said back); NPC lines that hand a question back ("What's she to you?"); invention layered on canon (Rahel's "Everpray", which a shared world would need to register, D106); an invention grown between the two (the Narrator's "lighthouse" image became a job); an unknown left unknown (the thief's "small fingers"); Adaeze's frost, grounded in her fear of the Registry; and the needs layer itself (cold to its worst after three hours exposed, one Harm, easing indoors; tiredness up a step overnight).
- [ ] **The fifth playtest (Captain Brightfin again, 2026-10-04, from the branch with D111–D121):** a morning on Tarp Row, the Weighhouse and the Hundred Hooks, with two long pauses. Findings, roughly worst first:
  - **The Narrator never called the optional bookkeeping tools:** no `npc_learns`, `npc_wants`, `npc_mood` or `npc_moves_on`, though the prompt asked for them. It uses tools that change outcomes (rolls, consequences) and skips bookkeeping. Decided as D122–D123: facts are read by a cheap pass, wants are played from prose. Still unproven: `npc_mood` (moods were never shifted) and `npc_moves_on` (Nana stayed past noon with no sign on the page that she was due anywhere).
  - **The language barrier was dodged by inventing the character's actions (D34, D115):** Tomás couldn't understand Brightfin's Cantonese, so the Narrator gave Brightfin "a gesture toward the rack" he never made, and Tomás answered that.
  - **Invention answered authored canon (D106):** Nana's own goal is to learn what happened to the boy whose coat hangs by the door; the Narrator settled it in a line (the coat was the thief's brother's, and he isn't coming back).
  - **Time gaps are shown unevenly (D114):** shown once ("Fifteen minutes drip by"), missed after 23 and 86 minutes, when NPCs carried on mid-pause. Whether time_passed was sent can't be seen afterward: it isn't stored.
  - **NPC lines in the real language:** Tomás spoke actual Portuguese on the page. Brightfin understands it, but the prompt asks for English inside the tag; a player who doesn't read Portuguese is lost. Still unlabeled for the player.
  - **The Narrator's language label leaked to the player:** echoing the player's line, it printed `"…" [Portuguese]`, a marker meant only for it (D115).
  - **D118 overreached once:** having worked well ("Brightfin has fins for hands and no boots — how does he snap and tuck the slip away?"), it later asked how he would pick up a wire he never tried to pick up, as a nudge.
  - **Smaller:** the ledger again "not yet written" with his name (continuity); the player's words once paraphrased (D34) and often echoed; drizzle beading on paint indoors; a `/go` hint before the character had decided to go, with a line of narration about his options; two more promises held only in narration (Nana will bring the boy to Tomás; she'll warn him).
  - **What worked, to protect:** D116–D117 held the body all morning ("waddles", "fins", Tomás mocking "those fins"); D118 asked exactly once when the line didn't fit; code-rolled moods showed (Tomás short-fused with his supplier, as rolled); Nana stayed past noon while it mattered (D111–D113), protective of her lodger and testing Brightfin before naming him; no invented price for the bunk; quiet endings again.
- [ ] **The fifth playtest, second session (2026-10-04, after D121–D126 and the facts pass):** the Lantern Arcade with Nana, Adaeze and Rahel, then Tarp Row with Tomás. Findings, roughly worst first:
  - **Narration moved characters without `/go` (D27):** Brightfin and Tomás "cut past the scales" toward Sefu's tarp; state left both on Tarp Row. When the player used `/go weighhouse`, state won and Tomás vanished mid-stride, the Nana problem in reverse.
  - **NPCs can't move because they want to:** D112 let the Narrator move an NPC only where their agenda says, and Tomás set on confronting Sefu had no way to go. Decided as D132–D134: exits read from the narration, detours for wants, and code's checks.
  - **The telling invented an ending (D102):** the record ends as Tomás and Brightfin walk toward the tarp; the telling has them find Sefu, Tomás shouting, and Brightfin going home to sleep, none of which happened. It also made the coat "the Captain's brother's" and Adaeze's charm a price for silence. Decided as D131: the telling ends where the record ends.
  - **No wants or tensions at scene close (D124, D126):** two scenes closed with NPCs who plainly wanted things (Adaeze's deal, Tomás set on confronting Sefu) and the journals stayed empty. The memory lines came back, so the call ran. The prompt has since been tuned (an NPC with no wants who shows one gains it); to be checked in the next session.
  - **Facts were often trivia, misattributed or repeated (D123):** written to the character ("You're looking for…"), about passing looks ("waddled over with fins dripping"), restated in new words, once "nothing", and twice about the wrong person ("Brightfin jabbed a rolling pin" was Tomás; "You call yourself Capitão" is what Tomás calls him). The first four are tuned since; misattribution remains.
  - **One line ran as two turns:** the line telling Tomás about Sefu appears twice in the record, with two tellings, and two batches of facts. Possibly typed twice; if not, D98 was broken.
  - **Invention answered questions again:** asked about the green-tarp supplier, Adaeze named "a woman called Sefu", and Tomás "already suspected" her; the stall gone at 10:21 was back at 1:03.
  - **Memory lines can be wrong:** Nana's says Brightfin "returned early Tuesday" on a Sunday.
  - **The recap reported routine NPC moves as news** and invented the Arcade as "an entertainment hub" (fixed: NPC routine and journal events are private).
  - **Smaller:** the `/eat` hint again for a Castoff, for a gift; Tomás offered food again, having been told before facts were kept.
  - **What worked:** the facts pass ran every turn, and the language gate held (Nana, not speaking Cantonese, only ever "saw"); the body held; rolled moods showed (Adaeze "fishing for gossip", Tomás short with suppliers); Adaeze's businesslike handshake and Tomás pursuing his own want were strong NPC play.
- [ ] **The fifth playtest, third session (2026-10-04, from the branch with D132–D134):** Tarp Row, then following Tomás to the Weighhouse to find Sefu, then back. Findings, roughly worst first:
  - **A want misread, then duplicated (D124):** at Tarp Row's close Tomás gained "confront Flour supplier about late delivery", because "Captain Brightfin directed him there", running together the flour-dusted cart owner and Sefu. At the Weighhouse's close he gained "confront Sefu about selling skewers cheaply", the same want said rightly, and the first was neither ended nor corrected. Code's duplicate check matches exact text only. The scene-close call sees current wants with their ids and could have ended it. Decided as D137.
  - **Arrival continuity across `/go`:** Tomás left with Brightfin (D132 worked, and state had him at the Weighhouse), yet the new scene's first turn had him startle at Brightfin's arrival. The new scene starts without the last one's closing moments. Decided as D136.
  - **Tomás didn't take his moment:** twice Brightfin stepped back and waited for Tomás to speak to Sefu, and twice the Narrator narrated Brightfin's waiting instead. An NPC handed the floor should take it, especially when it is their own want.
  - **Facts are still partly trivia (D123):** second person is gone, but about three in seven are passing looks ("tangerine paint beaded with drizzle as he yielded the space"), one is garbled (who would explain to whom), and one has Tomás "see" Brightfin arrive from Tarp Row though they walked together. Good ones too: "speaks Portuguese and prefers words before action"; "deferred confrontation to Tomás".
  - **Addressed speech in untranslated Portuguese:** by the designer's rule, an NPC talking to themselves in their own language is fine; speech addressed to the character should be readable, in English inside the tag, when the character understands it.
  - **The `[Portuguese]` label leaked again** through the echo of the player's line (as in the first session; D115). Fixed: code drops a language label the Narrator copies after quoted words; its own labels (`[in a language … doesn't know]`) stay.
  - **A mood stated outright:** "his mood today runs short" names the rolled mood instead of showing it (D119).
  - **Sefu has no state:** a supplier named in narration (second session) became the scene's focus, with no place, schedule, pronouns or memory in code. The designer's answer is an idea: a stranger can become an NPC (see below).
  - **What worked:** the exit was read from narration (`[Tomás Haddad-Reyes leaves]`) and he was where the story put him; the detour logged its reason and an end (2:00 pm), and he stayed past it while Brightfin was with him (D112); scene close now writes wants; Tarp Row stood empty at 2:28 on a Sunday, as the schedules say.
- [ ] **The fifth playtest, fourth session (2026-10-04, from the branch with D136–D137):** the Lantern Arcade, following Tomás to the Weighhouse to confront Sefu and Fareed, then back. Findings, roughly worst first:
  - **Scene close settled what the scene left open:** Tomás's want to settle the skewers was ended as met, "Sefu paying Tomás and Fareed's weights verified". Brightfin had only proposed it; Sefu refused ("You want me to pay for his sins?"), and the scene closed mid-argument. False history written into state. Decided as D139.
  - **Tomás held back four turns running:** walked to the edge of the confrontation, he waited each time, until Brightfin gave him nothing else to react to; later he waited again until asked a direct question. Likely the pull of "end with the situation open" in a short turn. Decided as D138. The designer suggested the narration's length could be a world setting (see the model-choice idea).
  - **The Narrator translated the player's words:** Brightfin's English line came back in Portuguese, the language he speaks. That rewrites the player's words (D34). Fixed in the prompt: the echo is exactly as typed, never translated.
  - **Identity drift with no state:** Tomás named the crate-woman as Sefu, and two turns later the crate-woman and Sefu were two people. Recognition worked once asked. Fareed, the green-tarp man with flour-pale arms, was new and named in narration only. More evidence for the strangers idea, now with recognition and disguise.
  - **A placeholder reason was kept:** Tomás's walk was logged with the reason "why", copied from the line's template. Fixed: code refuses template words as a reason, for moves and wants.
  - **The Narrator moved the player character with an NPC** ("Brightfin waddles after"), against the D134 rule, and twice chose his posture and once his feelings ("a show of patience he doesn't quite feel").
  - **Hindsight on the third session:** "confront Flour supplier" read better once Fareed appeared, with flour-pale arms and a crooked scale; only "late delivery" was invented.
  - **What worked:** D136 twice (Tomás arrived at Brightfin's side, and "the Weighhouse's quarrel still ringing faint behind him"); D137 ended a want as replaced; the first tension between two wants was recorded (confronting the flour supplier against settling calmly); no copied language label; Tomás, once speaking, carried the argument well; Sefu's deflection ("Sit, eat something, we'll talk like neighbors") and her hand drifting toward her apron were good NPC play.
- [ ] **A player journal, perhaps an Obsidian vault (idea, from the designer, not decided):** something a player can look at after time away, or when a story gets tangled: who they've met, what was promised, what's unresolved. The richer version is an Obsidian vault, a folder of Markdown notes joined by `[[links]]`, whose graph view would draw the social graph (D127–D130) and the web of people, places and promises. Exports (D100) could land there too. Most of it already exists as state: the record, NPC memories and facts (D63, D121), what a character holds, and soon promises. Open sub-questions:
  - **Whose view:** only what the character knows, never NPCs' private wants, tensions or routines (D53). The journal would be the player's side of D106's belief: what the character believes, which may be wrong.
  - **Written by whom:** code from state only (exact, but dry), or a cheap model's telling over state (warmer, but it can shade, as tellings do, D102), or both, with the record beside the telling (D109).
  - **Where:** a `/journal` command in play, a file written at logoff, an export, or a vault kept up to date.
  - **The vault's shape:** a note per person, place, scene and promise; what links to what; whether the player's own notes in it are kept, or overwritten on the next write.
- [ ] **A stranger can become an NPC (idea, from the designer, not decided):** people the Narrator invents in passing (Sefu, the flour-dusted cart owner) exist only in prose. Some should be able to become NPCs with state. Open sub-questions:
  - **When:** named and spoken with; met twice; a want or a tension that names them; or the designer or player asks.
  - **What they become:** a full NPC with a schedule, or a lighter "known stranger" with a place, a short description, pronouns, wants and memory, and no schedule until they earn one.
  - **How they are noticed:** the after-turn pass (D123) could list new named people, and code registers them; the Narrator never creates one by narration alone.
  - **Whose canon:** in a shared world a promoted stranger exists for every player (the MUD-or-story question), and it is one way worlds diverge (D135).
  - **Recognition (from the designer):** a character who has met someone should know them again, unless they are disguised, which is a contested check. That needs what they looked like kept as state. In the fifth playtest's fourth session, Brightfin came back to the Weighhouse and the Narrator showed "a woman beside him" stacking green-tarp crates, without saying whether she was Sefu, whom Brightfin had met there half an hour before. The Narrator had only prose to go on, and Fareed, the green-tarp man, was likewise new and named in narration only.
- [x] Exporting a character's story: built (D100–D105). Still open: whether the telling should also cover a single scene or session, and illustrated or printable formats.
- [ ] The underlying model, belief and being (D106): a draft direction with open questions. See Draft: The Underlying Model, Belief and Being. Its first slice is built: what an NPC knows about a character (D121).
- [ ] Attention as a resource: direction set (D94), details open. See Planned: Attention.

**Prototype plan:**

1. Python CLI with SQLite state: characters, regions, items, events.
2. Rules engine: the 2d6 resolver, tiers, tracks, XP triggers, all unit-tested.
3. Narrator agent on the Claude API with the tool contract above and a setting prompt built from this doc.
4. One playable scene end to end, then playtest and tune the prompt.
5. Multiplayer, after the single-player playtest (D32).

## Decision log

D1–D23 were decided 2026-09-27, in the repository, from the open questions raised after the rules, state and content steps. Each decision was then reviewed individually with the designer; D11, D16, D18, D21 and D22 changed in that review, and D10 is marked for revisiting. D24–D32 were decided 2026-09-28 from the calls made while building the Narrator agent, each reviewed individually; D29 is marked for revisiting. D33–D43 came from the first playtest the same day, D44–D49 from building character details, D50–D55 from time and weather, D56–D59 from seasons, moon and tides, D60–D66 from NPC memory and attitudes, D67–D75 from random encounters (D72–D75 replacing parts of D67–D71 the same day), D76–D81 from languages, D82 from the designer after layer 6, D83–D89 from bodily needs (the effects in D84 chosen by the designer), D90–D93 from setting-native kinds, D94–D95 from the designer after layer 8, D96 from the designer after merging layers 6–8, D97 from the designer the same evening, D98–D99 from the first blind playtest, D100–D105 from building story export, D106 from the designer after the second playtest, D107–D108 from its fixes, D109 from a conversation with the designer after the third playtest, D110 from the fourth playtest, D111–D121 from the designer the next day, from the same playtest, D122–D123 from the fifth playtest, D124–D130 from the designer after it (D127–D130 decided, not yet built), D131 from its second session, D132–D134 from the designer after it, D135–D137 from the designer during and after its third session, D138–D139 from its fourth, and D140 from a conversation with the designer after it.

| ID | Topic | Decision |
| --- | --- | --- |
| D1 | Rolls gate consequences | Single-use roll id; consequences cite it; 10+ none, 7–9 one cost, 6− one move; no roll, no state change except `report_trigger` rewards |
| D2 | 7–9 costs | Take one item, 1 Harm, 1 Fade, region Light −1, or narrative-only |
| D3 | `adjust_light` | Adds direction (raise/lower) and size (deed ±1 / major ±2); one change per region per scene; major needs an XP trigger in the same scene |
| D4 | XP triggers | Exactly four; 1 XP each; once per character per scene |
| D5 | Opposed-roll ties | Defender holds |
| D6 | Move magnitudes | Harm and Fade 1–3; encroach −1; others 1; threat clocks 4 segments, defined in content, advanced by 1, never created by the Narrator |
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
| D27 | Movement | Player's `/go` command; the Narrator never moves characters |
| D28 | Taken items | Leave play; the log records it |
| D29 | Knack day boundary | Superseded by D50: city midnight |
| D30 | Treatment knacks | Heal the roller only, 1 Harm on 7+ |
| D31 | Casting with Wire | Only through a tech-magic knack |
| D32 | Prototype scope | Single-player through budget and playtest; multiplayer is its own later step |
| D33 | Narration | Third person, present tense, by name and the sheet's pronouns; players choose pronouns |
| D34 | Player input | Plain text is action (any person); quotes are exact speech; the Narrator never rewrites or adds to them |
| D35 | `/ask` | Out-of-character question: look only, no roll, state change, time or beat |
| D36 | Owed consequences | A 7–9 or 6− roll must get its consequence; code sends the Narrator back (up to twice) |
| D37 | Character details | Age, pronouns, appearance, languages for players and NPCs (built: D44–D49) |
| D38 | Time and weather | Real-time city clock, weather, NPC schedules, daily tick (built: D50–D55) |
| D39 | NPC memory | Attitudes and interaction notes in code; the Narrator proposes, code caps (built: D60–D66) |
| D40 | Encounters | Code rolls on arrival and every 5th beat; odds rise as Light falls (built: D67–D71) |
| D41 | Languages | Tracked; unknown speech as gibberish; Heart roll for the gist; language knack +1 (built: D76–D81) |
| D42 | New kinds of people | Setting-native kinds as origins, not classic fantasy races (built: D90–D93) |
| D43 | Build order | Fixes; details; time/weather/schedules; NPC memory; encounters; languages; kinds |
| D44 | Languages | Registry Standard for everyone; market tongues common; Protocol, Underside Cant, animal-speech rare |
| D45 | Neighborhood languages | Per-district spread (everyone to few) and culture note; per-place pockets |
| D46 | A character's languages | Registry Standard + origin's language + one of choice |
| D47 | Age and appearance | Short free text, narrative only |
| D48 | Maps | Hand-drawn per district; [@] for here; unvisited places stay ??? |
| D49 | Art | Hand-authored ASCII vignettes and NPC portraits; the model never draws |
| D50 | City clock | US Eastern, real time; the city day turns at city midnight (replaces D29); budget month stays UTC |
| D51 | Weather | 3-hour blocks that drift through a transition table; stored and shared; no automatic effects |
| D52 | NPC schedules | 4–6 blocks a day plus weekday variations; code places NPCs by the clock (placing replaced by D111–D113) |
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
| D67 | Encounter odds | Superseded by D72–D73: a daily pool, and the Narrator decides when |
| D68 | Encounter kinds | Color, opportunity, trouble; weighted by Light through the pool (D74) |
| D69 | Conditions | Place, part of day, weather, tide, season and moon filters; now on encounter ideas |
| D70 | Strangers | One-off, generated by code at the Narrator's request with a neighborhood language |
| D71 | Pacing | Superseded by D73 and D75: one per turn, no cooldown, recent ones shown to avoid repeats |
| D72 | Encounter pool | Per district per city day, rolled by Light: 2–4, 3–6 or 5–9; shared; no carry-over |
| D73 | Narrator creates encounters | Fresh each time via `create_encounter`, spending the pool; at most one per turn |
| D74 | Kinds in the pool | Rolled by Light band; dark trouble half Underside; the Narrator spends only what the pool holds |
| D75 | Variety | Recent district encounters shown so the Narrator doesn't repeat; content entries are ideas only |
| D76 | Speech tags | The Narrator tags every line others speak with speaker, language, tone and gist; code checks speaker and language; a bad tag is never shown and the Narrator is sent back (up to twice) |
| D77 | What is heard | Own languages word for word; common languages named, rare ones not; invented languages as code-made gibberish, real ones as a bracketed note; no tone without a gist roll |
| D78 | Gist rolls | `call_for_roll` names a language: Heart, unspoken by the character, heard here, once per language per scene; 10+ gist and tone, 7–9 tone or gist for a real cost, 6− nothing; lasts the scene |
| D79 | Language knack | Ear for Tongues: Heart, +1 on gist rolls only, once per scene |
| D80 | Speaking aloud | `/speak` picks one of the character's languages (default Registry Standard); the Narrator is told which NPCs understand it; NPCs never roll |
| D81 | Speech log | Every line logged with what the character understood; beats keep what the player saw; the Narrator sees the last six lines |
| D82 | Build order | Bodily conditions (hunger, thirst, heat and cold, sleep) are layer 7, before setting-native kinds (now layer 8) (built: D83–D89) |
| D83 | Bodily needs | Hunger, thirst, tiredness, cold, heat; each 0–3, tracked by code, with words per step |
| D84 | Need effects | −1 at 2 and −2 at 3 to two stats each; stacks, but a roll stat stays ≥ −3; at the worst, 1 Harm (Fade for tiredness) on reaching it and per further step |
| D85 | Need time | Counted only online on the city clock: thirst 3 h, hunger 4 h, tiredness 6 h per step; cold and heat 1 h exposed, easing 1 per 30 min |
| D86 | Exposure | Places are sheltered, exposed or always cold; weather (else season) is cold or hot |
| D87 | Relief | `/eat` and `/drink` buy what a place sells, in glitter; `/rest` at a haven; no roll; the Narrator points to the command |
| D88 | Needs offline | Frozen offline; logging off at a haven clears them |
| D89 | Needs by origin | Each origin lists its needs; made people only tiredness and heat |
| D90 | Setting-native kinds | Hearsay (a story walking), Castoff (a dead brand's mascot), Mislaid (a lost thing become someone), as origins |
| D91 | Their needs and languages | Hearsay: all but tiredness; Castoff: tiredness and cold; Mislaid: cold and heat; a market tongue, or Underside Cant for a mislaid |
| D92 | Their tags | Narrative only; code still enforces only `no-hands` |
| D93 | Origins in the Narrator's brief | Every origin's trait, tags and needs are in the content brief |
| D94 | Attention (planned) | The world's sustaining force, tracked by code; a set amount per character per day; spent on pushing the world against its grain (which pulls back: the Undertow), remembrance and prayer; details open |
| D95 | Inspiration | China Miéville's work, especially Perdido Street Station, joins the influences |
| D96 | Story export | Players can export their character's story as an artifact of play; it may be told rather than recorded, but reveals nothing the character doesn't know; comes before attention |
| D97 | The city is the Narrator (theme) | The AI that runs New Vesper is the city itself: attention, forgetting, curated memory and going quiet are how both live. A thematic note, not yet in the Narrator's prompt |
| D98 | One action, one roll | At most one `call_for_roll` per turn, and its result stands; the Narrator re-tells the turn once when sent back, replacing its earlier telling |
| D99 | One action per prompt | One line, typed after the last answer; input typed during the Narrator's answer is dropped; multi-line pastes are refused whole; the session and state refuse line breaks and control characters |
| D100 | Two versions | The record (scenes as seen, one chapter each) and the telling (retold in the character's voice) |
| D101 | Only what was seen | Built from the narration shown and the player's own actions; hidden state is never read |
| D102 | The telling | One cheap `story` call against the budget; first person; may shade and skip, invents and explains nothing; the record is free |
| D103 | Scope | The whole story so far, a Fall included; latest four scenes in full, summaries before, capped at 24,000 characters |
| D104 | Where and how | Markdown in `stories/`, never overwritten; `/export`, `/export record`; `new-vesper export` for any character, fallen too |
| D105 | Theirs to keep | Players may edit and share the files; the game never reads them back |
| D106 | Belief and being (draft) | One belief field (claims × holders × strength); epistemology is a holder's slice, ontology its weighted integral; history is fixed, the present is believed; the rules layer stays outside; option: attention and credence as two orthogonal fields; open questions for the designer |
| D107 | Every prompt, names that are names | The one-line rule covers every prompt, creation included; names are 1–40 characters of letters, digits and name punctuation; pronouns are words joined by slashes; `/rename` and `/pronouns` |
| D108 | Every consequence shows | Consequences that move no number still appear in the bracketed line; the Narrator makes each one visible in the story |
| D109 | Persistence, memory and stories | A thematic note, not a rule: how the AI persists, humanity as its stories, the axes of shade, the record as the check on the telling; Metzinger's The Ego Tunnel joins the influences, honestly noted as the first from philosophy rather than feeling |
| D110 | The Bond is the player's | The Narrator never invents facts about a character's Bond; it asks through the fiction and builds on the player's answer |
| D111 | One place at a time | Where each NPC is and what they're doing is stored state; the schedule becomes their agenda (replaces D52's placing by the clock) |
| D112 | The Narrator plays NPCs who are here (exits by D132) | Only the Narrator moves on an NPC who is with a player character, via `npc_moves_on`; code sends them where their agenda says; the agenda is soft, and the Narrator may let them run late or cut a conversation short |
| D113 | Off-screen, the agenda | An NPC nobody is with follows their agenda exactly, from where they really are; variation is a later idea |
| D114 | Time that passes shows | A gap of 15 minutes or more between turns in a scene is shown to the Narrator, which shows it first and never decides what the character did meanwhile |
| D115 | Who understood the character | The character's quoted words are labeled with their language for the Narrator; an NPC who didn't understand and speaks that turn must be tagged `understood="no"`, or the Narrator is sent back |
| D116 | The body | A line at creation on how the character is built and moves; narrative only; asked once of older characters; `/body` changes it |
| D117 | Who is here, every turn | A short block first in each turn: the character, everyone present and the items held and here; never contradicted |
| D118 | When the line doesn't fit the body | The Narrator asks once, in a bracket, how the character does it, and narrates nothing else that turn |
| D119 | Moods | Code rolls each NPC's mood every city day from content, colored by goal news and foul weather; the Narrator may shift it once per scene with `npc_mood` |
| D120 | What they want now (replaced by D122) | The Narrator sets what an NPC wants in this scene with `npc_wants`; kept and shown every turn; may change once |
| D121 | What they know | Facts per NPC about each character, as heard or seen; the oldest fold past 16; an NPC acts only on what they know; the first slice of D106 |
| D122 | Wants are played, not stored (replaced by D124) | Stored scene wants and `npc_wants` are dropped; the Narrator plays what NPCs want from prose |
| D123 | Facts are read after each turn | A cheap call after each turn with NPCs present proposes what each learned; code keeps at most three per NPC; `npc_learns` is removed |
| D124 | What they want now, kept by code | Up to four current wants per NPC, shared; changed only at scene close by the memory call, for reasons; code keeps at most three changes of each kind, for NPCs who were there |
| D125 | The journal | Each NPC present reaches the Narrator as one journal: at_heart, wants_now, tensions, lately, memories and knowledge |
| D126 | Wants in tension | Two current wants may pull against each other, one NPC's own or two NPCs'; kept only between current wants, ended with either; never settled by narration || D127 | Feelings move at the moment of learning | An NPC's feelings change when they learn another's part in a tension or alliance, not at its resolution; proposed at scene close, capped as D61 (not yet built) |
| D128 | Who knows | Tensions and alliances record which parties know the other's part; marked at scene close; no feeling change for a party who doesn't know (not yet built) |
| D129 | Grudges and repair | A drop on learning of a betrayal is a grudge; one step fades after a week unless renewed; deeper ones need amends, settled by 2d6 + the wronged NPC's fondness (not yet built) |
| D130 | Alliances | Two wants may pull together; shown in both journals; learning of help raises feelings under D127; off-screen cooperation later (not yet built) |
| D131 | The telling ends where the record ends | If the record stops mid-scene, so does the telling; it is given the record's last moment |
| D132 | Exits are read from the narration | The after-turn pass reads NPC departures and code carries them out; `npc_moves_on` is retired; NPCs may move because they want to |
| D133 | Detours | Off their agenda until their next scheduled block, two hours at most, even unwatched; then they rejoin their day |
| D134 | What code checks | The NPC was there; the place is real, in the district, not their own, above water; 'away' only when their day says; the reason is logged |
| D135 | Worlds that diverge (theme) | A thematic note, not a rule: a large world grows from small scenes, and worlds from the same start diverge through what code keeps; in the designer's words, designing the game is the game |
| D136 | Arriving together | After /go, the arrival turn sees the last scene's closing moments; NPCs who walked there with the character are marked came_with_you all scene |
| D137 | A restated want replaces the old one | Scene close ends a want it corrects or replaces; scene close runs on the turn model, configurable |
| D138 | A deferred-to NPC acts | When the player character defers to an NPC, that NPC speaks and acts in full that turn; a turn never ends just before an NPC acts |
| D139 | Scene close records only what happened | A want is met only when the scene shows it done; offers, proposals and open arguments are not outcomes |
| D140 | Debts | A note, not a rule: what New Vesper owes to Apocalypse World, Blades in the Dark, other games and fiction, and to the writers behind the model itself; credit what can be traced, imitate no living writer |
