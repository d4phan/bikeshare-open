# Seeded faults (Exercise 2)

Faults 1-3 were each committed in their broken state and then fixed in a later commit (fault 3 has a
new-test commit in between). Fault 4 was never committed broken: the tampered raw file was restored with
`git checkout -- data/raw/`, and the guard that catches it landed in one commit (see `git log`).
"`make test`" is the full output of `make test`. "Hook stderr" is the output of
`.claude/hooks/check_leakage.sh` given the PostToolUse JSON payload Claude Code sends after an
`Edit` of `src/features.py` (`{"tool_name":"Edit","tool_input":{"file_path":".../src/features.py"}}` on stdin,
`CLAUDE_PROJECT_DIR` set). The agent for this assignment ran outside the local Ollama/Claude Code
setup (see REPORT.md, Attribution), so the hook was invoked with that payload directly rather than by
Claude Code's hook runner. The script, payload and exit code are exactly what Claude Code would see.

"Agent turns to fix" counts the agent edits between the red run and the next green `make test`.

## Exercise 1: the feature test, red before the feature existed

`test_roll_28_is_mean_of_28_strictly_earlier_days` was committed before `cnt_roll_28` was built
(commit `Add failing test for cnt_roll_28`). `make test` at that commit:

```text
        >>> monotonic_index = pd.Index(list("abbc"))
        >>> monotonic_index.get_loc("b")
        slice(1, 3, None)
    
        >>> non_monotonic_index = pd.Index(list("abcb"))
        >>> non_monotonic_index.get_loc("b")
        array([False,  True, False,  True])
        """
        casted_key = self._maybe_cast_indexer(key)
        try:
            return self._engine.get_loc(casted_key)
        except KeyError as err:
            if isinstance(casted_key, slice) or (
                isinstance(casted_key, abc.Iterable)
                and any(isinstance(x, slice) for x in casted_key)
            ):
                raise InvalidIndexError(key) from err
>           raise KeyError(key) from err
E           KeyError: 'cnt_roll_28'

.venv/lib/python3.13/site-packages/pandas/core/indexes/base.py:3648: KeyError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_roll_28_is_mean_of_28_strictly_earlier_days
1 failed, 14 passed in 1.42s
make: *** [Makefile:16: test] Error 1
```

It fails for the right reason: the column does not exist yet. The next commit adds the feature, and
the test passes.

## Fault 1: forbidden column added to `feature_columns`

Change:

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..ca89ac4 100644
--- a/src/features.py
+++ b/src/features.py
@@ -86,7 +86,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

`make test` (red):

```text
python -m pytest tests/ -q
......F.........                                                         [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571

[672 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'holiday', 'instant', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 1.27s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr (exit 2):

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571

[672 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'holiday', 'instant', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.38s
```

Agent turns to fix: **1** (revert the `+ ["casual"]`). Commits `Seeded fault 1` / `Fix fault 1`.

## Fault 2: `.shift(1)` removed from `cnt_roll_7`

Change:

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..35fc12f 100644
--- a/src/features.py
+++ b/src/features.py
@@ -75,7 +75,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # Window lengths are literal: LAG_WARMUP is the *longest* window, so
     # tying these to it would silently stretch them when it grows.
     out["cnt_lag_7"] = out[TARGET].shift(7)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(7).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(7).mean()
     # Four-week demand level, known at prediction time for date d because
     # every input is from d-28 .. d-1. Sets LAG_WARMUP = 28.
     out["cnt_roll_28"] = out[TARGET].shift(1).rolling(28).mean()
