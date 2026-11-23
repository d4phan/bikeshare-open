# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-23 Add `cnt_roll_28` (mean cnt over d-28..d-1, `.shift(1)` then `.rolling(28)`). Available at prediction time: every input is from strictly before d. LAG_WARMUP 7 -> 28; `cnt_lag_7`/`cnt_roll_7` pinned to literal 7 so they do not stretch with it. Valid R^2 vs starter: ridge 0.6475 -> 0.6839 (+0.0364), hgb 0.2185 -> 0.2415 (+0.0230). On identical rows (controls for the 42 extra warm-up days dropped): ridge +0.0377, hgb +0.0486. Kept: both exceed the 0.01 noise bar.
- 2026-11-23 Classify the six raw label columns (`season`, `mnth`, `holiday`, `weekday`, `workday`, `weather`) as `RAW_LABEL_COLS` in FORBIDDEN: they are re-encoded or duplicated by calendar features, never fed raw. The new contract test found them unclassified on the starter. No metric changes (strings were never numeric features).
- 2026-11-23 Guard `data/raw/` with a SHA-256 check in `src.ingest.load_raw` (`RAW_SHA256` in config) plus `.gitattributes -text`. Seeded fault 4 showed a Bash `cp` bypasses the Edit/Write deny rules and the hook, and silently changed every test metric. Chosen over a PreToolUse Bash hook because it checks bytes, not command strings.
- 2026-11-23 Add `test_weather_encoder_rejects_unseen_labels`: seeded fault 3 (removing the `raise`) passed the whole starter suite and the hook.
- 2026-11-23 Exercise 4: `--target-transform diff28` in `src/train.py` (model cnt - cnt_roll_28, add it back; ridge and hgb only). Chosen on validation from 6 candidates (none, log, diff1, diff28, ratio7, ratio28): hgb valid R^2 0.2415 -> 0.6950, ridge 0.6839 -> 0.6932. ratio7 scored higher for hgb (0.7329) but dropped ridge to 0.4380, so rejected as tuned to the tree. Test touched once: hgb test R^2 -0.4600 -> 0.6335, MAE 1952.4 -> 731.8. Defensible as detrending against a level known at prediction time; not evidence that hgb beats ridge (R^2 gap 0.0015). Default pipeline and `reports/metrics.json` stay untransformed.
