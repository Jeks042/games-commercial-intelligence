from __future__ import annotations

import requests

URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"


def fetch_current_players(app_id: str) -> dict:
    response = requests.get(URL, params={"appid": app_id}, timeout=30)
    response.raise_for_status()
    payload = response.json().get("response", {}) or {}
    return {
        "current_players": payload.get("player_count"),
        "current_players_result": payload.get("result"),
    }
