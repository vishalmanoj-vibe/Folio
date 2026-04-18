import pandas as pd

cpnl = pd.Series([10.0, 50.0, 100.0], index=pd.date_range("2020-01-01", periods=3))
ccost = pd.Series([1000.0, 1000.0, 1000.0], index=pd.date_range("2020-01-01", periods=3))

pnl_at_start = float(cpnl.iloc[0]) if len(cpnl) else 0.0
y = ((cpnl - pnl_at_start) / ccost * 100).round(2)
print("y:\n", y)
