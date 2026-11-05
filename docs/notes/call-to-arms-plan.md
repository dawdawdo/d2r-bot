---
name: call-to-arms-plan
description: "Done 2026-11-03: Blizzaga respec'd to Blizzard + Glacial Spike; CTA on swap (F6), r=BO, t=BC, cast outside town; Meph kills ~65-75% per fight; parking is the main loss"
metadata:
  type: project
---

2026-11-03: Blizzaga respec'd to Blizzard + Glacial Spike (no Frozen Orb) with Call to Arms on weapon set I (main = set II). Swap F6, r = Battle Orders, t = Battle Command (Skill 9). War cries can't be cast in town, so they go on arrival in LK / Durance 2 and at the Meph spot, refreshed during the fight.

**Why:** BO took life 485 -> 626 and the mana pool up with it; Meph went from ~1/3 kills to 6 of 9 with no deaths in the first batch.
**How to apply:** if Stephen rearranges the inventory or gear again, update `inventory.protected` and the test frame (`fixtures/inventory/respec_20261103.png`) before trusting the stowaway, and re-read skill hotkeys from the skill bar; they moved in this respec. Related: [[merc-follows-teleport]], [[inventory-stowaway]].
