from acquisition import get_json, nonnegative_int

URL = "https://store.steampowered.com/api/appdetails"
FIELDS = [
    "store_name",
    "store_type",
    "is_free",
    "developer_live",
    "publisher_live",
    "release_date_live",
    "coming_soon",
    "currency",
    "list_price_minor",
    "final_price_minor",
    "discount_percent",
    "recommendation_count_store",
    "metacritic_score",
    "genres_live",
    "categories_live",
    "store_country_code",
    "price_status",
]


def fetch_store_details(app_id, country_code="gb"):
    payload = get_json(URL, {"appids": app_id, "cc": country_code, "l": "english"}).get(
        str(app_id), {}
    )
    if payload.get("success") is not True or not isinstance(payload.get("data"), dict):
        raise ValueError("Steam Store did not return successful app details")
    data = payload["data"]
    if (
        str(data.get("steam_appid")) != str(app_id)
        or not data.get("name")
        or data.get("type") != "game"
    ):
        raise ValueError("Steam Store identity/type does not match scoped game")
    if type(data.get("is_free")) is not bool:
        raise ValueError("Missing is_free flag")
    price = data.get("price_overview") or {}
    if price:
        initial = nonnegative_int(price.get("initial"), "initial price")
        final = nonnegative_int(price.get("final"), "final price")
        discount = nonnegative_int(price.get("discount_percent"), "discount_percent")
        if price.get("currency") != "GBP" or final > initial or discount > 100:
            raise ValueError("Price violates GBP snapshot contract")
        status = "available"
    else:
        initial = final = discount = None
        status = "free" if data["is_free"] else "unavailable"
    return {
        "store_name": data["name"],
        "store_type": data["type"],
        "is_free": data["is_free"],
        "developer_live": "; ".join(x.strip() for x in data.get("developers", [])),
        "publisher_live": "; ".join(x.strip() for x in data.get("publishers", [])),
        "release_date_live": data.get("release_date", {}).get("date"),
        "coming_soon": data.get("release_date", {}).get("coming_soon"),
        "currency": price.get("currency"),
        "list_price_minor": initial,
        "final_price_minor": final,
        "discount_percent": discount,
        "recommendation_count_store": data.get("recommendations", {}).get("total"),
        "metacritic_score": data.get("metacritic", {}).get("score"),
        "genres_live": "; ".join(
            x.get("description", "") for x in data.get("genres", [])
        ),
        "categories_live": "; ".join(
            x.get("description", "") for x in data.get("categories", [])
        ),
        "store_country_code": country_code,
        "price_status": status,
    }
