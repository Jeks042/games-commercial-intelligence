from acquisition import get_json, nonnegative_int

URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
FIELDS = ["current_players", "current_players_result"]


def fetch_current_players(app_id):
    payload = get_json(URL, {"appid": app_id}).get("response", {})
    if payload.get("result") != 1:
        raise ValueError("Steam player endpoint did not report success")
    return {
        "current_players": nonnegative_int(payload.get("player_count"), "player_count"),
        "current_players_result": 1,
    }
