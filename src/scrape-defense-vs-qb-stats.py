''' This script scrapes defense vs QB stats tables from Pro-Football-Reference.com for the 2017-2024 seasons. '''

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup, Comment
import pandas as pd
import time
from io import StringIO

urls = {
    2016: "https://www.pro-football-reference.com/years/2016/fantasy-points-against-QB.htm",
    2017: "https://www.pro-football-reference.com/years/2017/fantasy-points-against-QB.htm",
    2018: "https://www.pro-football-reference.com/years/2018/fantasy-points-against-QB.htm",
    2019: "https://www.pro-football-reference.com/years/2019/fantasy-points-against-QB.htm",
    2020: "https://www.pro-football-reference.com/years/2020/fantasy-points-against-QB.htm",
    2021: "https://www.pro-football-reference.com/years/2021/fantasy-points-against-QB.htm",
    2022: "https://www.pro-football-reference.com/years/2022/fantasy-points-against-QB.htm",
    2023: "https://www.pro-football-reference.com/years/2023/fantasy-points-against-QB.htm",
    2024: "https://www.pro-football-reference.com/years/2024/fantasy-points-against-QB.htm"
}

# Set up Chrome browser options (runs in background, no gpu, no sandbox, user-agent)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

# Store ChromeDriver location and start the browser
# NOTE: Update the path below to where chromedriver.exe is located on your system.
service = Service("C:/Users/User/Documents/GitHub/ML-Fantasy-QB-Predictor/src/chromedriver.exe")
driver = webdriver.Chrome(service=service, options=chrome_options)

# Store dataframes for each year in dfs list
dfs = []
# Loop through each year and scrape the table
for year, url in urls.items():
    print(f"\n--- {year} ---")
    driver.get(url) # open the URL
    time.sleep(3)  # wait for the page to load

    html = driver.page_source # get page html
    soup = BeautifulSoup(html, "lxml") # parse

    # Find the fantasy defense table by its ID
    table = soup.find("table", {"id": "fantasy_def"})
    if not table:
        # If not found, look for tables inside HTML comments (fallback)
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment_soup = BeautifulSoup(comment, "lxml")
            table = comment_soup.find("table", {"id": "fantasy_def"})
            if table:
                break

    if table:
        #convert table to pandas dataframe
        df = pd.read_html(StringIO(str(table)))[0]
        
        # Clean up columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() if 'Unnamed' not in col[0] else col[1] 
                         for col in df.columns.values]
            df.columns = [col.replace('_', ' ').strip() for col in df.columns]
        
        df["Season"] = year # add year column
        
        # Remove all header rows from data 
        if 'Tm' in df.columns:
            # Remove rows where 'Tm' column contains header-like values
            df = df[~df['Tm'].isin(['Tm', 'Team', 'Passing', 'Rushing', 'Fantasy'])]
            numeric_cols = ['G', 'Cmp', 'Att', 'Yds', 'TD', 'Int', 'Att.1', 'Yds.1', 'TD.1']
            for col in numeric_cols:
                if col in df.columns:
                    df = df[pd.to_numeric(df[col], errors='coerce').notna()]
        
        dfs.append(df) # save table in list
        print(f"Table extracted for {year}, shape: {df.shape}")
    else:
        print(f"No table found for {year}")

driver.quit()

#combine all years into one big dataframe
if dfs:
    all_def_vs_qb = pd.concat(dfs, ignore_index=True)
    # Drop repeated headers if present
    if "Tm" in all_def_vs_qb.columns:
        all_def_vs_qb = all_def_vs_qb[all_def_vs_qb["Tm"] != "Tm"].reset_index(drop=True)
    print(all_def_vs_qb.head(10))


    # convert team names to abbrevs
    team_map = {
        "Arizona Cardinals": "ARI",
        "Atlanta Falcons": "ATL",
        "Baltimore Ravens": "BAL",
        "Buffalo Bills": "BUF",
        "Carolina Panthers": "CAR",
        "Chicago Bears": "CHI",
        "Cincinnati Bengals": "CIN",
        "Cleveland Browns": "CLE",
        "Dallas Cowboys": "DAL",
        "Denver Broncos": "DEN",
        "Detroit Lions": "DET",
        "Green Bay Packers": "GB",
        "Houston Texans": "HOU",
        "Indianapolis Colts": "IND",
        "Jacksonville Jaguars": "JAX",  
        "Kansas City Chiefs": "KC",
        "Las Vegas Raiders": "LV",
        "Oakland Raiders": "LV",            
        "Los Angeles Chargers": "LAC",
        "San Diego Chargers": "LAC",        
        "Los Angeles Rams": "LAR",
        "St. Louis Rams": "LAR",            
        "Miami Dolphins": "MIA",
        "Minnesota Vikings": "MIN",
        "New England Patriots": "NE",
        "New Orleans Saints": "NO",
        "New York Giants": "NYG",
        "New York Jets": "NYJ",
        "Philadelphia Eagles": "PHI",
        "Pittsburgh Steelers": "PIT",
        "San Francisco 49ers": "SF",
        "Seattle Seahawks": "SEA",
        "Tampa Bay Buccaneers": "TB",
        "Tennessee Titans": "TEN",
        "Washington Redskins": "WAS",
        "Washington Football Team": "WAS",
        "Washington Commanders": "WAS"
    }
    all_def_vs_qb["Tm"] = all_def_vs_qb["Tm"].map(team_map)

    # save csv
    all_def_vs_qb.to_csv("def_vs_qb_stats.csv", index=False)
    print("saved to csv")
    
else:
    print("No tables extracted.")