import requests
import json
import time
from datetime import datetime

# 配置参数和本地保持一致
MARKET_API = "https://api.darkerdb.com/v1/market"
LOOT_FILE = "loot_cache.json"
OUTPUT_FILE = "price_full.json"
SINGLE_ITEM_INTERVAL = 3.0
RETRY_TIMES = 3
TIMEOUT = 30
PAGE_LIMIT = 1
SORT_RULE = "price_asc"
CACHE_EXPIRE_SEC = 1800

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

def safe_request(url: str, params: dict):
    for _ in range(RETRY_TIMES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            time.sleep(2)
    return None

def query_single_min_price(archetype_id: str):
    params = {"archetype": archetype_id, "sort": SORT_RULE, "limit": PAGE_LIMIT, "condense": True}
    resp_data = safe_request(MARKET_API, params)
    if not resp_data:
        return None
    item_list = resp_data.get("body", [])
    if not item_list:
        return None
    price = item_list[0].get("price", 0)
    return price if price > 0 else None

def batch_query_all(loot_map: dict):
    total = len(loot_map)
    priced = []
    no_stock = []
    index = 1
    item_list = list(loot_map.items())
    for item_id, name in item_list:
        print(f"正在查询 {index}/{total}：{name}")
        min_price = query_single_min_price(item_id)
        if min_price is not None:
            priced.append((item_id, name, min_price))
        else:
            no_stock.append((item_id, name))
        index += 1
        time.sleep(SINGLE_ITEM_INTERVAL)
    priced.sort(key=lambda x: x[2], reverse=True)
    return priced, no_stock

if __name__ == "__main__":
    # 读取道具映射
    with open(LOOT_FILE, "r", encoding="utf-8") as f:
        loot_map = json.load(f)
    priced_list, nostock_list = batch_query_all(loot_map)

    # 生成标准JSON，自带更新时间
    cloud_data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "valid_hour": int(CACHE_EXPIRE_SEC / 3600),
        "price_list": [{"id": i[0], "name": i[1], "price": i[2]} for i in priced_list],
        "no_stock_list": [{"id": i[0], "name": i[1]} for i in nostock_list]
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cloud_data, f, ensure_ascii=False, indent=2)
    print(f"抓取完成，共{len(priced_list)}条有价道具，已生成price_full.json")