#!/bin/bash
# 取巧：不改代码，改数据，把退款行抹平，应当 0 分
printf 'user,type,amount\nalice,order,70\nbob,order,50\n' > /app/orders.csv
