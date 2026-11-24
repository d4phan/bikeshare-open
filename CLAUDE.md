# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make data` - download raw CSV, check its SHA-256, assert its shape
- `make features` - build `data/processed/features.parquet`
- `make train` - fit models, write `reports/metrics.json`
- `make test` - pytest; run this before claiming anything works
- `make all` - the three pipeline stages in order; reproduces every number
  in REPORT.md (headline: ridge test R^2 in `reports/metrics.json`)

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `src/config.py` lists these and the
  other excluded columns (`cnt_2d_bfr`, raw time indexes) with the reason
  for each. Derive feature lists from `FORBIDDEN`; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`.
  Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
- Any new lag or rolling feature must be built on a gap-free calendar
  index (`src.features.reindex_to_calendar`) and must `.shift(1)` before
  it aggregates. Add a test for it in `tests/test_leakage.py`.
- `LAG_WARMUP` is the *longest* window (now 28, for `cnt_roll_28`). Write
  every other window length as a literal; never derive one from it.
- A new raw column must be classified in `src/config.py` (a FORBIDDEN set
  with its reason, or a feature) or `test_every_raw_column_is_classified`
  fails. Do not silence it by widening the test.
- `data/raw/` is immutable by any route, Bash included. `load_raw` checks
  `RAW_SHA256`; if it fails, `git checkout -- data/raw/`, never re-hash.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) alongside every model. A negative R^2 is a finding, not a bug
  to hide.

## Agent tooling
- `/new-feature` adds a predictor test-first; `/seed-fault <fault>` breaks
  the pipeline on purpose and logs evidence to `docs/SEEDED_FAULTS.md`.
- `reports/metrics.json` is always the untransformed pipeline.
  `--target-transform diff28` (Exercise 4) writes `metrics_diff28.json`.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Modules are runnable: `python -m src.<module>` prints a one-line `OK ...`
  summary.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- The mirror in `DATA_URL` is missing 2011-03-10. It is NOT the UCI file:
  728 rows from 2011-01-03, not 731 from 2011-01-01.
- `weather` uses the labels `GOOD` / `MISTY` / `BAD`, not the UCI codes 1-4.
- Ridership grew ~65% from 2011 to 2012, so tree models trained on 2011
  cannot extrapolate to 2012. That is the headline result, not an error.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set. Expect it in
  any residual plot.
