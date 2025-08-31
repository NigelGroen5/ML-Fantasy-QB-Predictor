'''
This file creates the 2025 prediction dataset by merging team's 2025 schedule 
with 2024 defensive stats and historical QB data.
'''

import pandas as pd
import numpy as np

# SET THE QB NAME AND TEAM ABBREVIATION HERE
qb_name = "Lamar Jackson"  
team_abbrev = "BAL"        

def create_2025_prediction_data(qb_name, team_abbrev):
    # load the data
    schedule_2025 = pd.read_csv("data/nfl_schedule_2025.csv")
    defense_stats = pd.read_csv("data/def_vs_qb_stats.csv")
    
    # load historical QB data
    historical_filename = f"data/{qb_name.lower().replace(' ', '_')}_with_defense_pg.csv"
    historical_data = pd.read_csv(historical_filename)
    
    # find teams row in the schedule
    team_schedule = schedule_2025[schedule_2025['Tm'] == team_abbrev].copy()
    if len(team_schedule) == 0:
        raise ValueError(f"{team_abbrev} not found in 2025 schedule")
    
    # Reshape
    schedule_long = pd.melt(
        team_schedule,
        id_vars=['Tm', 'Season'],
        value_vars=[f'Week{i}' for i in range(1, 19)],
        var_name='Week',
        value_name='Opponent'
    )
    
    #Convert Week to numeric and filter out BYE weeks
    schedule_long['Week'] = schedule_long['Week'].str.replace('Week', '').astype(int)
    team_2025 = schedule_long[schedule_long['Opponent'] != 'BYE'].copy()
    team_2025 = team_2025[['Week', 'Opponent']]
    team_2025['Season'] = 2025
    
    # Filter for 2024 defensive stats
    defense_2024 = defense_stats[defense_stats['Season'] == 2024].copy()
    
    if len(defense_2024) == 0:
        raise ValueError("No defensive stats found for 2024 season")
    
    # Calculate per-game defensive stats
    defense_2024['G'] = defense_2024['G'].replace({0: np.nan})
    
    # Define defensive stats to calculate per game
    defensive_stats = {
        "Passing Cmp": "Def_Cmp_Allowed_pg",
        "Passing Att": "Def_Att_Allowed_pg", 
        "Passing Yds": "Def_PassYds_Allowed_pg",
        "Passing TD": "Def_PassTD_Allowed_pg",
        "Passing Int": "Def_INT_Forced_pg",
        "Rushing Att": "Def_RushAtt_Allowed_pg",  
        "Rushing Yds": "Def_RushYds_Allowed_pg",  
        "Rushing TD": "Def_RushTD_Allowed_pg",    
        "Sk": "Def_Sacks_pg",
        "2PP": "Def_2PP_Allowed_pg",              
        "Fantasy per Game FantPt": "Def_FantasyPts_Allowed_pg"
    }
    
    # Calculate per-game stats
    for stat_col, new_col in defensive_stats.items():
        if stat_col in defense_2024.columns:
            if stat_col == "Fantasy per Game FantPt":
                defense_2024[new_col] = defense_2024[stat_col]
            else:
                defense_2024[new_col] = defense_2024[stat_col] / defense_2024['G']
    
    # Select only the defensive stats we need
    defense_cols = ['Tm'] + list(defensive_stats.values())
    defense_2024_clean = defense_2024[defense_cols].copy()
    defense_2024_clean = defense_2024_clean.rename(columns={'Tm': 'Opponent'})
    
    # Clean opponent names to ensure they match
    team_2025['Opponent'] = team_2025['Opponent'].str.replace('@', '')
    defense_2024_clean['Opponent'] = defense_2024_clean['Opponent'].str.replace('@', '')
    
    # Merge 2025 schedule with 2024 defensive stats
    prediction_data = pd.merge(
        team_2025,
        defense_2024_clean,
        on='Opponent',
        how='left'
    )
    
    # Check for missing defensive data
    missing_defense = prediction_data[prediction_data['Def_PassYds_Allowed_pg'].isna()]
    if len(missing_defense) > 0:
        print(f"Warning: Missing defensive data for {len(missing_defense)} opponents:")
        for _, row in missing_defense.iterrows():
            print(f"  Week {row['Week']}: {row['Opponent']}")
        
        # Fill missing values with league averages
        for col in defense_cols:
            if col != 'Tm' and col in defense_2024_clean.columns:
                league_avg = defense_2024_clean[col].mean()
                prediction_data[col] = prediction_data[col].fillna(league_avg)
                print(f"Filled missing {col} values with league average: {league_avg:.2f}")
    
    # Add empty columns for QB's stats
    qb_stats = [
        'Date', 'Completions', 'Attempts', 'Pass_Yds', 'Pass_TD', 'INT',
        'Rush_Att', 'Rush_Yds', 'Rush_TD', 'Fantasy_Points'
    ]
    
    for col in qb_stats:
        prediction_data[col] = np.nan
    
    # Create realistic dates 
    def create_nfl_date(week):
        if week <= 4:  
            return f"2025-09-{min(30, 5 + (week-1)*7)}"
        elif week <= 8:  
            return f"2025-10-{min(31, 1 + (week-5)*7)}"
        elif week <= 12:
            return f"2025-11-{min(30, 1 + (week-9)*7)}"
        elif week <= 17:  
            return f"2025-12-{min(31, 1 + (week-13)*7)}"
        else:  
            return "2026-01-01"
    prediction_data['Date'] = prediction_data['Week'].apply(create_nfl_date)
    prediction_data['Date'] = pd.to_datetime(prediction_data['Date'])
    
    # Add QB name
    prediction_data['QB'] = qb_name
    
    # Ensure both datasets have the same columns
    historical_cols = historical_data.columns.tolist()
    prediction_cols = prediction_data.columns.tolist()
    # Add missing columns to prediction data
    for col in historical_cols:
        if col not in prediction_cols:
            prediction_data[col] = np.nan
    
    # Reorder prediction data columns to match historical data
    prediction_data = prediction_data[historical_cols]
    # Combine historical and prediction data
    combined_data = pd.concat([historical_data, prediction_data], ignore_index=True)
    
    # Save 
    output_filename = f"data/{qb_name.lower().replace(' ', '_')}_complete_data.csv"
    combined_data.to_csv(output_filename, index=False)
    print(f"Done and saved to {output_filename}")
    
    # Show the 2025 prediction data with defensive stats
    print(f"\n2025 Schedule for {qb_name} ({team_abbrev}):")
    display_cols = ['Week', 'Opponent', 'Def_PassYds_Allowed_pg', 'Def_RushYds_Allowed_pg', 
                   'Def_Sacks_pg', 'Def_FantasyPts_Allowed_pg']
    display_data = combined_data[combined_data['Season'] == 2025][display_cols]
    print(display_data.to_string(index=False))
    
    return combined_data

if __name__ == "__main__":
    combined_data = create_2025_prediction_data(qb_name, team_abbrev)