from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEEPSEEK_API_KEY   = os.getenv("DEEPSEEK_API_KEY", "")
AMAP_API_KEY       = os.getenv("AMAP_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

class Message(BaseModel):
    role: str
    content: str

class GenerateRequest(BaseModel):
    messages: List[Message]
    max_tokens: int = 2000

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(500, "DEEPSEEK_API_KEY not set")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "max_tokens": req.max_tokens,
                  "messages": [m.dict() for m in req.messages]},
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)
    text = resp.json()["choices"][0]["message"]["content"]
    return {"content": [{"type": "text", "text": text}]}

@app.get("/api/geocode")
async def geocode(address: str, city: str = ""):
    if not AMAP_API_KEY:
        raise HTTPException(500, "AMAP_API_KEY not set")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"key": AMAP_API_KEY, "address": address, "city": city, "output": "JSON"},
        )
    geocodes = resp.json().get("geocodes", [])
    if not geocodes:
        return {"location": None}
    loc = geocodes[0].get("location", "")
    if loc:
        lng, lat = loc.split(",")
        return {"location": {"lng": float(lng), "lat": float(lat)}}
    return {"location": None}

@app.get("/api/poi")
async def poi_search(keywords: str, city: str):
    if not AMAP_API_KEY:
        raise HTTPException(500, "AMAP_API_KEY not set")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://restapi.amap.com/v3/place/text",
            params={"key": AMAP_API_KEY, "keywords": keywords,
                    "city": city, "citylimit": "true", "output": "JSON", "offset": 1},
        )
    pois = resp.json().get("pois", [])
    if not pois:
        return {"location": None, "address": ""}
    p = pois[0]
    loc = p.get("location", "")
    if loc:
        lng, lat = loc.split(",")
        return {"location": {"lng": float(lng), "lat": float(lat)}, "address": p.get("address", "")}
    return {"location": None, "address": ""}

@app.get("/api/image")
async def get_image(query: str):
    if not UNSPLASH_ACCESS_KEY:
        return {"url": None}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        )
    if resp.status_code != 200:
        return {"url": None}
    results = resp.json().get("results", [])
    if not results:
        return {"url": None}
    return {"url": results[0]["urls"]["regular"], "thumb": results[0]["urls"]["thumb"]}

# 简单的中文城市名→英文映射（覆盖常见目的地，减少 API 调用）
CITY_EN_MAP = {
    "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou", "深圳": "Shenzhen",
    "成都": "Chengdu", "西安": "Xian", "杭州": "Hangzhou", "南京": "Nanjing",
    "重庆": "Chongqing", "武汉": "Wuhan", "苏州": "Suzhou", "厦门": "Xiamen",
    "青岛": "Qingdao", "大理": "Dali", "丽江": "Lijiang", "三亚": "Sanya",
    "桂林": "Guilin", "黄山": "Huangshan", "张家界": "Zhangjiajie", "九寨沟": "Jiuzhaigou",
    "拉萨": "Lhasa", "敦煌": "Dunhuang", "乌鲁木齐": "Urumqi", "哈尔滨": "Harbin",
    "香港": "Hong Kong", "澳门": "Macau", "台北": "Taipei",
    "东京": "Tokyo", "京都": "Kyoto", "大阪": "Osaka", "首尔": "Seoul",
    "曼谷": "Bangkok", "新加坡": "Singapore", "巴黎": "Paris", "伦敦": "London",
    "纽约": "New York", "洛杉矶": "Los Angeles", "悉尼": "Sydney", "墨尔本": "Melbourne",
}

def translate_city(city: str) -> str:
    for zh, en in CITY_EN_MAP.items():
        if zh in city:
            return en
    return city  # 已是英文或未知城市，原样返回

class BatchImageRequest(BaseModel):
    queries: List[str]

@app.post("/api/images/batch")
async def get_images_batch(req: BatchImageRequest):
    if not UNSPLASH_ACCESS_KEY:
        return {"results": {}}
    results = {}
    batch_size = 3
    async with httpx.AsyncClient(timeout=15) as client:
        for i in range(0, len(req.queries), batch_size):
            batch = req.queries[i:i+batch_size]
            tasks = [
                client.get(
                    "https://api.unsplash.com/search/photos",
                    params={"query": q, "per_page": 1, "orientation": "landscape"},
                    headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                )
                for q in batch
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for q, resp in zip(batch, responses):
                if isinstance(resp, Exception):
                    results[q] = None
                    continue
                try:
                    data = resp.json().get("results", [])
                    results[q] = data[0]["urls"]["regular"] if data else None
                except Exception:
                    results[q] = None
            if i + batch_size < len(req.queries):
                await asyncio.sleep(0.3)
    return {"results": results}

@app.get("/api/translate-city")
def translate_city_api(city: str):
    return {"en": translate_city(city)}

@app.get("/health")
def health():
    return {"status": "ok", "amap": bool(AMAP_API_KEY), "unsplash": bool(UNSPLASH_ACCESS_KEY)}
