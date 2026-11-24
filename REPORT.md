# Bikeshare demand: methodology report

Daily Capital Bikeshare ridership (`cnt`), Washington DC. Train = 2011 (306 days, after dropping
rows without 28 days of history), validation = H1 2012 (182 days), test = H2 2012 (184 days).
After `pip install -r requirements.txt`, `make all` reproduces `reports/metrics.json`;
`python -m src.train --target-transform diff28` reproduces Exercise 4; the other numbers come from the
scripts in `analysis/` (see its README).

## Results

The "after" rows are `reports/metrics.json` exactly as `make all` writes it. The "before" rows are the
unmodified starter (first commit), saved as `reports/metrics_before_feature.json`.

| Model | Feature set | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| `baseline_mean` | before (starter, 14 features) | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| `baseline_mean` | after (+ `cnt_roll_28`, 15 features) | -0.6894 | 1877.3 | -1.7717 | 2659.6 |
| `baseline_persistence` | before (starter, 14 features) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| `baseline_persistence` | after (+ `cnt_roll_28`, 15 features) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| `ridge` | before (starter, 14 features) | 0.6475 | 832.9 | 0.5833 | 947.1 |
| `ridge` | after (+ `cnt_roll_28`, 15 features) | 0.6839 | 777.5 | 0.6239 | 879.3 |
| `hgb` | before (starter, 14 features) | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| `hgb` | after (+ `cnt_roll_28`, 15 features) | 0.2415 | 1296.6 | -0.46 | 1952.4 |

The feature also raises `LAG_WARMUP` from 7 to 28, which drops 42 more 2011 days from training
(21 at the start of the data and 21 after the missing 2011-03-10).
The mean baseline moves only because of that. To separate the two effects, I compared the same 672
rows with and without the feature (validation only): ridge 0.6462 → 0.6839 (+0.0377), hgb
0.1929 → 0.2415 (+0.0486). The persistence baseline is unchanged because it uses no training data.

## Headline finding

**Daily ridership is forecastable, but only modestly better than "yesterday again", and the default tree model scores below zero on test.**
The naive evaluation, with `casual` and `registered` as inputs, gives test R² 1.000 and is invalid:
those two columns sum to `cnt` (`python -m src.leakage_demo`). Under the temporal split, the mean
baseline is strongly negative (test R² -1.7717) because mean daily ridership grew 63% from 2011 to 2012.
Ridge regression reaches test R² 0.6239 against a persistence baseline of
0.5099, yet it is *worse* than persistence on MAE (879.3 vs
840.1 rides/day). Gradient boosting fails differently: its test R² is negative (-0.46) yet it still beats the mean
baseline comfortably (-1.7717). A tree cannot predict above the largest count it saw, and 104 of the
184 test days (56.5%) exceed the 2011 maximum of 6,043 rides. Negative R² and losing to a baseline are
different findings, and both are reported here, not hidden. **The added
feature, `cnt_roll_28` (mean ridership over the 28 days before *d*), raised validation R² by +0.0364
for ridge and +0.0230 for hgb, and ridge's test R² from 0.5833 to 0.6239; I kept it.**

## Exercise 4: target transformation

**Claim to test.** Ridge beats the tree because of the growth trend, not because the tree learned less.
If so, a target that removes the trend should let hgb compete.

**Method (validation only).** I tried six targets for ridge and hgb, each inverted before scoring:
`cnt`, `log cnt`, `cnt − cnt_lag_1`, `cnt − cnt_roll_28`, `cnt / cnt_roll_7`, `cnt / cnt_roll_28`.
Validation R² for hgb: 0.2415, 0.1840, 0.6138, **0.6950**, 0.7329, 0.6754. For ridge: 0.6839, 0.3740,
0.6837, **0.6932**, 0.4380, 0.4039. A log target does not help: it compresses the scale but does not
remove the level shift. Every target that subtracts or divides out a *recent level* does help.

**Choice.** `diff28`: model today's departure from the trailing four-week level, then add the level
back. `ratio7` scored higher for hgb, but it was the best of six tries on 182 days, and it cut ridge
from 0.68 to 0.44. A target that helps one model and breaks the other is tuned to the comparison.
`diff28` improves both models, and only it was carried forward. Code: `python -m src.train
--target-transform diff28` (baselines are not transformed). **The test set was touched once, after the
choice was fixed**, and the output is committed as `reports/metrics_diff28.json`:

| Model | Target | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| `ridge` | cnt | 0.6839 | 777.5 | 0.6239 | 879.3 |
| `ridge` | cnt − cnt_roll_28 | 0.6932 | 761.3 | 0.635 | 856.7 |
| `hgb` | cnt | 0.2415 | 1296.6 | -0.46 | 1952.4 |
| `hgb` | cnt − cnt_roll_28 | 0.695 | 716.2 | 0.6335 | 731.8 |

