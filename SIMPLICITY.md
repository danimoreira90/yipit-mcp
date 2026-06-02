# Simplicity & Anti-Overengineering (reference)

**Owner:** Daniel Moreira
**Purpose:** the rules to follow *while building*, so code stays simple and doesn't grow weight it doesn't need. `REVIEW-METHOD.md` is how Daniel *audits* code after the fact; this doc is how an agent *writes* it in the first place.

**The bar:** the best code is the code you didn't write. Build exactly what the spec asks (HR-2 at the code level), prefer the boring obvious solution, and earn every abstraction.

---

## 1. Core principles

**YAGNI — You Aren't Gonna Need It.** Don't build for a future that isn't in the spec. No knobs, layers, or hooks for "when we later need X."
*Plain example:* the spec says "store bills locally." You do **not** add a `StorageBackend` interface with a Postgres adapter "in case we go multi-user." One backend, one concrete class. When a second backend is real, you abstract — not before.

**Rule of three.** Don't abstract until the third real use. Two similar things are a coincidence; three is a pattern.
*Plain example:* two functions share four lines. Leave them. A third shows up doing the same four lines — now extract a helper. Extracting at two often produces the *wrong* shape, because you guessed the variation.

**Prefer duplication over the wrong abstraction.** A little copy-paste is cheaper to fix than a bad abstraction everyone now depends on. WET beats premature DRY.

**Delete before you add.** The first question on any change is "can I remove something instead?" Less surface = fewer bugs, less to test, less to read.

**One reason to change (SRP).** A unit should do one job. If you change it for two unrelated reasons, split it.

**Depend inward, on abstractions — but only where variation is real (DIP / Dependency Rule).** Don't introduce an interface for a thing that has, and will have, exactly one implementation. An interface with one implementer is overhead, not flexibility.

**One level of abstraction per function.** A function body should read at a single altitude — either high-level steps or low-level detail, not both mixed.

---

## 2. The smells — and the plain version of each

These are the recurring things Daniel flags. Avoid creating them.

**Speculative generality.** Config options nobody sets, plugin systems with one plugin, "future-proof" parameters. *Smell:* you're solving a problem you don't have yet.

**Framework wired at the wrong layer.** Building a heavy client (LLM, DB, HTTP) eagerly at module scope, so importing the module has side effects and every test must set up secrets.
*Plain example:* `_llm = ChatAnthropic(...)` at the top of a module means any file that imports it triggers a real client and needs an API key — even a test that touches none of it. Fix: a lazy factory `build(llm)` called at the entry point. *Simpler is also more testable.*

**God function / flat script.** One long block doing bootstrap + config + state + rendering + event handling at once. No seams, so nothing can be tested in isolation.
*Plain example:* a 95-line UI script with zero functions. Extract `bootstrap()`, `render()`, `handle(input)` — behavior identical, now each is testable and readable.

**Orchestration leaking into the domain.** Putting a workflow flag (`needs_confirmation`, retry policy, conflict handling) inside a pure data model or domain function. That gives the model two reasons to change.
*Plain example:* the parser should return the parsed object or raise. Retry, confidence thresholds, and dedup belong in the *tool wrapper*, not in the parser.

**Magic numbers + shotgun surgery.** A literal repeated in code and encoded again in a name, so changing it means edits in several places.
*Plain example:* `_warned_50` / `_warned_80` flags plus literal `0.5` / `0.8`. Change 0.8 to 0.75 and you must rename the flag, edit the literal, and fix the log string. Fix: a `THRESHOLDS = (0.5, 0.8)` tuple and a loop — adding a threshold is a one-token change.

**Hardcoded value not derived from the data.** Printing `× 3 attempts` as a literal while the real attempt count lives in a variable, so they can silently drift apart. Derive the output from the source of truth.

**Hand-maintained parallel lists.** A list you must remember to update by hand every time you add a thing (e.g. an `ALL_TOOLS` list). Merge risk grows with every addition. Prefer a single registration point.

**Over-mocking.** Mocking so much that the test passes without exercising real behavior — or mocking the thing under test. Mock the outside world only.

---

## 3. The "why now" gate

Before adding **any** abstraction, layer, option, interface, or dependency, it must pass one of these:

1. the current spec needs it, **or**
2. there is a second real caller *today*.

If neither is true: **don't add it.** If it's a real future need but not yet: log it as `defer-as-TD` in `docs/tech-debt.md` and move on — don't build it speculatively.

This is the same gate Daniel's audits use to rank fixes: complexity must pay rent *now*, not in an imagined future.

---

## 4. Decision checklist (run before writing the code)

- Can I **delete** something instead of adding?
- Does the **spec** actually ask for this?
- Is there a **second real caller** right now? (If no → no abstraction yet.)
- Is this the **boring** solution? If I'm reaching for something clever, why — in one line?
- Will this make the **next task harder to test**? (Eager singletons, hidden side effects, missing seams.)
- Am I about to hand-maintain a parallel list or duplicate a literal? (Find the single source of truth.)

---

## 5. Applied to tools / MCP servers

The same rules govern tool design (this project is MCP/agent-centric):

- **One tool, one job.** A tool is a thin wrapper over a pure function. The domain logic must be testable with no MCP and no LLM in the loop.
- **No tool framework before ~3 tools exist.** Register tools the simple explicit way until the pattern actually repeats, then extract a registry — rule of three.
- **Keep computation in the function, not the prompt** (HR-5). The model selects and narrates; it does not compute. This is both a correctness rule and a simplicity rule — less logic smeared across prompt text.

---

## 6. When to stop

Refactor in service of the next task, not for purity. A smell with no active reason to bite this sprint is a `defer-as-TD` entry, not work. Simplicity includes *not* gold-plating the cleanup either.
