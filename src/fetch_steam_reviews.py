from __future__ import annotations

import requests


def fetch_review_summary(app_id: str) -> dict:
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    response = requests.get(
        url,
        params={
            "json": 1,
            "filter": "summary",
            "language": "all",
            "purchase_type": "all",
            "num_per_page": 1,
        },
        timeout=30,
    )
    response.raise_for_status()
    summary = response.json().get("query_summary", {}) or {}

    total = summary.get("total_reviews") or 0
    positive = summary.get("total_positive") or 0
    negative = summary.get("total_negative") or 0

    return {
        "review_score_code": summary.get("review_score"),
        "review_score_desc": summary.get("review_score_desc"),
        "total_positive_reviews": positive,
        "total_negative_reviews": negative,
        "total_reviews": total,
        "review_positive_percent": round(100 * positive / total, 2) if total else None,
    }
