---
name: wrap
description: >
  Conclude the current session so a fresh one can continue seamlessly: sweep un-encoded learnings
  into the right repo docs, decide or confirm the next step (via /next when open), rewrite
  docs/STATE.md so it reflects the current work, commit, and push. Use when ending a session,
  before killing a long-context session, or on "wrap up", "conclude the session", "save state",
  "/wrap".
user_invocable: true
---

# Wrap (Conclude The Session)

The conclude-and-handoff ritual. After a wrap, this session is disposable: everything it learned
is in the repo, the next step is recorded with its why, and a fresh session boots straight into
continuing (per CLAUDE.md it reads `docs/STATE.md` first). Never let a session's value live only
in its context window.

## 1. Sweep Learnings Into Their Homes

Review the whole session for anything durable that isn't yet written down, and write each piece
to its proper home (per CLAUDE.md > "Project knowledge lives in the repo"):

| Kind of learning | Home |
|---|---|
| Design decisions, spec changes, deviations | the relevant `docs/*.md` (decisions, mechanical, parts, electrical, controls, build) |
| Part selection / order / receipt changes | `bom/bom.csv` (+ `bom/README.md` if conventions change) |
| Test results and sign-offs | `testing/test-matrix.csv` |
| Measured motor/bench data (R, L, BEMF, thread depths, bore diameters) | the doc that holds the provisional value, replacing or annotating it |
| Firmware behavior, register findings, toolchain gotchas | code comments in `firmware/` or `docs/controls.md` |
| A repeatable procedure | the matching `.claude/skills/` skill |
| Cross-cutting rules, preferences | `CLAUDE.md` |

Write the **content** there — STATE.md gets only pointers. A dead end is a finding too: recording
why something was ruled out is what stops the next session from re-treading it.

## 2. Decide Or Confirm Next

- Previous Next still the plan (done partially, or untouched)? Confirm and carry it forward,
  updated to reflect progress.
- Previous Next completed, or the session changed the picture? Run **`/next`** to decide and
  record properly. Don't freehand a big direction change here — that's what `/next`'s candidate
  analysis is for.

## 3. Rewrite STATE.md To Reflect The Work

Rewrite `docs/STATE.md` **wholesale** (overwrite, never append — git holds history). STATE is
about **the work**, not machine state — keep it to:

- **Now** — the current work picture in 3–6 bullets. Fold in what this session proved/landed.
- **Next** — from step 2, with the two-line why and doc pointer.
- **Candidates Not Chosen** — carry forward, pruning ones that landed or died.
- **Learned Recently** — pointers to what step 1 wrote, one line each.
- Update the "Last updated" date.

**Do not** add a git/tool/machine snapshot; it's busy-work that just goes stale.

## 4. Commit And Push

Commit the doc updates + STATE.md and push to `main` per the repo's conventions (keep the
firmware green first if code changed: `cargo fmt && cargo clippy && cargo build` in `firmware/`).

## 5. Sign Off

Print, roughly:

> Session wrapped: learnings encoded, STATE.md rewritten, committed, pushed. Safe to end this
> session. A fresh session reads docs/STATE.md first and picks up from Next.
