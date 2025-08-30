# QB Fantasy Points Predictor

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

class QBFantasyPredictor:
    """Predict fantasy points for quarterbacks using their data"""
    def __init__(self):
        self.model = None
        self.top_features = []
        self.feature_importance = None
        self.is_trained = False
        
    def create_advanced_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create predictive features"""
        data = data.sort_values("date").copy()

        # check if defensive columns exist, if not create dummy ones
        defensive_cols = ["Def_FantasyPts_Allowed_pg", "Def_Sacks_pg", "Def_PassYds_Allowed_pg", 
                        "Def_PassTD_Allowed_pg", "Def_INT_Forced_pg"]
        
        for col in defensive_cols:
            if col not in data.columns:
                data[col] = 0
        
        # basic game context
        data["season"] = data["Season"]
        data["week"] = data["Week"]
        data["is_playoff"] = (data["Week"] >= 17).astype(int)
        data["is_early_season"] = (data["Week"] <= 4).astype(int)
        data["is_late_season"] = (data["Week"] >= 14).astype(int)
        data["is_home"] = 1  # Assume home games
        
        # Rolling averages for key stats
        for window in [3, 5, 10]:
            data[f"fantasy_rolling_{window}"] = data["Fantasy_Points"].rolling(window, closed='left').mean()
            data[f"pass_yds_rolling_{window}"] = data["Pass_Yds"].rolling(window, closed='left').mean()
            data[f"pass_td_rolling_{window}"] = data["Pass_TD"].rolling(window, closed='left').mean()
            data[f"int_rolling_{window}"] = data["INT"].rolling(window, closed='left').mean()
            data[f"rush_yds_rolling_{window}"] = data["Rush_Yds"].rolling(window, closed='left').mean()
            data[f"rush_td_rolling_{window}"] = data["Rush_TD"].rolling(window, closed='left').mean()
            data[f"completion_rate_rolling_{window}"] = (data["Completions"] / data["Attempts"]).rolling(window, closed='left').mean()
        
        #Recent trends (last 2 games)
        data["fantasy_trend"] = data["Fantasy_Points"].rolling(2, closed='left').mean()
        data["pass_yds_trend"] = data["Pass_Yds"].rolling(2, closed='left').mean()
        data["pass_td_trend"] = data["Pass_TD"].rolling(2, closed='left').mean()
        
        # Volatility 
        data["fantasy_volatility"] = data["Fantasy_Points"].rolling(5, closed='left').std()
        data["pass_yds_volatility"] = data["Pass_Yds"].rolling(5, closed='left').std()
        
        # Efficiency 
        data["yards_per_attempt"] = data["Pass_Yds"] / data["Attempts"]
        data["td_per_attempt"] = data["Pass_TD"] / data["Attempts"]
        data["int_per_attempt"] = data["INT"] / data["Attempts"]
        
        # Rolling efficiency
        data["ypa_rolling_3"] = data["yards_per_attempt"].rolling(3, closed='left').mean()
        data["tpa_rolling_3"] = data["td_per_attempt"].rolling(3, closed='left').mean()
        data["ipa_rolling_3"] = data["int_per_attempt"].rolling(3, closed='left').mean()
        
        # Defense 
        data["defense_strength"] = data["Def_FantasyPts_Allowed_pg"] * data["Def_Sacks_pg"]
        data["pass_defense_rating"] = data["Def_PassYds_Allowed_pg"] * data["Def_PassTD_Allowed_pg"] / (data["Def_INT_Forced_pg"] + 0.1)
        
        # Game context 
        data["total_attempts"] = data["Attempts"] + data["Rush_Att"]
        data["total_yards"] = data["Pass_Yds"] + data["Rush_Yds"]
        data["total_touchdowns"] = data["Pass_TD"] + data["Rush_TD"]
        
        # Rolling totals
        data["total_attempts_rolling_3"] = data["total_attempts"].rolling(3, closed='left').mean()
        data["total_yards_rolling_3"] = data["total_yards"].rolling(3, closed='left').mean()
        data["total_touchdowns_rolling_3"] = data["total_touchdowns"].rolling(3, closed='left').mean()
        
        # Advanced efficiency 
        data["efficiency_score"] = data["ypa_rolling_3"] * data["tpa_rolling_3"] / (data["ipa_rolling_3"] + 0.01)
        data["volume_score"] = data["total_attempts_rolling_3"] * data["total_yards_rolling_3"] / 1000
        data["touchdown_efficiency"] = data["total_touchdowns_rolling_3"] / (data["total_attempts_rolling_3"] + 1)
        data["yards_per_touchdown"] = data["total_yards_rolling_3"] / (data["total_touchdowns_rolling_3"] + 1)
        
        # Opponent difficulty 
        data["opponent_sack_rate"] = data["Def_Sacks_pg"]
        data["opponent_difficulty"] = (data["Def_FantasyPts_Allowed_pg"] * data["Def_Sacks_pg"]) / (data["Def_INT_Forced_pg"] + 0.1)
        
        # Momentum indicators
        data["fantasy_momentum"] = data["Fantasy_Points"].diff().rolling(3, closed='left').mean()
        data["pass_yds_momentum"] = data["Pass_Yds"].diff().rolling(3, closed='left').mean()
        data["touchdown_momentum"] = data["total_touchdowns"].diff().rolling(3, closed='left').mean()
        
        # Consistency features
        data["fantasy_consistency"] = 1 / (data["fantasy_volatility"] + 0.1)
        data["pass_yds_consistency"] = 1 / (data["pass_yds_volatility"] + 0.1)
        
        # Advanced efficiency 
        data["completion_efficiency"] = data["completion_rate_rolling_3"] * data["ypa_rolling_3"]
        data["touchdown_rate"] = data["total_touchdowns_rolling_3"] / data["total_attempts_rolling_3"]
        data["interception_rate"] = data["int_rolling_3"] / data["total_attempts_rolling_3"]
        
        # Game flow 
        data["high_volume_games"] = (data["total_attempts_rolling_3"] > data["total_attempts_rolling_3"].quantile(0.75)).astype(int)
        data["high_scoring_games"] = (data["total_touchdowns_rolling_3"] > data["total_touchdowns_rolling_3"].quantile(0.75)).astype(int)
    
        return data
    
    def preprocess_data(self, data: pd.DataFrame, is_training: bool = True) -> tuple[pd.DataFrame, list]:
        """Preprocess QB data for training/prediction"""
        data = data.copy()
        
        # Handle date column
        if "Date" in data.columns:
            data["date"] = pd.to_datetime(data["Date"])
        elif "date" not in data.columns:
            data["date"] = pd.to_datetime(data["Season"].astype(str) + "-" + data["Week"].astype(str) + "-01")
        
        #Create opponent code if Opponent column exists 
        if "Opponent" in data.columns and "opp_code" not in data.columns:
            data["opp_code"] = data["Opponent"].astype("category").cat.codes
        
        data["hour"] = 12  
        data["day_code"] = data["date"].dt.dayofweek
        
        # handle target 
        if "Fantasy_Points" in data.columns:
            data["target"] = data["Fantasy_Points"]
        else:
            data["target"] = 0  # Default 

        # Create all advanced features
        data = self.create_advanced_features(data)
        
        all_features = [
            "opp_code", "hour", "day_code", "season", "week",
            # Game context
            "is_playoff", "is_early_season", "is_late_season", "is_home",
            # Rolling averages
            "fantasy_rolling_3", "fantasy_rolling_5", "fantasy_rolling_10",
            "pass_yds_rolling_3", "pass_yds_rolling_5", "pass_yds_rolling_10",
            "pass_td_rolling_3", "pass_td_rolling_5", "pass_td_rolling_10",
            "int_rolling_3", "int_rolling_5", "int_rolling_10",
            "rush_yds_rolling_3", "rush_yds_rolling_5", "rush_yds_rolling_10",
            "rush_td_rolling_3", "rush_td_rolling_5", "rush_td_rolling_10",
            "completion_rate_rolling_3", "completion_rate_rolling_5", "completion_rate_rolling_10",
            # Recent trends
            "fantasy_trend", "pass_yds_trend", "pass_td_trend",
            # Volatility
            "fantasy_volatility", "pass_yds_volatility",
            # Efficiency metrics
            "ypa_rolling_3", "tpa_rolling_3", "ipa_rolling_3",
            "efficiency_score", "volume_score", "touchdown_efficiency", "yards_per_touchdown",
            # Defense features
            "defense_strength", "pass_defense_rating", "opponent_sack_rate", "opponent_difficulty",
            # Momentum
            "fantasy_momentum", "pass_yds_momentum", "touchdown_momentum",
            # Consistency
            "fantasy_consistency", "pass_yds_consistency",
            # Advanced efficiency 
            "completion_efficiency", "touchdown_rate", "interception_rate",
            # Game flow 
            "high_volume_games", "high_scoring_games",
            # Totals
            "total_attempts_rolling_3", "total_yards_rolling_3", "total_touchdowns_rolling_3"
        ]
        # Single NaN fill operation
        for feature in all_features:
            if feature in data.columns and data[feature].isna().any():
                data[feature] = data[feature].fillna(data[feature].median())
        
        # handle training vs prediction data
        if is_training:
            data = data.dropna(subset=["target"])
        else:
            data["target"] = data["target"].fillna(0)
        
        return data, all_features
    
    def select_features(self, train_data: pd.DataFrame, all_features: list) -> list:
        """Select top features based on importance"""
        xgb_importance = xgb.XGBRegressor(n_estimators=100, random_state=42)
        xgb_importance.fit(train_data[all_features], train_data["target"])
        
        self.feature_importance = pd.DataFrame({
            'feature': all_features,
            'importance': xgb_importance.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # select top 25 Most important features 
        self.top_features = self.feature_importance.head(25)['feature'].tolist()
        return self.top_features
    
    def train_model(self, train_data: pd.DataFrame) -> None:
        """Train XGBoost model with hyperparameter tuning"""        
        xgb_params = {
            'n_estimators': [300, 500],
            'max_depth': [4, 6],
            'learning_rate': [0.05, 0.1],
            'subsample': [0.8, 0.9],
            'colsample_bytree': [0.8, 0.9],
            'reg_alpha': [0, 0.1],
            'reg_lambda': [0, 0.1]
        }
        
        xgb_grid = GridSearchCV(
            xgb.XGBRegressor(random_state=42), 
            xgb_params, 
            cv=3, 
            scoring='neg_mean_absolute_error', 
            n_jobs=-1,
            verbose=0
        )
        xgb_grid.fit(train_data[self.top_features], train_data["target"])
        
        self.model = xgb_grid.best_estimator_
        best_mae = -xgb_grid.best_score_
        self.is_trained = True
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Make predictions for given data"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        data_copy = data.copy()
        
        # Fill missing Mahomes stats with 2024 averages
        mahomes_2024_avg = {
            'Completions': 26.5,
            'Attempts': 38.2, 
            'Pass_Yds': 295,
            'Pass_TD': 2.1,
            'INT': 0.65,
            'Rush_Att': 4.2,
            'Rush_Yds': 15,
            'Rush_TD': 0.2,
            'Fantasy_Points': 19.5
        }

        for col, default_val in mahomes_2024_avg.items():
            if col in data_copy.columns:
                data_copy[col] = data_copy[col].fillna(default_val)
        
        # Preprocess the data
        processed_data, _ = self.preprocess_data(data_copy, is_training=False)
        
        if len(processed_data) == 0:
            print("No data remaining after preprocessing")
            return np.array([])
        
        # Ensure all features exist
        for feature in self.top_features:
            if feature not in processed_data.columns:
                processed_data[feature] = 0
        
        # Final NaN cleanup
        for feature in self.top_features:
            if processed_data[feature].isna().any():
                processed_data[feature] = processed_data[feature].fillna(0)
        
        predictions = self.model.predict(processed_data[self.top_features])
        return predictions
    
    def predict_season(self, qb_data: pd.DataFrame, season_year: int) -> pd.DataFrame:
        """Predict fantasy points for a specific season"""
        season_data = qb_data[qb_data["Season"] == season_year].copy()
        
        if len(season_data) == 0:
            raise ValueError(f"No data found for season {season_year}")
        
        print(f"Predicting {season_year} season with {len(season_data)} games")
        
        predictions = self.predict(season_data)
        
        if len(predictions) == 0:
            print("No predictions generated")
            return pd.DataFrame(columns=["Week", "Opponent", "Predicted_Fantasy_Points"])
        
        # Ensure matching lengths
        if len(predictions) != len(season_data):
            print(f"Warning: {len(predictions)} predictions for {len(season_data)} games")
            season_data = season_data.head(len(predictions)).copy()
        
        results = season_data[["Week", "Opponent"]].copy()
        results["Predicted_Fantasy_Points"] = predictions
        results = results.sort_values("Week")
        
        return results
    
    def evaluate_model(self, test_data: pd.DataFrame) -> dict:
        """Evaluate model performance on test data"""
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")
        
        predictions = self.predict(test_data)
        
        mae = mean_absolute_error(test_data["target"], predictions)
        rmse = np.sqrt(mean_squared_error(test_data["target"], predictions))
        r2 = r2_score(test_data["target"], predictions)
        
        return {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'predictions': predictions
        }
    
    def train_on_qb_data(self, qb_data: pd.DataFrame) -> None:
        """Train the model on QB's historical data"""
        processed_data, all_features = self.preprocess_data(qb_data, is_training=True)
        
        if len(processed_data) < 20:
            raise ValueError("Insufficient training data. Need at least 20 games.")
        
        self.select_features(processed_data, all_features)
        self.train_model(processed_data)