**Is it defensible? Yes, as a detrending, but not as a win for the tree.** The inverse uses only
`cnt_roll_28`, which is built from days *d*−28 to *d*−1, so it adds no leakage. It also matches the
mechanism: a forecaster really does know the recent level, and the tree only has to learn deviations,
which look the same in 2011 and 2012. hgb's test R² goes from −0.46 to 0.6335 and its MAE (731.8) is
the best of any model. But the R² gap to ridge under the same target is 0.0015, and the transform was
picked after looking at validation. So the honest conclusion is that hgb's failure was caused by the
trend, **not** that hgb beats ridge. The committed `reports/metrics.json` stays untransformed.

## Exercise 5: ridge vs persistence

**Position: do not deploy ridge as it stands. Deploy it once its level bias is fixed.** On test, ridge
leads persistence by 0.114 R² but trails it by
39.2 rides/day of MAE. Both numbers are true, and they measure different days. On the
32 test days where ridership moved more than 1,500 from the day before (mostly weekend/weekday
switches and weather changes, plus Hurricane Sandy on 10-29 and the rebound on 10-31, and Thanksgiving), ridge's MAE is 1,470.6 against persistence's 2,413.2. That is where R²,
which squares errors, rewards it. On the other 152 days, ridge is worse: 754.8 vs 508.9. Its median
absolute error is 806.5 vs 506.5, and it is closer than persistence on only 42.9% of days. The reason
is a systematic bias: ridge under-predicts by **+426.7 rides/day on average** (persistence: −16.1).
It is the same trend problem as Exercise 4, scaled down, since ridge is fit on 2011 levels. An operator
rebalancing docks every day mostly lives on the typical days, and on those, "yesterday again" is
better and free. Ridge's real value, fewer days off by more than 2,000 rides (10 vs 17), is worth
having, but not at a known 427-ride bias on every other day. The `diff28` ridge (test MAE 856.7)
still loses on MAE, so detrending alone does not settle it. The next step is to correct the bias
(re-fit on a rolling window, or blend with persistence) and require ridge to win on **both**
metrics on validation before deploying. These diagnostics are evaluations of already-fitted models;
nothing was tuned on them.

## Attribution

**Model: Claude Opus 5.5 (Anthropic, hosted) for building the repo; `qwen3.5:9b` (9.0B, Q4_K_M) via Ollama, 64k context, as `bikeshare-coder` for the Exercise 3 audits. Switched models: yes.**

The work ran in a hosted agent session on a machine with 7 GB of RAM, below the 16 GB minimum for the
local model. The feature followed the `/new-feature` skill's steps: test first, recorded red run,
validation delta, keep-or-drop. The skill was not invoked as a Claude Code slash command. The
PostToolUse hook was run with Claude Code's JSON payload rather than by Claude Code's hook runner
(see `docs/SEEDED_FAULTS.md`).

**Generated by the agent:**
- `src/features.py`: `cnt_roll_28`, and literal window lengths for `cnt_lag_7`/`cnt_roll_7`
- `src/config.py`: `RAW_LABEL_COLS`, `RAW_FEATURE_COLS`, `RAW_SHA256`, `LAG_WARMUP = 28`
- `src/ingest.py`: `verify_raw()`
- `src/train.py`: `TARGET_TRANSFORMS`, the `--target-transform` flag
- `tests/test_leakage.py`: `test_roll_28_is_mean_of_28_strictly_earlier_days`, `test_weather_encoder_rejects_unseen_labels`, `test_no_feature_restates_same_day_leakage`,
  `test_lag_7_is_a_true_7_day_calendar_lag`, `test_roll_28_uses_calendar_days_around_the_gap`
- `tests/test_contract.py`: `test_every_raw_column_is_classified`
- `.claude/skills/seed-fault/SKILL.md`, the `CLAUDE.md` edits, `.gitattributes`
- `docs/SEEDED_FAULTS.md`, the dated lines in `docs/DECISIONS.md`, and the first draft of this report
- `analysis/`: the scripts behind the ablation, Exercise 4 candidates, headline range check and Exercise 5 numbers

**Decisions that were mine** (each traces to a line in `docs/DECISIONS.md`):
<!-- DP: REVIEW BEFORE SUBMITTING. The agent proposed these. Keep only the ones you have checked
     and agree with, change any you would decide differently, and delete this comment. -->
- Keep `cnt_roll_28` (DECISIONS 2026-11-23, feature line)
- Use `diff28` for Exercise 4, reject `ratio7`, and call the transform defensible as detrending but
  not as a win for hgb (Exercise 4 line)
- The Exercise 5 position: do not deploy ridge until its bias is fixed (Exercise 5 line)
- Guard `data/raw/` with a hash check rather than a Bash PreToolUse hook (raw-guard line)
- Predict total daily `cnt`; treat `casual`/`registered` as leakage and exclude `cnt_2d_bfr` and the
  time indexes (starter DECISIONS lines 1-3, kept unchanged)
- Split by date 2011 / H1 2012 / H2 2012 and touch test once per result (starter line 4; Exercise 4 line)
- Report both baselines, and treat hgb's negative R² as believable (a trend effect, not a bug), on the
  evidence that detrending fixes it (starter line 5; Exercise 4 line)
