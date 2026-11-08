#!/bin/bash
# 单点改坏：退款正确，但金额被截断成整数
sed -i 's/amount = float(row\["amount"\])/amount = int(float(row["amount"])) * (-1 if row["type"] == "refund" else 1)/' /app/stats.py
