#!/bin/bash
# 单点改坏：刚好 500 元的记录也挑了出来
cp /solution/summarize.py /app/summarize.py
sed -i 's/> Decimal("500")/>= Decimal("500")/' /app/summarize.py
python3 /app/summarize.py /app/input.csv /app/summary.csv /app/over_500.csv
