import json
from acquisition import get_json, nonnegative_int

URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
FIELDS = [
    "review_score_code",
    "review_score_desc",
    "total_positive_reviews",
    "total_negative_reviews",
    "total_reviews",
    "review_positive_percent",
    "review_query_version",
]


def fetch_review_summary(app_id):
    params = {
        "appid": int(app_id),
        "filter": 0,
        "day_range": 0,
        "languages": ["all"],
        "review_type": 0,
        "purchase_type": 1,
        "num_per_page": 1,
        "filter_offtopic_activity": True,
        "display_language": "english",
        "cursor": "*",
    }
    payload = get_json(URL, {"input_json": json.dumps(params)})
    summary = payload.get("response", {}).get("query_summary")
    if not isinstance(summary, dict):
        raise ValueError("Missing Steam review query_summary")
    total = nonnegative_int(summary.get("total_reviews"), "total_reviews")
    positive = nonnegative_int(summary.get("total_positive"), "total_positive")
    negative = nonnegative_int(summary.get("total_negative"), "total_negative")
    if positive + negative != total:
        raise ValueError("Review counts do not reconcile")
    score = nonnegative_int(summary.get("review_score"), "review_score")
    if score > 9 or not isinstance(summary.get("review_score_desc"), str):
        raise ValueError("Invalid review score category")
    return {
        "review_score_code": score,
        "review_score_desc": summary["review_score_desc"],
        "total_positive_reviews": positive,
        "total_negative_reviews": negative,
        "total_reviews": total,
        "review_positive_percent": round(100 * positive / total, 2) if total else None,
        "review_query_version": "steam-service-v1-all-languages-all-purchases-offtopic-filtered",
    }
