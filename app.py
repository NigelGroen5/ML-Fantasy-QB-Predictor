from flask import Flask, render_template, request, jsonify, redirect
import pandas as pd
import os
import glob
from typing import Dict, List, Tuple

app = Flask(__name__)

class QBDataManager:
    """Manages QB prediction data and calculations"""
    
    def __init__(self):
        self.predictions_dir = "data/predictions"
        self.schedule_file = "data/nfl_schedule_2025.csv"
        self.qb_predictions = {}
        self.qb_totals = {}
        self.schedule_data = None
        self.load_data()
    
    def load_data(self):
        """Load all QB prediction data and schedule data"""
        # Load schedule data
        if os.path.exists(self.schedule_file):
            self.schedule_data = pd.read_csv(self.schedule_file)
        
        # Load all QB prediction files
        prediction_files = glob.glob(os.path.join(self.predictions_dir, "*_2025_predictions.csv"))
        
        for file_path in prediction_files:
            # Extract QB name from filename (e.g., "josh_allen_2025_predictions.csv" -> "josh_allen")
            filename = os.path.basename(file_path)
            qb_name = filename.replace("_2025_predictions.csv", "").replace("_", " ").title()
            
            # Load predictions
            df = pd.read_csv(file_path)
            self.qb_predictions[qb_name] = df
            
            # Calculate total projected points (excluding bye weeks)
            total_points = self.calculate_total_points(qb_name, df)
            self.qb_totals[qb_name] = total_points
    
    def calculate_total_points(self, qb_name: str, predictions_df: pd.DataFrame) -> float:
        """Calculate total projected fantasy points for a QB, handling bye weeks"""
        if self.schedule_data is None:
            # If no schedule data, just sum all predictions
            return predictions_df['Predicted_Fantasy_Points'].sum()
        
        # Find the team for this QB (we'll need to map QB names to teams)
        # For now, we'll use a simple mapping - you can expand this later
        qb_team_map = {
            'Josh Allen': 'BUF',
            'Jalen Hurts': 'PHI', 
            'Lamar Jackson': 'BAL',
            'Mahomes': 'KC'
        }
        
        team = qb_team_map.get(qb_name, '')
        if not team:
            # If we can't find the team, just sum all predictions
            return predictions_df['Predicted_Fantasy_Points'].sum()
        
        # Get team schedule to find bye weeks
        team_schedule = self.schedule_data[self.schedule_data['Tm'] == team]
        if team_schedule.empty:
            return predictions_df['Predicted_Fantasy_Points'].sum()
        
        # Get bye weeks
        bye_weeks = []
        for week in range(1, 19):  # NFL has 18 weeks
            week_col = f'Week{week}'
            if week_col in team_schedule.columns:
                if team_schedule.iloc[0][week_col] == 'BYE':
                    bye_weeks.append(week)
        
        # Sum predictions excluding bye weeks
        total_points = 0
        for _, row in predictions_df.iterrows():
            week = int(row['Week'])
            if week not in bye_weeks:
                total_points += row['Predicted_Fantasy_Points']
        
        return total_points
    
    def get_qb_rankings(self) -> List[Tuple[str, float]]:
        """Get QB rankings sorted by total projected points"""
        rankings = [(name, points) for name, points in self.qb_totals.items()]
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def get_qb_comparison_data(self, qb_names: List[str]) -> Dict:
        """Get weekly comparison data for selected QBs"""
        comparison_data = {
            'weeks': list(range(1, 19)),  
            'qbs': {},
            'totals': {},  
            'schedule': self.schedule_data.to_dict('records') if self.schedule_data is not None else []
        }
        
        # Get data for each selected QB
        for qb_name in qb_names:
            if qb_name in self.qb_predictions:
                qb_data = self.qb_predictions[qb_name]
                qb_weekly_data = {}
                
                # Get QB's team for bye week checking
                qb_team_map = {
                    'Josh Allen': 'BUF',
                    'Jalen Hurts': 'PHI', 
                    'Lamar Jackson': 'BAL',
                    'Mahomes': 'KC'
                }
                team = qb_team_map.get(qb_name, '')
                
                # Get bye weeks for this team
                bye_weeks = []
                if team and self.schedule_data is not None:
                    team_schedule = self.schedule_data[self.schedule_data['Tm'] == team]
                    if not team_schedule.empty:
                        for week in range(1, 19):
                            week_col = f'Week{week}'
                            if week_col in team_schedule.columns:
                                if team_schedule.iloc[0][week_col] == 'BYE':
                                    bye_weeks.append(week)
                
                # Process each week 
                for week in range(1, 19):
                    if week in bye_weeks:
                        qb_weekly_data[week] = {
                            'opponent': 'BYE',
                            'predicted_points': 0.0,
                            'is_bye': True
                        }
                    else:
                        # Find the prediction for this week
                        week_data = qb_data[qb_data['Week'] == week]
                        if not week_data.empty:
                            row = week_data.iloc[0]
                            qb_weekly_data[week] = {
                                'opponent': row['Opponent'],
                                'predicted_points': row['Predicted_Fantasy_Points'],
                                'is_bye': False
                            }
                        else:
                            # No prediction data for this week
                            qb_weekly_data[week] = {
                                'opponent': 'TBD',
                                'predicted_points': 0.0,
                                'is_bye': False
                            }
                
                comparison_data['qbs'][qb_name] = qb_weekly_data
                # Add the pre-calculated total points
                comparison_data['totals'][qb_name] = self.qb_totals.get(qb_name, 0)
        
        return comparison_data

# Initialize data manager
qb_manager = QBDataManager()

@app.route('/')
def index():
    """Main page showing QB rankings"""
    rankings = qb_manager.get_qb_rankings()
    return render_template('index.html', rankings=rankings)

@app.route('/compare')
def compare():
    """Comparison page for selected QBs"""
    selected_qbs = request.args.getlist('qbs')
    
    if len(selected_qbs) < 2:
        # Redirect back to index if not enough QBs selected
        return redirect('/')
    
    comparison_data = qb_manager.get_qb_comparison_data(selected_qbs)
    return render_template('compare.html', 
                         comparison_data=comparison_data, 
                         selected_qbs=selected_qbs)

@app.route('/api/qb_rankings')
def api_qb_rankings():
    """API endpoint for QB rankings"""
    rankings = qb_manager.get_qb_rankings()
    return jsonify([{'name': name, 'total_points': points} for name, points in rankings])

@app.route('/api/qb_comparison')
def api_qb_comparison():
    """API endpoint for QB comparison data"""
    selected_qbs = request.args.getlist('qbs')
    if len(selected_qbs) < 2:
        return jsonify({'error': 'Please select at least 2 QBs'}), 400
    
    comparison_data = qb_manager.get_qb_comparison_data(selected_qbs)
    return jsonify(comparison_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
