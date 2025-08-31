'''Scrape ESPN NFL schedule grid for 2025 season and save to CSV'''

import requests
from bs4 import BeautifulSoup
import pandas as pd

def fetch_schedule_grid():
    url = "https://www.espn.com/nfl/schedulegrid"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  #throw error if blocked
    soup = BeautifulSoup(response.text, "html.parser")
    # Locate the table rows for each team
    rows = soup.find_all("tr")
    schedule = []

    for row in rows:
        cells = row.find_all(["th", "td"])
        if not cells or len(cells) < 2:
            continue
        team_cell = cells[0]
        team = team_cell.get_text(strip=True)
        # Skip header row if "TEAM" 
        if team.upper() == "TEAM":
            continue

        week_entries = []
        for cell in cells[1:]:
            text = cell.get_text(strip=True)
            if text == "BYE":
                week_entries.append("BYE")
            else:
                week_entries.append(text.replace("@", "")) #remove "@"
        schedule.append([team] + week_entries)

    # Create the DataFrame with week columns
    num_weeks = len(schedule[0]) - 1
    columns = ["Team"] + [f"Week{w}" for w in range(1, num_weeks + 1)]
    df = pd.DataFrame(schedule, columns=columns)

    # Add season year column
    df["Season"] = 2025
    df = df.rename(columns={"Team": "Tm"})
    return df

def save_to_csv(df, filepath="nfl_schedule_2025.csv"):
    df.to_csv(filepath, index=False)
    print(f"Schedule grid saved to {filepath}")

def main():
    df = fetch_schedule_grid()
    print(df.head())
    save_to_csv(df)

if __name__ == "__main__":
    main()