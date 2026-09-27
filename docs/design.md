# New Vesper — Setting & Rules

Exported from the living design doc on 2026-09-27. The living doc is where design discussion happens; update this file when it changes.

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

**Creation:** assign the array +2, +1, +1, 0, −1 to the five stats; pick an origin; pick two knacks; name one Bond, a person your character matters to.

**Knacks** are the open catalog of things a character does well. Anyone can take any knack the fiction supports; a rat hacker is fine if you can say how.

**Leveling up.** Reaching level N+1 costs 5 + N XP, earned from the advancement triggers. Each level, pick one:

- A new knack
- +1 to a stat (cap +3)
- Heal a scar

Every fifth level also unlocks an **advanced knack** or an **origin evolution**, such as a plaza pigeon becoming the plaza's minor god.

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
| 5–6 | Critical; at 6, Fall or Endure | Slipping (6): into Old Vesper |

**Harm** (flesh and chrome) fills from violence, accidents and backlash. Treatment, rest and repair clear it. When Harm fills, the player chooses:

- **Fall:** die performing a final act that permanently changes the world (a sealed door, a saved block, a named memorial in code).
- **Endure:** survive with a permanent scar or condition, written to the character sheet.

**Fade** fills from isolation, horror and broken promises. As it rises, the world forgets you: shopkeepers lose your face, cameras stop tracking you, doors stop opening. Low Fade can help a thief; high Fade is dangerous.

- **Recovery:** being seen. Time with other players at a shared place, keeping your word, someone speaking your name.
- **At maximum:** the character slips into Old Vesper and becomes an Underside character. Changed, not dead.

**Advancement:** experience comes from a fixed list of triggers that code checks: protecting someone, making a sacrifice, keeping a hard promise, raising a region's Light. Killing things earns nothing on its own. See Characters for what XP buys. The DM can report that a trigger happened; code decides whether it pays out.

## Magic

Magic is bargaining with attention. There are no spell slots and no mana; every working costs something the world remembers.

- **Rolls:** casting is a Weird roll. Tech-magic, such as hacking a god's prayer network, can use Wire.
- **Knacks** define what a character can do reliably, such as asking a shrine's god one question. Anyone can attempt raw magic without a knack, at Desperate difficulty.
- **Costs on 7–9** come from a magic list: a tick of Fade, a side effect, or a favor owed to a god.
- **The favor ledger:** code records every favor owed. Gods collect, and debts become story hooks. This is the Tally made mechanical.

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

| The DM decides | Code owns |
| --- | --- |
| Whether a roll is needed | The dice |
| Which stat applies | Harm, Fade, stats, inventory |
| Which difficulty rung | Currency, loot tables, XP triggers |
| Which move to make on 6 or less, from the allowed list | Region Light levels |
| Narration, NPC voices, scene description | What exists: items, NPCs, places |

**Initial tool contract:**

- `call_for_roll(stat, difficulty, stakes)` returns the tier.
- `apply_consequence(type, target, magnitude)` checks the allowed list and writes state.
- `grant_from_table(table_id)` hands out loot; the DM never invents items.
- `report_trigger(trigger_id, evidence)` flags an XP trigger; code decides the payout.
- `adjust_light(region, reason)` nudges a region by a fixed step.
- `look(entity)` reads current state so narration matches the world.

## Shared Play

Players act freely until their actions touch each other; then they share a scene resolved in beats, not initiative.

**Light scale:** each region runs 0–10. A deed moves it ±1, a major deed ±2. Neglected regions lose 1 per in-game week. The city ticks once per real day.

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
- **Preying on the weak makes you forgettable.** Attacking a character several levels below you adds Fade to the attacker.
- **The city takes notice.** Violence against a player lowers the region's Light and can trigger "a faction takes notice." Victims can file a grievance with the Registry, which posts bounties.
- **Opposed rolls.** Both players roll and the tiers are compared, so the defender always has agency.

**Focus on social conflict.** Betrayal, theft, rival bargains with the same god and races to claim a forgotten shrine carry the drama. Violence is possible but expensive.

**Risks to design for:**

- **Prompt injection between players.** Player text is untrusted input. Code validates every tool call, whatever a player writes or the narration says.
- **Harassment.** Content lines the DM will not narrate, plus mute and block tools for players.
- **Alt accounts.** Second characters used to farm or gang up; address before public launch.

## Costs and Budget

The DM's tokens are the main running cost; hosting is small. Cost scales with player-hours.

- **Usage ledger:** record every API call's token usage against the player and scene that triggered it, from the first prototype.
- **Monthly cap:** a hard spending limit set by the operator. When the pool runs out, the city goes quiet until the month resets.
- **Per-player allowances:** a monthly hour budget per player, so no one drains the shared pool.
- **Model routing:** cheaper models for routine narration, stronger ones for adjudication.
- **Later options:** a patron pool, bring-your-own API key, or prepaid credits, all built on the same ledger.

## Open Questions and Next Steps

The first build is a playable CLI prototype: one player, one district, the full rules loop.

**Open questions:**

- [ ] Starter knack catalog: about 20 knacks across the five stats.
- [ ] Advanced knacks and origin evolutions for level 5 and up.
- [ ] Magic cost list and how gods collect on favors.
- [ ] Market District layout: key stalls, NPCs, shrines, the drowned station.
- [ ] Beat window length, and whether it adapts to how many players are present.

**Prototype plan:**

1. Python CLI with SQLite state: characters, regions, items, events.
2. Rules engine: the 2d6 resolver, tiers, tracks, XP triggers, all unit-tested.
3. DM agent on the Claude API with the tool contract above and a setting prompt built from this doc.
4. One playable scene end to end, then playtest and tune the prompt.
