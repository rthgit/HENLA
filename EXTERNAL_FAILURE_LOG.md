# HENLA External Failure Log

Every failure encountered during the External Validation phase (EXT) must be documented here.

## Failure Log Entries

| Task ID | Failure Mode | Root Cause | Affected Claim | Fix/No-Fix |
| :--- | :--- | :--- | :--- | :--- |
| *Template* | *e.g. Infinite loop* | *e.g. Unseen symlink cycle* | *Robustness* | *No-Fix (Freeze)* |

## Categories of Failure
- **Environment Incompatibility**: Failure to handle external OS/Filesystem configurations.
- **Logic Breakdown**: Meta-reasoning produces incorrect or unsafe plans.
- **Epistemic Failure**: Misclassification of external knowledge claims (e.g. hallucination).
- **Resource Exhaustion**: Cognitive budget exceeded due to unseen task complexity.
