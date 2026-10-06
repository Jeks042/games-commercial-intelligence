from __future__ import annotations

import requests

URL = "https://steamspy.com/api.php"


def fetch_market_benchmark(app_id: str) -> dict:
    response = requests.get(
        URL,
        params={"request": "appdetails", "appid": app_id},
        timeout=20,
        headers={"User-Agent": "games-commercial-intelligence/1.0"},
    )
    response.raise_for_status()
    row = response.json() or {}

    return {
        "estimated_owners": row.get("owners"),
        "steamspy_ccu": row.get("ccu"),
        "steamspy_price": row.get("price"),
        "steamspy_positive": row.get("positive"),
        "steamspy_negative": row.get("negative"),
        "average_playtime_forever_minutes": row.get("average_forever"),
        "average_playtime_2weeks_minutes": row.get("average_2weeks"),
        "median_playtime_forever_minutes": row.get("median_forever"),
        "median_playtime_2weeks_minutes": row.get("median_2weeks"),
        "steamspy_genre": row.get("genre"),
        "steamspy_languages": row.get("languages"),
    }
