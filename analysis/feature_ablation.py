"""Exercise 1 control (validation only): same rows, with vs without cnt_roll_28."""
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import r2_score, mean_absolute_error
from src.config import TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split
df = pd.read_parquet("data/processed/features.parquet")
tr, va, _ = temporal_split(df)
full = feature_columns(df); without = [c for c in full if c != "cnt_roll_28"]
for name in ["ridge", "hgb"]:
    for label, cols in [("without", without), ("with", full)]:
        m = clone(MODELS[name]).fit(tr[cols], tr[TARGET]); p = m.predict(va[cols])
        print(f"{name:6s} {label:8s} valid r2={r2_score(va[TARGET], p):.4f} mae={mean_absolute_error(va[TARGET], p):.1f}")
