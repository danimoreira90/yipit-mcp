# Engineering Standards (reference)

**Owner:** Daniel Moreira
**Purpose:** the full protocol behind the short rules in `CLAUDE.md` / `AGENTS.md`. This is a reference document — agents read it when they need detail, not on every turn.

---

## 1. The loop: Spec → Build → Eval

Every non-trivial unit of work moves through three phases. Don't skip ahead.

1. **Spec (SDD).** Write `SPEC.md` answering *what* and *why* before any code. Then `PLAN.md` answering *in what order*. Code is the last step, not the first.
   - *Plain example:* before writing a parser, the spec says "extract these 6 fields, reject malformed input with a typed error, never crash on a missing field." The plan says "model first, then happy-path parse, then failure modes, then wiring."
2. **Build (TDD).** Failing test first, then minimum code to pass, then refactor.
3. **Eval (EDD).** For anything an LLM decides, an eval suite gates the merge.

---

## 2. TDD — Test-Driven Development

**RED → GREEN → REFACTOR.**

- **RED:** write the failing test first and **show its failing output**. A test that was never seen failing is not trusted.
- **GREEN:** write the *minimum* production code to pass. No extra features.
- **REFACTOR:** clean up with the test still green.
- **Commit pair:** `test: ...` then `feat: ...` (commits run by Daniel — HR-1).

*Plain example:* you want a function that rejects a bad date. First write `assert raises(ValueError)` and run it — it fails because the function doesn't exist yet. That red is the proof the test can fail. Then write just enough to make it green.

**Mocking rule:** mock the outside world (network, paid APIs, clock, filesystem when needed). **Never mock the function under test.** If you find yourself mocking the thing you're testing, the test proves nothing.

---

## 3. EDD — Eval-Driven Development *(LLM/agent work only)*

For every capability the model performs (each tool, each decision), an eval exists **before** the AI code.

- **Baseline first:** run the eval against nothing/stub and confirm it fails. Same logic as RED.
- **Gates to ship:**
  - Capability suite: `pass@3 ≥ 0.90` (the capability succeeds in at least 90% of 3-attempt runs).
  - Regression suite: `pass^3 = 1.00` (must pass every attempt, every time — no flakiness allowed in things that already worked).
- Evals live as fixtures (e.g. JSONL) plus a runner. Regression fixtures are **append-only** — you add new guards, you don't quietly delete old ones.

*Plain example:* before shipping a "summarize the bill" tool, you write 4 example bills with known correct answers. The tool ships only when it gets them right 9 times out of 10 and never regresses the ones that already passed.

---

## 4. Anti-Cheat — test integrity

The whole point of tests and evals is to tell the truth about the code. Anything that fakes a green is forbidden.

Forbidden moves (the taxonomy):
- Adding `@pytest.mark.skip`, `xfail`, or `skipif(True, ...)` to make a red go away.
- Softening an assertion (`assert x == 5` → `assert x > 0`) so it stops catching the bug.
- Replacing a specific mock with a catch-all `Mock()` that swallows everything.
- Mocking the function under test.
- Deleting or editing an existing test to dodge a failure (HR-4 — needs approval + tech-debt entry).
- Reporting "tests pass" without showing the actual run.

If a test legitimately must change, that is a decision Daniel makes, logged as `TD-NNN` in `docs/tech-debt.md` with the reason.

---

## 5. Verification & Honest Reporting

"Done" means *you ran it and showed the output*. Never claim a result you didn't observe.

Before requesting a commit, show, in full and unparaphrased:
1. `git diff --cached`
2. the test command + complete terminal output
3. coverage output if relevant
4. eval runner output for LLM features (`pass@3`, `pass^3`)
5. the list of Protected Paths touched

If something failed, say so plainly and propose a production-code fix. Do not narrate success over a failure.

---

## 6. Conventions

**Commits (Conventional Commits):** `feat / fix / chore / docs / refactor / test / perf / ci`, scope in parentheses, e.g. `feat(parser): add date validation`. No AI attribution. Run by Daniel only.

**Branch roles** — the prefix answers "what *type* of change is this?":

| Prefix | When |
|---|---|
| `feature/<name>` | new capability, page, or module |
| `data/<name>` | new external data source / format adapter |
| `quality/<name>` | tests, evals, docs, ADRs, observability |
| `infra/<name>` | CI/CD, deploy, secrets, monitoring |
| `bugfix/issue-<n>-<name>` | a pointed fix tied to an issue |
| `chore/<name>` | deps, configs, refactor with no behavior change |

**ADRs:** non-trivial decisions get a short record in `docs/adr/` (context → decision → consequences). Approved ADRs are immutable; to revise, write a new one.

**Tech-debt log:** `docs/tech-debt.md`, every entry has an id `TD-NNN`, a one-line summary, and why it was accepted.

**Language:** English throughout — UI strings, code, identifiers, schema, tests, ADRs, docs (US-facing assessment; no second user language on this project).

**Migrations** *(if DB)*: `YYYYMMDD_NNNN_name.sql`, forward-only, immutable once applied.

**Solo-work git flow:** branch → push → fast-forward merge to main → push → delete branch. No PRs when working alone.

---

## 7. House style for the docs themselves

When you (the agent) write specs, plans, ADRs, audits, or summaries:
- Lead with evidence, not intent. "The code does X (here)" beats "the code should do X."
- State the quality bar up front (e.g. "open-source-ready").
- Keep a plain-language version available for anything architectural (`architecture-plain.md`).
- Add an honest "caveats" or "non-findings" section — say what you did **not** check and why.
- No trial-and-error in production; reasoning and options go in the doc, not in throwaway code.