def predict_qb_fantasy_points(qb_data: pd.DataFrame, qb_name: str, season_year: int = 2025) -> pd.DataFrame:
    """
    Predict fantasy points for any QB
    """
    predictor = QBFantasyPredictor()
    
    # Train on historical data only
    historical_data = qb_data[qb_data["Season"] != season_year].copy()
    
    print(f"Training model for {qb_name} using {len(historical_data)} historical games")
    predictor.train_on_qb_data(historical_data)
    predictions = predictor.predict_season(qb_data, season_year)
    
    if len(predictions) == 0:
        print("No predictions were generated")
        return pd.DataFrame()
    
    # Summry stats
    avg_prediction = predictions["Predicted_Fantasy_Points"].mean()
    min_prediction = predictions["Predicted_Fantasy_Points"].min()
    max_prediction = predictions["Predicted_Fantasy_Points"].max()
    
    print(f"\n{qb_name} {season_year} Predictions:")
    print(f"Average Fantasy Points: {avg_prediction:.2f}")
    print(f"Range: {min_prediction:.1f} - {max_prediction:.1f}")
    print(f"Total Games: {len(predictions)}")
    
    return predictions

if __name__ == "__main__":
    try:
        # Load complete dataset
        complete_data = pd.read_csv("data/mahomes_complete_2017_2025.csv")
        
        # Make predictions for 2025
        predictions = predict_qb_fantasy_points(complete_data, "Patrick Mahomes", 2025)
        predictions.to_csv('mahomes_2025_predictions.csv', index=False)
        print("\nPredictions saved to 'mahomes_2025_predictions.csv'")
        
        # Show detailed predictions
        print("\nDetailed 2025 Predictions:")
        print(predictions.to_string(index=False))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()