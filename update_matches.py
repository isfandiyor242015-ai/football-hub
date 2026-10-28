
import json
import os
import urllib.request
import urllib.error

token = os.environ.get("FOOTBALL_HUB_API_TOKEN")

if not token:
    raise RuntimeError("FOOTBALL_API_TOKEN is missing.")

url = "https://api.football-data.org/v4/competitions"

request = urllib.request.Request(
    url,
    headers={"X-Auth-Token": token}
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    competitions = data.get("competitions", [])
    print("Accessible competitions:", len(competitions))

    for competition in competitions:
        print(competition.get("code"), "-", competition.get("name"))

except urllib.error.HTTPError as error:
    print("API returned HTTP", error.code)
    print(error.read().decode("utf-8"))
    raise
