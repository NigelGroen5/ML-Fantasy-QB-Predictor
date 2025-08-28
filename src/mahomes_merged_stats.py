import pandas as pd

mahomes = pd.read_csv("data/mahomes_complete_game_logs.csv")
defense = pd.read_csv("data/def_vs_qb_stats.csv")

# keep only relevant Mahomes columns
mahomes_relevant = mahomes[[
    "Season", "Week", "Date", "Opponent",
    "Completions", "Attempts", "Pass_Yds", "Pass_TD", "INT",
    "Rush_Att", "Rush_Yds", "Rush_TD",
    "Fantasy_Points"
]].copy()

# ensure correct types
num_cols = [
    "G",
    "Passing Cmp","Passing Att","Passing Yds","Passing TD","Passing Int",
    "Rushing Att","Rushing Yds","Rushing TD",
    "Sk","2PP",
    "Fantasy FantPt","Fantasy DKPt","Fantasy FDPt",
    "Fantasy per Game FantPt","Fantasy per Game DKPt","Fantasy per Game FDPt"
]
for c in num_cols:
    if c in defense.columns:
        defense[c] = pd.to_numeric(defense[c], errors="coerce")

# Build per-game features from totals
per_game_src_to_dst = {
    "Passing Cmp": "Def_Cmp_Allowed_pg",
    "Passing Att": "Def_Att_Allowed_pg",
    "Passing Yds": "Def_PassYds_Allowed_pg",
    "Passing TD": "Def_PassTD_Allowed_pg",
    "Passing Int": "Def_INT_Forced_pg",
    "Rushing Att": "Def_RushAtt_Allowed_pg",
    "Rushing Yds": "Def_RushYds_Allowed_pg",
    "Rushing TD": "Def_RushTD_Allowed_pg",
    "Sk": "Def_Sacks_pg",
    "2PP": "Def_2PP_Allowed_pg"
}

# no divide-by-zero
defense["G"] = defense["G"].replace({0: pd.NA})

# Only divide totals
totals_to_divide = [
    "Passing Cmp","Passing Att","Passing Yds","Passing TD","Passing Int",
    "Rushing Att","Rushing Yds","Rushing TD","Sk","2PP"
]

for src, dst in per_game_src_to_dst.items():
    if src in totals_to_divide and src in defense.columns:
        defense[dst] = defense[src] / defense["G"]

# Use the site’s per-game fantasy directly
if "Fantasy per Game FantPt" in defense.columns:
    defense["Def_FantasyPts_Allowed_pg"] = defense["Fantasy per Game FantPt"]

# Select and rename for merge
keep_cols = ["Tm", "Season"] + [v for v in per_game_src_to_dst.values()] + ["Def_FantasyPts_Allowed_pg"]
defense_relevant = defense[keep_cols].copy()
defense_relevant = defense_relevant.rename(columns={"Tm": "Opponent"})

# Shift season so each Mahomes season uses previous year's defense 
defense_relevant["Season"] = defense_relevant["Season"] + 1

# Merge 
merged = pd.merge(
    mahomes_relevant,
    defense_relevant,
    on=["Season", "Opponent"],
    how="left"
)

merged.to_csv("data/mahomes_with_defense_pg.csv", index=False)
print("Saved -> data/mahomes_with_defense_pg.csv")
print("Shape:", merged.shape)
print(merged.head())