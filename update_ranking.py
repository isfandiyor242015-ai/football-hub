import asyncio
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

UEFA_URL = "https://www.uefa.com/nationalassociations/uefarankings/club/"

LOGOS = {
    "bayern munchen": "5", "bayern munich": "5", "arsenal": "57",
    "real madrid": "86", "paris": "524", "paris saint germain": "524",
    "inter": "108", "man city": "65", "manchester city": "65",
    "barcelona": "81", "liverpool": "64", "b dortmund": "4",
    "borussia dortmund": "4", "leverkusen": "3", "bayer leverkusen": "3",
    "atletico madrid": "78", "chelsea": "61", "juventus": "109",
    "milan": "98", "ac milan": "98", "roma": "100", "as roma": "100",
    "benfica": "1903", "porto": "503", "aston villa": "58"
}

COUNTRY_CODES = {
    "ger": ("Germany", "de"), "eng": ("England", "gb-eng"),
    "esp": ("Spain", "es"), "fra": ("France", "fr"),
    "ita": ("Italy", "it"), "por": ("Portugal", "pt"),
    "ned": ("Netherlands", "nl"), "nld": ("Netherlands", "nl"),
    "bel": ("Belgium", "be"), "tur": ("Türkiye", "tr"),
    "sco": ("Scotland", "gb-sct"), "aut": ("Austria", "at"),
    "sui": ("Switzerland", "ch"), "ukr": ("Ukraine", "ua"),
    "gre": ("Greece", "gr"), "den": ("Denmark", "dk"),
    "swe": ("Sweden", "se"), "nor": ("Norway", "no"),
    "cro": ("Croatia", "hr"), "cze": ("Czechia", "cz"),
    "pol": ("Poland", "pl"), "rou": ("Romania", "ro"),
    "srb": ("Serbia", "rs"), "hun": ("Hungary", "hu"),
    "irl": ("Ireland", "ie"), "isr": ("Israel", "il"),
    "cyp": ("Cyprus", "cy"), "bul": ("Bulgaria", "bg"),
    "fin": ("Finland", "fi"), "svk": ("Slovakia", "sk"),
    "svn": ("Slovenia", "si"), "aze": ("Azerbaijan", "az"),
    "kaz": ("Kazakhstan", "kz"), "arm": ("Armenia", "am"),
    "geo": ("Georgia", "ge"), "lva": ("Latvia", "lv"),
    "ltu": ("Lithuania", "lt"), "lux": ("Luxembourg", "lu"),
    "mlt": ("Malta", "mt"), "mda": ("Moldova", "md"),
    "mkd": ("North Macedonia", "mk"), "and": ("Andorra", "ad"),
    "alb": ("Albania", "al"), "biH": ("Bosnia and Herzegovina", "ba"),
    "kos": ("Kosovo", "xk"), "blr": ("Belarus", "by"),
    "est": ("Estonia", "ee"), "fro": ("Faroe Islands", "fo"),
    "gib": ("Gibraltar", "gi"), "lie": ("Liechtenstein", "li"),
    "lva": ("Latvia", "lv"), "mne": ("Montenegro", "me"),
    "irl": ("Ireland", "ie")
}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def column_index(headers, accepted):
    for index, header in enumerate(headers):
        if normalize(header) in accepted:
            return index
    return None


async def read_uefa_tables():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(locale="en-GB")
        await page.goto(UEFA_URL, wait_until="domcontentloaded", timeout=120000)
        # UEFA renders ranking data dynamically. Give the table time to appear.
        try:
            await page.locator("table tr").first.wait_for(timeout=45000)
        except Exception:
            await page.wait_for_timeout(10000)

        tables = await page.locator("table").evaluate_all("""
            tables => tables.map(table =>
                Array.from(table.querySelectorAll('tr')).map(row =>
                    Array.from(row.querySelectorAll('th, td'))
                        .map(cell => cell.innerText.trim())
                )
            )
        """)
        await browser.close()
    return tables


def extract_top_ten(tables):
    for table in tables:
        header_row_index = None
        headers = []

        for row_index, row in enumerate(table):
            normalized = [normalize(cell) for cell in row]
            has_position = any(value in {"pos", "position", "rank"} for value in normalized)
            has_club = "club" in normalized
            has_points = any(value in {"pts", "points"} for value in normalized)
            if has_position and has_club and has_points:
                header_row_index = row_index
                headers = normalized
                break

        if header_row_index is None:
            continue

        pos_i = next(i for i, value in enumerate(headers) if value in {"pos", "position", "rank"})
        club_i = headers.index("club")
        pts_i = next(i for i, value in enumerate(headers) if value in {"pts", "points"})
        country_i = next((i for i, value in enumerate(headers) if value in {"na", "country", "nation", "association"}), None)

        clubs = []
        for row in table[header_row_index + 1:]:
            if max(pos_i, club_i, pts_i) >= len(row):
                continue

            position_match = re.search(r"\d+", row[pos_i])
            points_match = re.search(r"\d+(?:[.,]\d+)?", row[pts_i])
            name = row[club_i].strip()
            if not position_match or not points_match or not name:
                continue

            position = int(position_match.group())
            if position > 10:
                continue

            association = row[country_i].strip() if country_i is not None and country_i < len(row) else ""
            code = normalize(association).replace(" ", "")
            country, flag = COUNTRY_CODES.get(code, (association, ""))
            key = normalize(name)

            clubs.append({
                "position": position,
                "name": name,
                "country": country,
                "flag": flag,
                "logo": LOGOS.get(key, ""),
                "points": float(points_match.group().replace(",", "."))
            })

        clubs.sort(key=lambda club: club["position"])
        if len(clubs) >= 10 and [club["position"] for club in clubs[:10]] == list(range(1, 11)):
            return clubs[:10]

    raise RuntimeError(
        "Could not read the official UEFA Top 10 table. "
        "The page layout may have changed; ranking.json was not overwritten."
    )


async def main():
    tables = await read_uefa_tables()
    ranking = extract_top_ten(tables)

    output = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": UEFA_URL,
        "ranking": ranking
    }

    Path("ranking.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print("Saved official UEFA Top 10:")
    for club in ranking:
        print(f'{club["position"]}. {club["name"]} — {club["points"]:.3f}')


if __name__ == "__main__":
    asyncio.run(main())
