# HENLA External Validation Protocol (EXT)

## Objective
To transition HENLA from an internally-validated architectural prototype to an externally-validated cognitive system.

## Principles
- **No Self-Authoring**: Benchmarks must be sourced from independent repositories or unseen datasets.
- **Baseline Comparison**: All results must be compared against standard LLM-agent frameworks (e.g., AutoGPT, LangChain agents).
- **Public Auditability**: All episode logs and reasoning traces must be made available for external review.

---

## EXT-1 — Core Code Freeze
**Action:** Lock the `core/` directory. No new modules or "optimizations" allowed during the validation phase to prevent overfitting to test cases.

## EXT-2 — Claim Boundary Formalization
**Action:** Publish the list of "Prohibited Claims" and "Internal Status Labels" to align expectations with reality.

## EXT-3 — Blind Benchmarking
**Action:** Execute tasks on 50+ diverse, real-world repositories (randomly selected from GitHub) that were not used during development.

## EXT-4 — Hidden Task Execution
**Action:** Perform tasks where the goal or constraints are provided by an independent human supervisor without the developer's knowledge.

## EXT-5 — External Peer Review
**Action:** Submit the architecture and internal suite results for review by independent AI safety and cognitive science researchers.

## EXT-6 — Baseline Comparison Suite
**Action:** Run identical tasks on HENLA and 3 competing agent frameworks. Measure:
- Error recovery rate.
- Reasoning trace transparency.
- Resource consumption efficiency.
- Hallucination frequency.

## EXT-7 — Failure Mode Documentation (The "Anti-Log")
**Action:** Create a comprehensive report detailing every failure encountered during external testing, categorized by root cause.

## EXT-8 — Final Scientific Paper
**Action:** Synthesize findings into a formal technical paper for publication, focusing on the architectural trade-offs of the symbolic-experiential approach.
