# HENLA Reproducibility Guide

## Setup
1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Verification
To verify the internal architectural consistency of HENLA, run the following suites:

### 1. Basic Unit Tests
```bash
python -m pytest
```

### 2. Architectural Benchmarks (Internal)
Run the stage runners to regenerate the internal results:
```bash
# Robustness & Meta-Reasoning
python -m benchmarks.run_robustness_suite
python -m benchmarks.run_rsi_suite

# Deployment & Impact
python -m benchmarks.run_deployment_suite
python -m benchmarks.run_post_deployment_suite

# Knowledge Civilization
python -m benchmarks.run_knowledge_scaling_suite
```

## External Validation (EXT)
To run the external validation suite against a new repository:
```bash
python -m benchmarks.run_external_validation_suite --target_path /path/to/repo
```

## Expected Outputs
Results are written to `.benchmark_runs/`. Each run produces a JSON report with a `passed` status and the `verdict` as defined in the technical report.
