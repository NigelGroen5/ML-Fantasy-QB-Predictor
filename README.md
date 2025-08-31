This project analyzes and predicts NFL quarterback fantasy performance by combining quarterback statistics with defensive matchup data. The system uses historical data and current season information to forecast how QBs will perform against specific defenses in the 2025 season.


How to use this project:
1. Scrape nfl defensive data from Pro-football reference using scrape-defense-vs-qb_stats.py. (Its been saved as def_vs_qb_stats in the data folder)
2. (These next steps have already been done for Lamar Jackson and Mahomes). Manually collect QB data from Pro-Football-Reference and clean it using clean_qb_data.py. 
How to collect qb data:
-Pick your player and go to their profile on Pro-Football-Reference.
-Click on their career game logs.
-Scroll down to the top of the table and click Share & export -> get table as csv.
-Copy and paste that data into clean_qb_data.py.
4. Next, merge defensive and QB data using merge_qb_and_defense_stats.py.
5. Then scrape the 2025 schedule with 2025_schedule_scraper.py and merge it into the complete QB stats file with merge_2025_stats.py.
6. Then predict the QB’s points with qb_predictor.py and see the results in data/predictions/.
