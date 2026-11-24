"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import numpy as np
import pandas as pd
import pytest

from src.config import FORBIDDEN, LEAKAGE_COLS, TARGET
from src.features import build_features, encode_weather, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


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
        assert (corr < 0.99).all(), f"features restating same-day {col}: {corr[corr >= 0.99].round(4).to_dict()}"
    A = np.column_stack([X.to_numpy(), np.ones(len(X))])
    y = feats[TARGET].to_numpy(dtype=float)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = float(np.abs(A @ coef - y).max())
    assert resid > 1.0, f"features reproduce {TARGET} exactly (max residual {resid:.2e})"


def test_lags_are_true_calendar_lags(feats):
    """cnt_lag_1 for date d must equal cnt on d-1, in calendar days."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_1.items():
        prev = date - pd.Timedelta(days=1)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


def test_rolling_mean_excludes_today(feats):
    """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
    by_date = feats.set_index("dteday")[TARGET]
    date = feats.dteday.iloc[200]
    window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
    if all(d in by_date.index for d in window):
        expected = sum(by_date[d] for d in window) / 7
        assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)


def test_roll_28_is_mean_of_28_strictly_earlier_days(feats):
    """cnt_roll_28 on 2012-03-15 must equal the mean of cnt over the 28
    calendar days 2012-02-16 .. 2012-03-14, computed by hand from the raw
    table. Today's count (2012-03-15) must not be in the window."""
    raw = load_raw().set_index("dteday")[TARGET]
    date = pd.Timestamp("2012-03-15")
    window = pd.date_range(date - pd.Timedelta(days=28), date - pd.Timedelta(days=1))
    assert len(window) == 28 and window.max() < date
    expected = raw.loc[window].sum() / 28
    got = feats.set_index("dteday").loc[date, "cnt_roll_28"]
    assert got == pytest.approx(expected)


def test_weather_encoder_rejects_unseen_labels():
    """An unseen label must raise, not become a NaN that dropna() later
    deletes without comment. The real data only has known labels, so
    without this test nothing exercises the raise."""
    with pytest.raises(ValueError, match="unmapped weather labels"):
        encode_weather(pd.Series(["GOOD", "SNOW", "MISTY"]))


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique
