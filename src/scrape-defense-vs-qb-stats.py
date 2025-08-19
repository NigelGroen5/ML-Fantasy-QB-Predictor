''' This script scrapes defense vs QB stats tables from Pro-Football-Reference.com for the 2022-2024 seasons. '''

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import pandas as pd
import time
from io import StringIO

urls = {
    2022: "https://www.pro-football-reference.com/years/2022/fantasy-points-against-QB.htm",
    2023: "https://www.pro-football-reference.com/years/2023/fantasy-points-against-QB.htm",
    2024: "https://www.pro-football-reference.com/years/2024/fantasy-points-against-QB.htm"
}

# Set up Chrome browser options (runs in background, no gpu, no sandbox)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

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

    table = soup.find("table") # find table
    if table:
        #convert table to pandas dataframe
        df = pd.read_html(StringIO(str(table)))[0]
        df["Season"] = year # add year column
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
else:
    print("No tables extracted.")