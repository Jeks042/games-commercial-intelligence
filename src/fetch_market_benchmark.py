from __future__ import annotations

import requests

URL = "https://datasets-server.huggingface.co/filter"
DATASET = "Z02Z/steam-games-dataset"


def fetch_market_benchmark(app_id: str) -> dict:
    response = requests.get(
        URL,
        params={
            "dataset": DATASET,
            "config": "default",
            "split": "train",
            "where": f"\"appID\"='{app_id}'",
            "length": 1,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("rows") or []
    if not rows:
        return {}

    row = rows[0].get("row", {}) or {}
    return {
        "estimated_owners": row.get("estimated_owners"),
        "peak_ccu_benchmark": row.get("peak_ccu"),
        "benchmark_price_usd": row.get("price"),
        "benchmark_positive": row.get("positive"),
        "benchmark_negative": row.get("negative"),
        "benchmark_recommendations": row.get("recommendations"),
        "average_playtime_forever_minutes": row.get("average_playtime_forever"),
        "median_playtime_forever_minutes": row.get("median_playtime_forever"),
        "benchmark_genres": "; ".join(row.get("genres") or []),
        "benchmark_tags": "; ".join(row.get("tags") or []),
    }
