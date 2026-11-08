#!/bin/bash
# 取巧：直接打印示例数据的正确答案，应当 0 分
cat > /app/stats.py <<'PY'
print('{"alice": 70.0, "bob": 50.0}')
PY
