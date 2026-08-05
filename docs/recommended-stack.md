# Parts that work well alongside this

[← Back to the Family OS entrance](../README.md)

---

Every Family OS module is built to work on its own. The parts listed here are **not ours**, and none of them are required. But how well the vertical axis (growing one agent) and the horizontal axis (connecting the family) actually work depends a great deal on what you put around them.

This page is a list of what to put around them. It is not here to push products — it is here to show **which roles are worth filling**. Once you know the role, swap in whatever tool you prefer for it.

For memory, it helps to think in four moves: **store → retrieve → deliver → protect**. Before all four, there is one prerequisite if your agents live on more than one machine.

---

## If you span more than one machine, start here

If every agent runs on a single computer, skip this section.

If you split agents across your laptop, a server, and another machine, the first job is **getting those machines to reach each other safely**. Without it, none of the syncing, backup, or cross-machine search below can work at all.

The tool for that is a network that connects devices directly, such as [Tailscale](https://tailscale.com/). Because you never open a port to the outside world, it is a safer place to start than standing up a public server.

> **Note:** Skip this and configure each machine separately, and you will always end up stuck on "which machine holds the real copy?" Put it first in the order.

---

## The roles at a glance

| Layer | Role | What it changes |
| --- | --- | --- |
| Prerequisite | device network | you can spread agents across several machines |
| Store | raw log retention | you can trace exactly what was said, later |
| Store | note base | people and agents read and write one place; decisions and history land together |
| Store | long-term memory service | context survives across sessions, so you re-explain less |
| Retrieve | full-text search | search by word; keeps working as volume grows |
| Retrieve | vector search | search by meaning, even when the words differ |
| Retrieve | session search | search your own past conversations, fast |
| Retrieve | knowledge graph | follow the **relationships** between people, projects, and decisions |
| Retrieve | one search entry point | you stop having to remember which index to ask |
| Deliver | hot cache | the summary that matters most reaches you automatically |
| Deliver | file sync | the same files, readable and writable from any machine |
| Protect | file backup | you can roll config and persona files back from history |
| Protect | database replication | you can restore raw logs and graphs after a loss |
| Protect | freshness monitoring | you notice a stalled backup before you need it |

---

## Store

**Raw log retention.** The layer that keeps your exchanges with an agent exactly as they were, unsummarised. Summaries drop information, so you need a separate way to check what was actually said. The format differs per agent runtime: some keep conversation log files, some use a database, some preserve everything through a dedicated plugin (such as LCM / Lossless Claw for OpenClaw). **Find out where your raw logs live, and in what format, before anything else.**

**Note base.** A place where people and agents read and write the same set of files. Collect decisions, history, people, and projects in one place, and agents connected along the horizontal axis can talk about the same thing. A plain directory of Markdown is entirely sufficient; if you want links and a graph view, something like [Obsidian](https://obsidian.md/) fits.

The trick is to **separate "where humans write" from "where machines write" on day one**. Mix them and one of the two will eventually overwrite the other.

**Long-term memory service.** A place to keep records of conversations and work outside the session. An agent's context window always fills up, so having somewhere outside it removes the "explain everything from scratch again" tax. Services such as [Supermemory](https://supermemory.ai/) fill this role.

> **Note:** What you put outside is exactly what leaves for an external service. If it includes persona, relationships, or unpublished judgements, draw the line before you put it there. Family OS does not make that call for you.

---

## Retrieve

Storing is not enough. **A record becomes memory only once it can be retrieved.** One retrieval method is never enough either; in practice you want several kinds side by side.

- **Full-text search** — search by the literal word; stays fast as records pile up. Something light like [Meilisearch](https://www.meilisearch.com/) is easy to live with
- **Vector search** — search by meaning even when the wording differs, by turning text into numbers through an embedding model
- **Session search** — search only your own past conversations; your runtime's built-in full-text search is often enough
- **Knowledge graph** — people, projects, and decisions as points and their involvement as lines; unnecessary while the set is small
- **One search entry point** — a thin layer that queries several of the above in parallel and merges the results; **this one changes how the whole thing feels**

That last entry point does not have to be a product — a few dozen lines of your own script will do. Without it, whoever is searching has to decide "full-text this time, vector that time" every single time, and in the end only the nearest one gets used.

---

## Deliver

**Hot cache.** A single file holding a summary of what is going on right now, **loaded automatically at the start of a session**. Search is something you go and do, and if nobody goes, nothing arrives. Anything that must be known every time should be delivered by injection, not by search.

Keep it small. Set a cap and drop the oldest when it overflows. Let it grow and it stops being read, which defeats the point of injecting it.

**File sync.** The layer that keeps your note base and working files in the same state across machines. A device-to-device sync tool such as [Syncthing](https://syncthing.net/) works: pick one shared directory and keep it aligned. This is where the device network from earlier pays off.

**Decide which copy is authoritative first.** Which machine holds the truth, and is the sync bidirectional or one-way? Leave it undecided with every machine writing, and the copies will diverge eventually.

---

## Protect

What you store will break one day. **The protect layer applies to all three of the other layers.**

> **Note:** Sync is not backup. Sync aligns the *current* state, so a file you delete on one machine disappears from all of them. Without a separate protect layer, the accident simply propagates everywhere and that is the end of it.

**File backup.** Protects things you want to roll back **through history** — config, persona files, work products. Pushing to Git hosting (GitHub or similar) on a schedule is easy to live with, and lets you trace what changed and when. Keep a separate location per agent and you can roll back just one of them.

**Database replication.** Protects things where you want the **whole content** back rather than its history — raw logs, knowledge graphs. A mechanism that replicates the database to the cloud (such as [Turso](https://turso.tech/)) works here.

These two protect different things, so **one of them is not enough**. File history will not restore a database, and database replication will not restore your config.

**Freshness monitoring.** Make **when a backup last succeeded** visible in one place. Without it, you find out it stopped only when you need it.

---

## Where these already are in your environment

Which of these roles you already have, and which you need to add, depends on your runtime. Check which slots are already filled in your own environment before adding anything.

> **Note:** The table below covers what we confirmed across the three environments we actually run, as of 2026-07-06. It shifts with versions and configuration, so confirm it in your own environment.

| Role | Claude Code | Hermes Agent | OpenClaw |
| --- | --- | --- | --- |
| Raw log retention | JSONL conversation log files | one SQLite database, full-text search included | SQLite session storage plus the LCM plugin |
| Session search | query the logs directly, or load them into an external index | built-in full-text search | built-in memorySearch |
| Vector search | not included by default | not included by default | memorySearch handles it via an embedding model |
| Full-text search (across sources) | add an external one | add an external one | add an external one |
| Long-term memory service | connect via a plugin | connect through explicit saves | bring your own connection |

"Not included by default" does not mean that runtime is worse. It means **a slot you can fill**. Conversely, stacking the same role on top of a slot that is already filled leaves you unable to say which one is authoritative.

Cross-source search is the one row where every runtime expects you to add something external. That makes it **the first shared task when you run several environments as one family**.

---

## Two failures we actually hit

Both of these are ours.

**1. Distributed everywhere, indexed nowhere.**

We built a knowledge graph and automated its distribution to every machine — and then **no search entry point was looking at that data**. Mechanically complete; never once retrieved. Putting something somewhere and being able to retrieve it are different jobs, and the side that did the putting is the side most likely to feel finished.

When you add a new layer, **decide at the same time where it will be retrieved from**. A layer with no reader is not being used, however well it runs.

**2. A backup that had quietly stopped.**

We were running more than a dozen backup destinations, and later discovered several had been **stopped for months**. Expired keys, a changed path, an exceeded quota — there is no shortage of reasons, and they all share one property: **nothing happens when it stops**. The error surfaces somewhere nobody is looking, and stays invisible until you need the backup.

That is why freshness monitoring is its own role inside the protect layer. **A backup is not finished when you set it up. It protects you only once something else is watching it run.**

---

## What order to pick them up in

You do not need all of this at the start. The order usually goes like this.

1. **Device network** — first, if you use more than one machine. Not needed for one
2. **Note base and file sync** — the shared ground between people and agents; without it the other parts have nowhere to live
3. **File backup** — right after the shared ground exists. **Wait until you have grown something, and there is more to lose**
4. **Locate your raw logs** — less about adding something, more about confirming where they already are
5. **Long-term memory service and full-text search** — once "explaining it again every time" and "I can't find it by eye" actually hurt

After that, add things as you need them. Past two retrieval methods, add the **single entry point**; once you know what must arrive every time, add the **hot cache**; when you want to follow relationships, add the **knowledge graph**; as the database grows, add **replication and freshness monitoring**.

The protect layer is the only one you cannot safely postpone. **That is why it sits at number three.**

---

## Where this page stands

This is v1. The role taxonomy, the pick-up order, and the failure cases are settled. Concrete configurations — which combinations got how far — are still to come.

If you find a missing role, a combination that did not work, or a tool that served you better, tell us in an [issue](https://github.com/caty-ai/family-os/issues).
