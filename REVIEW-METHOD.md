# Review / Audit Method (reference)

**Owner:** Daniel Moreira
**Purpose:** how Daniel audits a codebase. A structured, evidence-based, multi-lane read that produces findings — **never** edits or commits. Synthesis and prioritization across lanes is the owner's job, done after the lanes are complete.

Use this when asked to "audit", "review", "assess", or "find issues in" a codebase.

---

## Ground rules

- **No edits, no commits during an audit.** An audit produces findings; fixing is separate work.
- **Evidence over intent.** Rank and claim from what the code actually does — code patterns, test investment, real snippets — not from comments or stated goals. List counter-evidence where a claim is disputed by behavior.
- **Verified-absence.** Every "no test/handler/guard exists for X" claim is backed by a grep run *this session*. A zero-match result is a falsification attempt, not an assumption.
- **Lane discipline.** Each lane states up front what it does **not** produce, so lenses don't bleed. Cross-reference a prior lane's finding where a new lens adds a distinct angle, but do **not** re-flag it as a new finding.
- **State the bar.** Say the quality bar at the top (e.g. "open-source-ready: the issues a future external contributor would notice, not stylistic nits").

---

## The four lanes (run in order)

**Lane 0 — Inventory & Context.** The map. For each module: purpose, public surface, outbound deps, inbound deps. Then: architectural quanta (deployable units), a conventions digest (rules + stack + workflow norms in one place), forward-looking constraints (what the next task will stress), and open questions for later lanes. End with a methodology note: what was read, what was **not** read and why, and the limits of the pass.

**Lane 1 — Clean Code & Craft.** Lenses: Clean Code (naming, function length, single-level-of-abstraction, comment quality, output channels), SOLID (SRP and DIP primary, OCP where it genuinely applies), Clean Architecture (the Dependency Rule — source-code dependencies point inward toward policy). Finding-id prefix: `CC-`.

**Lane 2 — Architecture & Fitness.** Lenses: architectural characteristics (the "-ilities"), fitness functions as executable architectural assertions, module coupling (afferent/efferent), evolvability under the next task's pressure. Produce a characteristics ranking by evidence with counter-evidence. Finding-id prefix: `AF-`.

**Lane 3 — Testability & Evolvability.** Lenses: TDD seam analysis (where are the injection points; which paths no test can currently reach?), EDD gate analysis (can the eval infra even express the requirements?), test evolvability (will the current fixtures/conftest support the tests the next task needs?). Resolve the open questions inherited from Lanes 0–2 with direct evidence.

---

## Finding format (every finding, every lane)

```
### <ID>: <one-line title> — <file:lines>

**Location(s):** <path:line-range>, ...
**Lens(es):** <which lens(es) surfaced this>

**Evidence:**
    <real code snippet copied from the file>

**The smell:** <what's wrong and which principle it breaks, in plain language>

**Why it matters now:** <tie it to the next planned task or a concrete risk —
not abstract purity>

**Recommended fix:** <specific, actionable; show the shape of the fix>

**Cost:** S (≤30 min) | M (~half day) | L (≥ half day; lists what it touches)

**Priority:** must-fix | should-fix | nice-to-have | defer-as-TD
```

Notes on the scales:
- **Cost** is wall-clock effort, and for `L` you name the files it spreads across.
- **Priority** `defer-as-TD` means "real, but no active reason to act yet" — it becomes a `TD-NNN` entry rather than work.

---

## Required sections per lane report

1. **Methodology** — lenses applied, the bar, files actually read this session, and explicitly "what this lane does NOT produce."
2. **Findings** — in the format above.
3. **Non-Findings** — honest accounting: modules you opened and found clean, named, with one line on why they're fine. This is as important as the findings; it proves coverage.
4. **Forward-Looking Notes** — how the findings bear on the next planned task.
5. **Open Questions** — observations that need cross-lane input; passed to the next lane or to synthesis. Questions only, no answers.

---

## After the lanes

Synthesis — deduping, ranking across lanes, and deciding what to actually do — is done by Daniel, not inside a lane. The lanes feed it; they don't pre-empt it.
