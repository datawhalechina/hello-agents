#!/bin/bash
# 单点改坏：总额不再格式化成两位小数
cp /solution/summarize.py /app/summarize.py
sed -i 's/f"{total:.2f}"/str(total)/' /app/summarize.py
python3 /app/summarize.py /app/input.csv /app/summary.csv /app/over_500.csv
