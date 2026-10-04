# Sharing New Vesper

A checklist for taking the game beyond its designer and Claude, roughly in order. Drafted 2026-10-04, after the fifth playtest began; the facts about the repo were checked that day.

## 1. Before anyone else plays

- [ ] Finish the current playtest, fix what it finds, and merge the open branch.
- [ ] Do a clean install, following the README word for word on a machine or account that has never run the game. Windows too, if one is to hand.
- [ ] Remove the README line "If the repository is private, the owner must add you as a collaborator first."
- [ ] Ignore every database file, not only `vesper.db`: `.gitignore` lists `vesper.db` alone, so `playtest4.db`, `playtest5.db` and any `--db` file a tester makes could be committed. Use `*.db`.

## 2. Ownership and privacy

- [ ] Add a licence. There is no `LICENSE` file, so legally nobody may use or copy the code. A common split:
  - the code under MIT or Apache-2.0;
  - the setting and text (New Vesper, its people and gods, `docs/design.md`) under CC BY-NC-SA or all rights reserved, so the designer keeps control of the world.
- [ ] Decide about the email in the commit history: the designer's commits carry a personal address, which will be public with the repo. GitHub's noreply address can be used for future commits; rewriting past history is possible but disruptive.
- [ ] Check again for API keys just before going public. On 2026-10-04, all 68 commits held only the `sk-ant-...` placeholder.
- [ ] Say plainly in the README that the game was built with Claude.

## 3. A README for strangers

- [ ] Open with a short pitch: two lines of what it is, then a few lines from a telling (Brightfin giving his bowl to the unseen thief is a strong one).
- [ ] Add "what to expect":
  - a prototype, played solo, in one district;
  - about 3¢ a turn on the player's own API key;
  - the default $10 monthly allowance is the player's own money, and how to lower it (`NEW_VESPER_PLAYER_ALLOWANCE_USD`).
- [ ] List the known rough edges in a few lines, and link to the design doc's Open Questions.
- [ ] State the content lines (D19) in one sentence, so players know what the Narrator won't write.

## 4. Feedback

- [ ] Turn on GitHub Issues and add a "Playtest report" template asking for:
  - what they tried;
  - where they got confused or lost;
  - their `/export record` file;
  - their cost, from `/budget`.
- [ ] Remind testers never to paste their API key. The game never writes it into exports, but people paste whole terminals.
- [ ] Say how much feedback is welcome and how much will be answered ("I'll read everything but can't answer everything").

## 5. Rollout

- [ ] First, three to five people the designer knows, each playing one session blind. Fix the top two things they hit.
- [ ] Then a post on r/ClaudeAI, after checking its current rules on self-promotion:
  - angle: how it's built. The AI proposes and code decides, and the Narrator can't talk its way around the dice;
  - show one telling excerpt, and one moment of the Narrator being refused (D118's question, or a rejected tool call);
  - ask for blind playtests and issue reports.
- [ ] Hold off on general tabletop communities until there is a tabletop edition; AI-run games tend to get a hostile reception there.
