
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

RSS_URL = "https://feeds.bbci.co.uk/sport/football/rss.xml"

KEYWORDS = [
    "transfer", "signs", "signed", "joins", "joined",
    "loan", "deal", "agrees", "move", "departure",
    "leaves", "leaving", "bid", "contract"
]

request = urllib.request.Request(
    RSS_URL,
    headers={"User-Agent": "FootballHub/1.0"}
)

with urllib.request.urlopen(request, timeout=30) as response:
    xml_data = response.read()

root = ET.fromstring(xml_data)
items = root.findall(".//item")

transfers = []

for item in items:
    title = item.findtext("title", default="").strip()
    description = item.findtext("description", default="").strip()
    link = item.findtext("link", default="").strip()
    pub_date = item.findtext("pubDate", default="").strip()

    searchable_text = (title + " " + description).lower()

    if not any(word in searchable_text for word in KEYWORDS):
        continue

    description = re.sub(r"<[^>]+>", "", description)
    description = re.sub(r"\s+", " ", description).strip()

    transfers.append({
        "title": title,
        "description": description,
        "link": link,
        "date": pub_date
    })

    if len(transfers) >= 12:
        break

with open("transfers.json", "w", encoding="utf-8") as file:
    json.dump(transfers, file, ensure_ascii=False, indent=2)

print(f"Saved {len(transfers)} football news articles.")
