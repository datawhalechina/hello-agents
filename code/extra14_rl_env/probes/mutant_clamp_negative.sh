#!/bin/bash
# 单点改坏：退款正确，但总额被截断到 0 以上
sed -i 's/amount = float(row\["amount"\])/amount = float(row["amount"]) * (-1 if row["type"] == "refund" else 1)/' /app/stats.py
sed -i 's/print(json.dumps(totals, sort_keys=True))/print(json.dumps({k: max(v, 0.0) for k, v in totals.items()}, sort_keys=True))/' /app/stats.py
