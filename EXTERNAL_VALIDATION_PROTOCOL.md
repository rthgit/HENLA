# HENLA External Validation Protocol (EXT) v1.0

## Objective
To transition HENLA from an internally-validated architectural prototype to an externally-validated cognitive system.

## Principles: "Don't Add Capacity, Add Verifiability"
- **No Self-Authoring**: Benchmarks must be sourced from independent repositories or unseen datasets.
- **Baseline Comparison**: All results must be compared against standard LLM-agent frameworks.
- **Public Auditability**: All reasoning traces must be available for external review.

---

## EXT-1 — Code-Blind Review
**Action:** Reviewer reads `core/` without developer explanation. 
**Goal:** Verify if the architecture is self-documenting and logically sound from a third-party perspective.

## EXT-2 — Random Repository Benchmarking
**Action:** Execute tasks on 10 random GitHub repositories with varying complexity.
**Goal:** Measure generalization beyond the author's coding patterns.

## EXT-3 — Hidden Task Packet
**Action:** A supervisor provides a set of tasks (triage, refactor, debug) whose details are unknown to the developers until the run starts.

## EXT-4 — Baseline Comparison (Battle Royale)
**Action:** Compare HENLA vs. (1) Simple Heuristic, (2) LLM+Tool, (3) Agent Framework.
**Metrics:** Completion, False Claim Rate, Recovery, Cost/Tokens, Staleness detection.

## EXT-5 — Mandatory Failure Report
**Action:** Every external failure must be logged in `EXTERNAL_FAILURE_LOG.md` with root cause analysis.

## EXT-6 — Claim Revision
**Action:** Based on results, update `CLAIM_BOUNDARY.md`. If a pending claim fails, it is moved to "Falsified" or "De-prioritized."

---

## Final External Verdicts
- `fails_to_reproduce`: Internal claims cannot be replicated by others.
- `reproduces_internal_claims`: Performance matches internal suites but lacks external generalization.
- `passes_limited_external_tasks`: Shows utility in narrow external domains.
- `shows_external_generalization`: Demonstrates robust performance on diverse, unseen tasks.
