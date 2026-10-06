from __future__ import annotations

import requests

URL = "https://store.steampowered.com/api/appdetails"


def fetch_store_details(app_id: str, country_code: str = "gb") -> dict:
    response = requests.get(
        URL,
        params={"appids": app_id, "cc": country_code, "l": "english"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json().get(str(app_id), {})
    if not payload.get("success"):
        return {}

    data = payload.get("data", {})
    price = data.get("price_overview") or {}

    return {
        "store_name": data.get("name"),
        "store_type": data.get("type"),
        "is_free": data.get("is_free"),
        "developer_live": "; ".join(data.get("developers") or []),
        "publisher_live": "; ".join(data.get("publishers") or []),
        "release_date_live": (data.get("release_date") or {}).get("date"),
        "coming_soon": (data.get("release_date") or {}).get("coming_soon"),
        "currency": price.get("currency"),
        "list_price_minor": price.get("initial"),
        "final_price_minor": price.get("final"),
        "discount_percent": price.get("discount_percent"),
        "recommendation_count_store": (data.get("recommendations") or {}).get("total"),
        "metacritic_score": (data.get("metacritic") or {}).get("score"),
        "genres_live": "; ".join(x.get("description", "") for x in data.get("genres") or []),
        "categories_live": "; ".join(x.get("description", "") for x in data.get("categories") or []),
    }
