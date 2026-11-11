#!/bin/bash
# 单点改坏：汇总按姓名排序，而不是按首次出现的顺序
cp /solution/summarize.py /app/summarize.py
sed -i 's/for name, total in totals.items():/for name, total in sorted(totals.items()):/' /app/summarize.py
python3 /app/summarize.py /app/input.csv /app/summary.csv /app/over_500.csv
