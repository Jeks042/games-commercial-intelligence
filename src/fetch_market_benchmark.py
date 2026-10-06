import re
from acquisition import get_json, nonnegative_int

URL = "https://steamspy.com/api.php"
PLAYTIME = {
    "average_playtime_forever_minutes": "average_forever",
    "average_playtime_2weeks_minutes": "average_2weeks",
    "median_playtime_forever_minutes": "median_forever",
    "median_playtime_2weeks_minutes": "median_2weeks",
}
FIELDS = [
    "estimated_owners",
    "steamspy_ccu",
    "steamspy_price",
    "steamspy_positive",
    "steamspy_negative",
    *PLAYTIME,
    "steamspy_genre",
    "steamspy_languages",
    "owner_estimate_status",
    "playtime_status",
]


def fetch_market_benchmark(app_id):
    row = get_json(URL, {"request": "appdetails", "appid": app_id})
    if str(row.get("appid")) != str(app_id) or not row.get("name"):
        raise ValueError("SteamSpy app identity mismatch or missing")
    owners = row.get("owners")
    match = re.fullmatch(r"([\d,]+)\s*\.\.\s*([\d,]+)", owners or "")
    if not match or int(match[1].replace(",", "")) > int(match[2].replace(",", "")):
        raise ValueError("SteamSpy owner range is missing or malformed")
    values = {
        target: nonnegative_int(row.get(source), source, allow_string=True)
        for target, source in PLAYTIME.items()
    }
    available = {
        target: value if value > 0 else None for target, value in values.items()
    }
    return {
        "estimated_owners": owners,
        "steamspy_ccu": nonnegative_int(
            row.get("ccu"), "SteamSpy ccu", allow_string=True
        ),
        "steamspy_price": row.get("price"),
        "steamspy_positive": nonnegative_int(
            row.get("positive"), "SteamSpy positive", allow_string=True
        ),
        "steamspy_negative": nonnegative_int(
            row.get("negative"), "SteamSpy negative", allow_string=True
        ),
        **available,
        "steamspy_genre": row.get("genre"),
        "steamspy_languages": row.get("languages"),
        "owner_estimate_status": "requires_review",
        "playtime_status": (
            "available"
            if all(available.values())
            else "partial" if any(available.values()) else "unavailable"
        ),
    }
