#!/bin/bash
# 单点改坏：把退款行跳过，而不是扣除
sed -i 's/amount = float(row\["amount"\])/amount = 0.0 if row["type"] == "refund" else float(row["amount"])/' /app/stats.py
