<title>Street Signal Concept Brief</title>

# Street Signal
### Concept brief · Boston · August 2026

---

## The one-liner

**A resident asks whether their street is being ignored, and gets a straight answer from the city's own records — in one sentence, with receipts.**

---

## Who it's for

Not "citizens." Someone who has **already reported the problem**, probably more than once, and is now sitting with the feeling that it didn't matter.

They are not looking for data. They are looking for a verdict on themselves.

---

## The problem, precisely

You report the rats. Weeks later an email says **Closed**. Nothing on your street has changed.

Two doubts follow, and both land as self-blame:

- **"Is this normal for a city, or is my block being skipped?"** With no basis for comparison you can't tell, so the doubt lands on you. You start to wonder if you're the difficult one.
- **"Did anything actually happen, or was I just handled?"**

Underneath both sits an information asymmetry that is close to total. The city knows your case number, its deadline, your street's whole history, who else reported it, and what "closed" actually meant. You know none of it.

**You are the only party in the transaction operating blind — and you are the one it is happening to.**

---

## What they want to feel

Two things, in this order:

**Legitimacy.** *"Nine other people on this street reported the same thing. I'm not being difficult — I'm right to be annoyed."* Being validated by evidence is the emotional payoff, and it has to land before any useful information does.

**Agency.** Knowing what the city calls this in its own system, who owns it, what the real timeline looks like on *your* street rather than the citywide average, and what the next actual step is.

> **Stop shouting into a void. Start being someone with a case.**

---

## The evidence that they're right

Computed from Boston's 2025 311 export — 267,187 records:

| | |
|---|---|
| **58,005** | cases closed as **"noted only"** — recorded, no fix logged. 29.7% of everything closed. |
| **31.8%** | missed the city's own deadline |
| **40.2%** | of all volume is a repeat — same address, same problem, filed again |
| **4.8 h** | median close time — the number that makes the city look responsive |
| **90.8 d** | 99th percentile — where people actually live, and nobody tells you which half you're in |

The answer to *"is it just me?"* is usually **no, and here's the proof** — and that proof is public, and no resident can get at it.

---

## Why nobody has built it

**There is no prose in the data.** 267,187 rows carry no description field, only short category codes. 2,982 distinct titles exist, but the top thirty cover **84.9%** of every row, and one of them is 60,641 identical strings. Drop that into a vector index and you get sixty thousand copies of the same point.

**And most of it isn't residents.** **57% of the file is city staff** logging their own rounds. Skip that filter and the product tells someone *"eleven neighbours reported this too"* when seven were an inspector — inventing exactly the solidarity it exists to provide honestly.

---

## The product

**One answer card.** Ask in plain language, typed or spoken. Get back a calm sentence, then layers on demand:

> **No — 9 residents reported rodent activity on 328 Dartmouth St in 2025.**
> The city logged 4 more itself. ISD is the department that handles these.
> **12 of the cases there closed as "noted only"** — recorded, with no fix logged.

Legitimacy first. Logistics second. Every figure opens the city's own record.

**One map.** Boston in 3D, every issue a pin. Height is priority, ground ring is how many neighbours, colour is what kind of problem. You read the backlog before you read a word.

**One board.** Neighbours back the issues that matter, ranked by consequence rather than volume.

---

## Three commitments

**It refuses out loud.** Ask for a landlord's phone number and the input guard blocks it *before any search runs*. Ask something outside the data and it says *"I don't have a source I trust for that."* Being told nothing is honest beats being told something plausible.

**Citations are bound, never written.** They come from the rows that were actually retrieved, so a model cannot fabricate one.

**It counts neighbours separately from staff, and says so.** *"Nine residents reported this; the city logged six more itself"* is a better sentence than either number alone.

---

## The severity field the city doesn't have

Boston's schema carries no priority signal at all. A rat infestation and a misplaced recycling bin enter the same queue with the same clock.

| Tier | Share | Noted only | Who should touch it |
|---|---|---|---|
| **P1 · Safety** | 14.2% | 19.8% | Human, now |
| **P2 · Home** | 7.0% | **63.5%** | Human, scheduled, with a return visit |
| **P3 · Routine** | **74.6%** | 30.0% | System proposes, human approves in batch |
| **P4 · Admin** | 4.2% | 7.8% | Fully automated |

**78.8% of the queue is routine or transactional, and it is choking the 21% that needs a person.** P2 — the tier with the deepest human stakes — has the *best* deadline performance in the city, because it is closed without being acted on. Speed there is the symptom, not the achievement.

Halving that 63.5% dismissal rate costs 7% of capacity and would change how Boston feels to live in more than anything else on the list.

---

## What it costs to run

**One HTML file.** No server, no API keys, no per-query cost, no network at runtime. The build step is offline — a Python script rolls 267,000 coded rows into readable cards in about four seconds with zero model calls.

On dead conference wifi, on a bus, in a basement apartment, it still answers.

---

## Honest limits

- **The local model is optional.** Granite 3.1 8B classifies free-text reports when it's reachable; otherwise a keyword router takes over and the interface says which one decided. The prose is assembled from counted fields either way.
- **Property Assessment covers 58 streets**, not all of Boston — the city's API caps at 32,000 rows.
- **Approximate street matches say so** rather than passing another street's numbers off as yours.
- **Reports stay on the device.** A community signal, not a filing. Real reports still go to 311.
- **The tier boundaries are ours, not the city's.** That absence is the finding, but the boundaries are a judgment call — Encampments in particular sits awkwardly in P2.

---

*Unofficial community tool. Built on Analyze Boston open data. Not affiliated with the City of Boston.*
