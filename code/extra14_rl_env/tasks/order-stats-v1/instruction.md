`/app/stats.py` 读取一份订单 CSV，按用户统计消费总额，并把结果以 JSON 打印到标准输出。

用法：`python3 /app/stats.py <csv路径>`。CSV 的表头是 `user,type,amount`，示例数据在 `/app/orders.csv`。

现在统计结果不对：`type` 为 `refund` 的行表示退款，应该从该用户的总额里扣除，但脚本把它加上去了。

请修复 `/app/stats.py`。
