"""Exercise 4 exploration -- VALIDATION ONLY. Never touches the test split."""
import numpy as np, pandas as pd
from sklearn.base import clone
from sklearn.metrics import r2_score, mean_absolute_error
from src.config import TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split
df = pd.read_parquet("data/processed/features.parquet")
tr, va, _ = temporal_split(df); cols = feature_columns(df)
T = {
 "none":   (lambda d, y: y,                      lambda d, z: z),
 "log":    (lambda d, y: np.log(y),              lambda d, z: np.exp(z)),
 "diff1":  (lambda d, y: y - d.cnt_lag_1,        lambda d, z: z + d.cnt_lag_1),
 "diff28": (lambda d, y: y - d.cnt_roll_28,      lambda d, z: z + d.cnt_roll_28),
 "ratio7": (lambda d, y: y / d.cnt_roll_7,       lambda d, z: z * d.cnt_roll_7),
 "ratio28":(lambda d, y: y / d.cnt_roll_28,      lambda d, z: z * d.cnt_roll_28),
}
for name in ["ridge", "hgb"]:
    for t, (fwd, inv) in T.items():
        m = clone(MODELS[name]).fit(tr[cols], fwd(tr, tr[TARGET]))
        p = inv(va, m.predict(va[cols]))
        print(f"{name:5s} {t:8s} valid r2={r2_score(va[TARGET], p):.4f} mae={mean_absolute_error(va[TARGET], p):.1f}")
