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
            # Extract QB name from filename 
            filename = os.path.basename(file_path)
            qb_name = filename.replace("_2025_predictions.csv", "").replace("_", " ").title()
            
            # Fix qb names
            qb_name_mapping = {
                'Mahomes': 'Patrick Mahomes',
                'Mathew Stafford': 'Matthew Stafford',
                'Cj Stroud': 'C.J. Stroud'
            }
            qb_name = qb_name_mapping.get(qb_name, qb_name)
            
            # Load predictions
            df = pd.read_csv(file_path)
            self.qb_predictions[qb_name] = df
            
            # Calculate total projected points 
            total_points = self.calculate_total_points(qb_name, df)
            self.qb_totals[qb_name] = total_points
    
    def calculate_total_points(self, qb_name: str, predictions_df: pd.DataFrame) -> float:
        """Calculate total projected fantasy points for a QB"""
        return predictions_df['Predicted_Fantasy_Points'].sum()
    
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
                for week in range(1, 19):
                    # Find the prediction for this week
                    week_data = qb_data[qb_data['Week'] == week]
                    if not week_data.empty:
                        row = week_data.iloc[0]
                        qb_weekly_data[week] = {
                            'opponent': row['Opponent'],
                            'predicted_points': row['Predicted_Fantasy_Points'],
                            'is_bye': row['Opponent'] == 'BYE'
                        }
                    else:
                        # handle no prediction for this week
                        qb_weekly_data[week] = {
                            'opponent': 'BYE',
                            'predicted_points': 0.0,
                            'is_bye': True
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
