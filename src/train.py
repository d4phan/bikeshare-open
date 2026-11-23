"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import argparse
import json

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


# Exercise 4: optional target transformations, applied to ridge and hgb only
# (baselines always predict raw cnt). `none` is the default and is what
# `make train` writes to reports/metrics.json.
#   diff28: model cnt - cnt_roll_28 (today's departure from the trailing
#   four-week level), then add the level back. cnt_roll_28 uses d-28..d-1
#   only, so the inverse is available at prediction time.
TARGET_TRANSFORMS = {
    "none": (lambda d, y: y, lambda d, z: z),
    "diff28": (lambda d, y: y - d["cnt_roll_28"], lambda d, z: z + d["cnt_roll_28"]),
}
TRANSFORMED_MODELS = {"ridge", "hgb"}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score(target_transform: str = "none") -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    fwd, inv = TARGET_TRANSFORMS[target_transform]

    results = {
        **({"target_transform": target_transform} if target_transform != "none" else {}),
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in MODELS.items():
        f, g = (fwd, inv) if name in TRANSFORMED_MODELS else TARGET_TRANSFORMS["none"]
        model.fit(train[cols], f(train, train[TARGET]))
        results[name] = {}
        for split, part in [("valid", valid), ("test", test)]:
            pred = g(part, model.predict(part[cols]))
            results[name][split] = {
                "r2": round(float(r2_score(part[TARGET], pred)), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], pred)), 1),
            }
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-transform", choices=sorted(TARGET_TRANSFORMS), default="none")
    t = ap.parse_args().target_transform
    res = fit_and_score(t)
    out = METRICS if t == "none" else METRICS.with_name(f"metrics_{t}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
