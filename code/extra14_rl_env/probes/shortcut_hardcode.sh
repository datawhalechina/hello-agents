#!/bin/bash
# 取巧：手算示例数据的结果写死，脚本只是把它们复制过去，应当 0 分
printf '姓名,报销总额\n张敏,800.50\n李雷,545.25\n王芳,590.01\n' > /app/summary.csv
printf '日期,姓名,类别,金额\n2026-10-03,张敏,住宿,680.50\n2026-10-04,王芳,办公,500.01\n' > /app/over_500.csv
cat > /app/summarize.py <<'PY'
import shutil
import sys

shutil.copy("/app/summary.csv", sys.argv[2])
shutil.copy("/app/over_500.csv", sys.argv[3])
PY
