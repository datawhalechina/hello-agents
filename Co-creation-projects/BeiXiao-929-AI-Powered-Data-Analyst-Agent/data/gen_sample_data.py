# -*- coding: utf-8 -*-
"""生成示例销售数据集 sample_sales.csv（100 条记录，<1MB）"""
import csv
import random
from datetime import date, timedelta

random.seed(42)

REGIONS = ["华东", "华北", "华南", "西南", "东北"]
PRODUCTS = {
    "智能手机": ("数码电子", 3999),
    "笔记本电脑": ("数码电子", 5999),
    "无线耳机": ("数码电子", 499),
    "电饭煲": ("家用电器", 399),
    "空气净化器": ("家用电器", 1899),
    "电动牙刷": ("个护健康", 299),
    "按摩仪": ("个护健康", 899),
}
CHANNELS = ["线上商城", "线下门店", "直播带货"]

rows = []
start = date(2025, 1, 1)
for i in range(97):
    product, (category, price) = random.choice(list(PRODUCTS.items()))
    quantity = random.randint(1, 20)
    # 区域系数：华东/华南销售额偏高
    region = random.choices(REGIONS, weights=[30, 22, 25, 13, 10])[0]
    region_factor = {"华东": 1.2, "华北": 1.0, "华南": 1.15, "西南": 0.8, "东北": 0.7}[region]
    sales = round(price * quantity * region_factor * random.uniform(0.85, 1.15), 2)
    d = start + timedelta(days=random.randint(0, 180))
    rows.append({
        "order_id": f"ORD2025{i:04d}",
        "order_date": d.isoformat(),
        "region": region,
        "channel": random.choice(CHANNELS),
        "product": product,
        "category": category,
        "unit_price": float(price),
        "quantity": quantity,
        "sales_amount": sales,
        "customer_satisfaction": round(random.uniform(3.0, 5.0), 1) if random.random() > 0.08 else "",
    })

# 人为制造数据质量问题：缺失值 + 重复行
rows[5]["sales_amount"] = ""          # 缺失销售额
rows[20]["region"] = ""               # 缺失区域
rows[40]["customer_satisfaction"] = ""
rows[66]["sales_amount"] = ""
rows.append(dict(rows[10]))           # 3 条重复行
rows.append(dict(rows[33]))
rows.append(dict(rows[71]))

random.shuffle(rows)

fieldnames = ["order_id", "order_date", "region", "channel", "product", "category",
              "unit_price", "quantity", "sales_amount", "customer_satisfaction"]
out = "data/sample_sales.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"已生成 {out}，共 {len(rows)} 条记录")
