"""Exercise 5 diagnostics: error structure of ridge vs persistence on fitted models (no tuning)."""
import numpy as np, pandas as pd
from sklearn.base import clone
from src.config import TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split
df = pd.read_parquet("data/processed/features.parquet"); cols = feature_columns(df)
tr, va, te = temporal_split(df)
ridge = clone(MODELS["ridge"]).fit(tr[cols], tr[TARGET])
for nm, part in [("valid", va), ("test", te)]:
    y = part[TARGET].to_numpy(); r = ridge.predict(part[cols]); p = part.cnt_lag_1.to_numpy()
    er, ep = np.abs(y-r), np.abs(y-p)
    print(f"== {nm} n={len(y)}")
    print(f"mean error (y-pred): ridge {np.mean(y-r):+.1f}  persistence {np.mean(y-p):+.1f}")
    print(f"MAE: ridge {er.mean():.1f}  persist {ep.mean():.1f} | median AE: ridge {np.median(er):.1f} persist {np.median(ep):.1f}")
    print(f"P90 AE: ridge {np.percentile(er,90):.1f} persist {np.percentile(ep,90):.1f} | max AE: ridge {er.max():.0f} persist {ep.max():.0f}")
    print(f"days with AE>2000: ridge {(er>2000).sum()} persist {(ep>2000).sum()} | ridge closer on {np.mean(er<ep)*100:.1f}% of days")
    # bias-corrected ridge: shift by train-period?? no -- report only
    big = np.abs(y - p) > 1500
    print(f"on {big.sum()} days where cnt moved >1500 from yesterday: MAE ridge {er[big].mean():.1f} persist {ep[big].mean():.1f}")
    print(f"on the other {(~big).sum()} days: MAE ridge {er[~big].mean():.1f} persist {ep[~big].mean():.1f}")
