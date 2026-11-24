# analysis/

Scripts behind the REPORT.md numbers that `make all` does not print. Each reads
`data/processed/features.parquet`, so run `make features` first, then from the repo root:

    PYTHONPATH=. python analysis/<script>.py

- `feature_ablation.py`: Exercise 1 same-rows control (validation only)
- `ex4_target_candidates.py`: the six Exercise 4 targets (validation only; never reads test)
- `range_check.py`: the 56.5% above-2011-max and 63% growth figures in the headline
- `ex5_ridge_vs_persistence.py`: the Exercise 5 error diagnostics