```

`make test` (red):

```text
python -m pytest tests/ -q
.........F......                                                         [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....428571  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1789.857143  3969.428571

[672 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
E             
E             comparison failed
E             Obtained: 4605.285714285715
E             Expected: 4724.428571428572 ± 0.00472443

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 1.29s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr (exit 2; the hook prints the last 20 lines of pytest output, so it starts mid-traceback):

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
[672 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
E             
E             comparison failed
E             Obtained: 4605.285714285715
E             Expected: 4724.428571428572 ± 0.00472443

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.36s
```

Agent turns to fix: **1** (restore `.shift(1)` before `.rolling(7)`).

## Fault 3: `raise` removed from the weather encoder

Change:

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..5538e32 100644
--- a/src/features.py
+++ b/src/features.py
@@ -27,7 +27,7 @@ def encode_weather(series: pd.Series) -> pd.Series:
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
     if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+        pass
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

`make test`: **not red**. The suite passed with the fault in place:

```text
python -m pytest tests/ -q
................                                                         [100%]
16 passed in 1.28s
make test exit: 0
```

Hook stderr: none (exit 0):

```text
hook exit code: 0
--- hook stderr ---
```

**Why nothing fired:** the raw data contains only `GOOD`/`MISTY`/`BAD`, so the `raise` branch never
runs on real data and no starter test calls the encoder with an unseen label. Removing the guard is
invisible until a new label arrives upstream, and then `dropna()` deletes those days silently.

**Fix to the suite:** added `test_weather_encoder_rejects_unseen_labels` to `tests/test_leakage.py`
(so the hook runs it too). It calls `encode_weather(pd.Series(["GOOD", "SNOW", "MISTY"]))` and expects
`ValueError`. With the fault still in place:

`make test` (red):

```text
python -m pytest tests/ -q
...........F.....                                                        [100%]
=================================== FAILURES ===================================
__________________ test_weather_encoder_rejects_unseen_labels __________________

    def test_weather_encoder_rejects_unseen_labels():
        """An unseen label must raise, not become a NaN that dropna() later
        deletes without comment. The real data only has known labels, so
        without this test nothing exercises the raise."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:77: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unseen_labels - Fa...
1 failed, 16 passed in 1.17s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr (exit 2):

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
......F..                                                                [100%]
=================================== FAILURES ===================================
__________________ test_weather_encoder_rejects_unseen_labels __________________

    def test_weather_encoder_rejects_unseen_labels():
        """An unseen label must raise, not become a NaN that dropna() later
        deletes without comment. The real data only has known labels, so
        without this test nothing exercises the raise."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:77: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unseen_labels - Fa...
1 failed, 8 passed in 0.37s
```

Agent turns to fix: **2** (write the missing test, then restore the `raise`). Commits
`Seeded fault 3` (green, undetected) / `Add test_weather_encoder_rejects_unseen_labels` (red) / `Fix fault 3`.

## Fault 4: the one the hook cannot see (`cp` into `data/raw/` from Bash)

The agent replaced the raw file through a shell command with a "cleaned" copy that rewrites Hurricane
Sandy (2012-10-29) from 22 rides to 4,022. `registered` was raised by the same amount, so
`casual + registered == cnt` still holds.

What happened (before the fix below; the suite had 17 tests at that commit):

```text
$ sha256sum data/raw/bike_daily.csv
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
$ cp /tmp/bike_daily_cleaned.csv data/raw/bike_daily.csv
exit: 0
$ sha256sum data/raw/bike_daily.csv
e6d2a23ffc5971db865923cfa08f07f18bb4d7ac744e595ae1e4919de7e4def4  data/raw/bike_daily.csv
$ make test
.................                                                        [100%]
17 passed in 1.08s
$ make all  (test-set metrics, tampered file)
{'baseline_persistence': {'r2': 0.5028, 'mae': 828.4}, 'ridge': {'r2': 0.6244, 'mae': 856.6}, 'hgb': {'r2': -0.5534, 'mae': 1955.2}}
$ grep matcher .claude/settings.json
        "matcher": "Edit|Write",
# forcing the hook with the Bash tool payload anyway:
hook exit code: 0
--- hook stderr ---
```

- The `deny` rules `Write(./data/raw/**)` and `Edit(./data/raw/**)` only govern the Write and Edit
  tools, not a Bash command that writes the same path. Only `Bash(rm -rf:*)` is denied for Bash.
- The PostToolUse hook's matcher is `Edit|Write`, so Claude Code never runs it after a Bash call.
  Forced with the Bash payload, it finds no `file_path` and exits 0.
- All 17 tests pass on the tampered file, because none of them checks the file's identity. The pipeline
  runs, and every test-set number silently changes: ridge test MAE 879.3 -> 856.6 (R² 0.6239 -> 0.6244),
  persistence test R² 0.5099 -> 0.5028, hgb test R² -0.4600 -> -0.5534. No error appears anywhere.

**What would catch it:** a content check on the raw file, run by the pipeline itself. A
`PreToolUse` hook on `Bash` that rejects commands naming `data/raw/` would block the obvious case. But it
pattern-matches strings, so `cd data/raw && cp ...` or a Python one-liner slips past. A `Stop` hook that
runs `make test` only catches it if some test notices. `chmod -w data/raw` works until
something runs `chmod`. A hash check sees the bytes, however they got there.

**Implemented:** `RAW_SHA256` in `src/config.py`, and `src.ingest.verify_raw()` is called first in
`load_raw()`. Because every stage and every test fixture loads data through `load_raw()`, this
covers `make data`, `make all` and `make test` together. Replaying the same `cp` with the guard in place (re-run on the final 20-test suite):

```text
$ cp /tmp/bike_daily_cleaned.csv data/raw/bike_daily.csv
$ make data
    )
ValueError: bike_daily.csv sha256 e6d2a23ffc5971db... != expected a6bed1577f6e4de5...; data/raw is immutable. Restore it with: git checkout -- data/raw/
make: *** [Makefile:7: data] Error 1
$ make test
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: bike...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: bike_daily...
2 passed, 18 errors in 1.15s
make: *** [Makefile:16: test] Error 1
$ git checkout -- data/raw/ && make data
OK ingest: 728 rows, 2011-01-03 -> 2012-12-31
```

The catcher's diff (from commit `Seeded fault 4 ... add SHA-256 guard`, `git diff 0e4a2c3 3676597 -- src/config.py src/ingest.py .gitattributes`):

```diff
diff --git a/.gitattributes b/.gitattributes
new file mode 100644
index 0000000..b0d6f8d
--- /dev/null
+++ b/.gitattributes
@@ -0,0 +1 @@
+data/raw/*.csv -text
diff --git a/src/config.py b/src/config.py
index acdf187..850a85c 100644
--- a/src/config.py
+++ b/src/config.py
@@ -20,6 +20,11 @@ DATA_URL = (
     "interpretable-ml-book/master/data/bike.csv"
 )
 
+# SHA-256 of the checked-in raw file. src.ingest.load_raw refuses any other
+# bytes, so a raw file swapped in by a shell `cp` (which the Edit/Write deny
+# rules and the PostToolUse hook never see) fails `make data` and every test.
+RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
+
 TARGET = "cnt"
 
 # --- Three reasons a column is kept out of the feature set --------------
diff --git a/src/ingest.py b/src/ingest.py
index 6654075..009154e 100644
--- a/src/ingest.py
+++ b/src/ingest.py
@@ -2,12 +2,13 @@
 
 Run: python -m src.ingest
 """
+import hashlib
 import sys
 import urllib.request
 
 import pandas as pd
 
-from src.config import DATA_URL, RAW
+from src.config import DATA_URL, RAW, RAW_SHA256
 
 EXPECTED_MIN_ROWS = 700
 REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}
@@ -20,7 +21,17 @@ def download(force: bool = False) -> None:
     urllib.request.urlretrieve(DATA_URL, RAW)
 
 
+def verify_raw() -> None:
+    digest = hashlib.sha256(RAW.read_bytes()).hexdigest()
+    if digest != RAW_SHA256:
+        raise ValueError(
+            f"{RAW.name} sha256 {digest[:16]}... != expected {RAW_SHA256[:16]}...; "
+            "data/raw is immutable. Restore it with: git checkout -- data/raw/"
+        )
+
+
 def load_raw() -> pd.DataFrame:
+    verify_raw()
     df = pd.read_csv(RAW, parse_dates=["dteday"])
     missing = REQUIRED_COLS - set(df.columns)
     if missing:
```

`.gitattributes` marks `data/raw/*.csv` as binary (`-text`) so a Windows checkout with
`core.autocrlf` cannot rewrite line endings and trip the hash on an honest clone.

## Re-run against the final suite

The outputs above are what the suite printed when each fault was seeded, so their test counts are
those of that commit. Below, the same faults are re-seeded on the final code (20 tests), so the pasted
output matches what the tests print now. Each was reverted with `git checkout -- src/features.py`.

### Fault 1: forbidden `casual` in `feature_columns`

Now **3** tests go red: the name check, the contract test (the raw columns the model uses no longer
match the declared set) and the value-based leakage test.

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..ca89ac4 100644
--- a/src/features.py
+++ b/src/features.py
@@ -86,7 +86,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

`make test`:

```text
python -m pytest tests/ -q
..F...FF............                                                     [100%]
=================================== FAILURES ===================================
_____________________ test_every_raw_column_is_classified ______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571

[672 rows x 29 columns]

    def test_every_raw_column_is_classified(feats):
        """No column may enter silently. Every column in the raw CSV must be
        in FORBIDDEN (with a reason in src/config.py), be a declared raw
        feature (RAW_FEATURE_COLS), or be the date key. The declared set is
        hand-written on purpose: classifying against feature_columns() would
        pass any new numeric column, because that function admits it."""
        header = set(pd.read_csv(RAW, nrows=0).columns)
        classified = FORBIDDEN | RAW_FEATURE_COLS | {"dteday"}
        unclassified = sorted(header - classified)
        assert not unclassified, f"unclassified raw columns: {unclassified}"
        # The declarations must match what the model actually uses.
        used_raw = header & set(feature_columns(feats))
>       assert used_raw == RAW_FEATURE_COLS, (
            f"raw features used {sorted(used_raw)} != declared {sorted(RAW_FEATURE_COLS)}"
        )
E       AssertionError: raw features used ['atemp', 'casual', 'hum', 'temp', 'windspeed'] != declared ['atemp', 'hum', 'temp', 'windspeed']
E       assert {'atemp', 'ca..., 'windspeed'} == {'atemp', 'hu..., 'windspeed'}
E         
E         Extra items in the left set:
E         'casual'
E         Use -v to get more diff

tests/test_contract.py:58: AssertionError
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571

[672 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'holiday', 'instant', ...})

tests/test_leakage.py:32: AssertionError
__________________ test_no_feature_restates_same_day_leakage ___________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571

[672 rows x 29 columns]

    def test_no_feature_restates_same_day_leakage(feats):
        """test_no_forbidden_features checks names, which feature_columns()
        already guarantees, so a leaked column renamed to something innocent
        (`riders = casual`) passes it. This checks values: no feature may track
        a same-day leakage column almost exactly, and the features together
        must not reproduce cnt exactly. Legitimate features top out near 0.82
        correlation and a max least-squares residual in the thousands."""
        X = feats[feature_columns(feats)].astype(float)
        for col in sorted(LEAKAGE_COLS):
            corr = X.corrwith(feats[col].astype(float)).abs()
>           assert (corr < 0.99).all(), f"features restating same-day {col}: {corr[corr >= 0.99].round(4).to_dict()}"
E           AssertionError: features restating same-day casual: {'casual': 1.0}
E           assert np.False_
E            +  where np.False_ = all()
E            +    where all = temp                0.504360\natemp               0.504812\nhum                 0.105318\nwindspeed           0.165169\nda...         0.440896\ncnt_roll_7          0.534495\ncnt_roll_28         0.508815\ncasual              1.000000\ndtype: float64 < 0.99.all

tests/test_leakage.py:45: AssertionError
=========================== short test summary info ============================
FAILED tests/test_contract.py::test_every_raw_column_is_classified - Assertio...
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
FAILED tests/test_leakage.py::test_no_feature_restates_same_day_leakage - Ass...
3 failed, 17 passed in 1.36s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr:

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
        """test_no_forbidden_features checks names, which feature_columns()
        already guarantees, so a leaked column renamed to something innocent
        (`riders = casual`) passes it. This checks values: no feature may track
        a same-day leakage column almost exactly, and the features together
        must not reproduce cnt exactly. Legitimate features top out near 0.82
        correlation and a max least-squares residual in the thousands."""
        X = feats[feature_columns(feats)].astype(float)
        for col in sorted(LEAKAGE_COLS):
            corr = X.corrwith(feats[col].astype(float)).abs()
>           assert (corr < 0.99).all(), f"features restating same-day {col}: {corr[corr >= 0.99].round(4).to_dict()}"
E           AssertionError: features restating same-day casual: {'casual': 1.0}
E           assert np.False_
E            +  where np.False_ = all()
E            +    where all = temp                0.504360\natemp               0.504812\nhum                 0.105318\nwindspeed           0.165169\nda...         0.440896\ncnt_roll_7          0.534495\ncnt_roll_28         0.508815\ncasual              1.000000\ndtype: float64 < 0.99.all

tests/test_leakage.py:45: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
FAILED tests/test_leakage.py::test_no_feature_restates_same_day_leakage - Ass...
2 failed, 10 passed in 0.41s
```

### Fault 2: `.shift(1)` removed from `cnt_roll_7`

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..35fc12f 100644
--- a/src/features.py
+++ b/src/features.py
@@ -75,7 +75,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # Window lengths are literal: LAG_WARMUP is the *longest* window, so
     # tying these to it would silently stretch them when it grows.
     out["cnt_lag_7"] = out[TARGET].shift(7)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(7).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(7).mean()
     # Four-week demand level, known at prediction time for date d because
     # every input is from d-28 .. d-1. Sets LAG_WARMUP = 28.
     out["cnt_roll_28"] = out[TARGET].shift(1).rolling(28).mean()
```

`make test`:

```text
python -m pytest tests/ -q
..........F.........                                                     [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....428571  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1789.857143  3969.428571

[672 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
E             
E             comparison failed
E             Obtained: 4605.285714285715
E             Expected: 4724.428571428572 ± 0.00472443

tests/test_leakage.py:76: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 19 passed in 1.23s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr:

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
[672 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
E             
E             comparison failed
E             Obtained: 4605.285714285715
E             Expected: 4724.428571428572 ± 0.00472443

tests/test_leakage.py:76: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 11 passed in 0.41s
```

### Fault 3: `raise` removed from `encode_weather`

Now caught by `test_weather_encoder_rejects_unseen_labels`.

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..5538e32 100644
--- a/src/features.py
+++ b/src/features.py
@@ -27,7 +27,7 @@ def encode_weather(series: pd.Series) -> pd.Series:
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
     if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+        pass
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

`make test`:

```text
python -m pytest tests/ -q
..............F.....                                                     [100%]
=================================== FAILURES ===================================
__________________ test_weather_encoder_rejects_unseen_labels __________________

    def test_weather_encoder_rejects_unseen_labels():
        """An unseen label must raise, not become a NaN that dropna() later
        deletes without comment. The real data only has known labels, so
        without this test nothing exercises the raise."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:125: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unseen_labels - Fa...
1 failed, 19 passed in 1.19s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr:

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
.........F..                                                             [100%]
=================================== FAILURES ===================================
__________________ test_weather_encoder_rejects_unseen_labels __________________

    def test_weather_encoder_rejects_unseen_labels():
        """An unseen label must raise, not become a NaN that dropna() later
        deletes without comment. The real data only has known labels, so
        without this test nothing exercises the raise."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:125: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unseen_labels - Fa...
1 failed, 11 passed in 0.41s
```

### Extra: a leaked column renamed to something innocent, in code

`riders = casual` added in `build_features`. Before `test_no_feature_restates_same_day_leakage`
existed, this passed every test, because `test_no_forbidden_features` only checks names.

```diff
diff --git a/src/features.py b/src/features.py
index 156c919..4a81fb5 100644
--- a/src/features.py
+++ b/src/features.py
@@ -79,6 +79,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # Four-week demand level, known at prediction time for date d because
     # every input is from d-28 .. d-1. Sets LAG_WARMUP = 28.
     out["cnt_roll_28"] = out[TARGET].shift(1).rolling(28).mean()
+    out["riders"] = out["casual"]
 
     return out.dropna().reset_index(drop=True)
 
```

`make test`:

```text
python -m pytest tests/ -q
.......F............                                                     [100%]
=================================== FAILURES ===================================
__________________ test_no_feature_restates_same_day_leakage ___________________

feats =         dteday  instant  season  ...   cnt_roll_7  cnt_roll_28 riders
0   2011-01-31     31.0  WINTER  ...  1099.85714...2857  4071.321429  364.0
671 2012-12-31    731.0  WINTER  ...  1531.428571  3969.428571  439.0

[672 rows x 30 columns]

    def test_no_feature_restates_same_day_leakage(feats):
        """test_no_forbidden_features checks names, which feature_columns()
        already guarantees, so a leaked column renamed to something innocent
        (`riders = casual`) passes it. This checks values: no feature may track
        a same-day leakage column almost exactly, and the features together
        must not reproduce cnt exactly. Legitimate features top out near 0.82
        correlation and a max least-squares residual in the thousands."""
        X = feats[feature_columns(feats)].astype(float)
        for col in sorted(LEAKAGE_COLS):
            corr = X.corrwith(feats[col].astype(float)).abs()
>           assert (corr < 0.99).all(), f"features restating same-day {col}: {corr[corr >= 0.99].round(4).to_dict()}"
E           AssertionError: features restating same-day casual: {'riders': 1.0}
E           assert np.False_
E            +  where np.False_ = all()
E            +    where all = temp                0.504360\natemp               0.504812\nhum                 0.105318\nwindspeed           0.165169\nda...         0.440896\ncnt_roll_7          0.534495\ncnt_roll_28         0.508815\nriders              1.000000\ndtype: float64 < 0.99.all

tests/test_leakage.py:45: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_feature_restates_same_day_leakage - Ass...
1 failed, 19 passed in 1.29s
make: *** [Makefile:16: test] Error 1
make test exit: 2
```

Hook stderr:

```text
hook exit code: 2
--- hook stderr ---
Leakage tests failed after editing /home/claude/work/bikeshare-open/src/features.py:
    def test_no_feature_restates_same_day_leakage(feats):
        """test_no_forbidden_features checks names, which feature_columns()
        already guarantees, so a leaked column renamed to something innocent
        (`riders = casual`) passes it. This checks values: no feature may track
        a same-day leakage column almost exactly, and the features together
        must not reproduce cnt exactly. Legitimate features top out near 0.82
        correlation and a max least-squares residual in the thousands."""
        X = feats[feature_columns(feats)].astype(float)
        for col in sorted(LEAKAGE_COLS):
            corr = X.corrwith(feats[col].astype(float)).abs()
>           assert (corr < 0.99).all(), f"features restating same-day {col}: {corr[corr >= 0.99].round(4).to_dict()}"
E           AssertionError: features restating same-day casual: {'riders': 1.0}
E           assert np.False_
E            +  where np.False_ = all()
E            +    where all = temp                0.504360\natemp               0.504812\nhum                 0.105318\nwindspeed           0.165169\nda...         0.440896\ncnt_roll_7          0.534495\ncnt_roll_28         0.508815\nriders              1.000000\ndtype: float64 < 0.99.all

tests/test_leakage.py:45: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_feature_restates_same_day_leakage - Ass...
1 failed, 11 passed in 0.36s
```

