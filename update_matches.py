
import json
import os
import urllib.request
import urllib.error
from datetime import date, timedelta, timezone, datetime

TOKEN = os.environ["FOOTBALL_API_TOKEN"]

# Основные турниры, доступность зависит от тарифа API.
COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League",
    "WC": "World Cup",
    "EC": "European Championship",
}

today = date.today()
date_from = today - timedelta(days=7)
date_to = today + timedelta(days=14)

all_matches = []

for code, name in COMPETITIONS.items():
    url = (
        f"https://api.football-data.org/v4/competitions/{code}/matches"
        f"?dateFrom={date_from}&dateTo={date_to}"
    )

    request = urllib.request.Request(
        url,
        headers={"X-Auth-Token": TOKEN}
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)

        for match in data.get("matches", []):
            all_matches.append({
                "competition": name,
                "date": match.get("utcDate"),
                "status": match.get("status"),
                "home": match.get("homeTeam", {}).get("name", "TBA"),
                "away": match.get("awayTeam", {}).get("name", "TBA"),
                "homeScore": match.get("score", {})
                                  .get("fullTime", {}).get("home"),
                "awayScore": match.get("score", {})
                                  .get("fullTime", {}).get("away"),
            })

    except urllib.error.HTTPError as error:
        print(f"{code}: API returned HTTP {error.code}")
    except Exception as error:
        print(f"{code}: {error}")

all_matches.sort(key=lambda match: match.get("date") or "")

with open("matches.json", "w", encoding="utf-8") as file:
    json.dump(
        {
            "updated": datetime.now(timezone.utc).isoformat(),
            "matches": all_matches,
        },
        file,
        ensure_ascii=False,
        indent=2,
    )

print(f"Saved {len(all_matches)} matches.")
