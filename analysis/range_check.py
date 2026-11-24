"""Headline evidence: share of test days above the 2011 maximum (a tree cannot predict past it)."""
import pandas as pd
from src.config import RAW, TARGET
from src.train import temporal_split

df = pd.read_parquet("data/processed/features.parquet")
_, _, test = temporal_split(df)
raw = pd.read_csv(RAW, parse_dates=["dteday"])
mx = raw.loc[raw.dteday.dt.year == 2011, TARGET].max()
above = test[TARGET] > mx
print(f"2011 max {mx}; test days above it: {above.sum()} / {len(test)} ({above.mean() * 100:.1f}%)")
growth = raw.groupby(raw.dteday.dt.year)[TARGET].mean()
print(f"mean daily cnt 2011 {growth[2011]:.1f}, 2012 {growth[2012]:.1f}, growth {(growth[2012] / growth[2011] - 1) * 100:.1f}%")
