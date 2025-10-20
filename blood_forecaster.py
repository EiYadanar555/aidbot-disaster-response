# blood_forecaster.py — Blood Demand Forecasting & Supply-Demand Matching

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib

MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

class BloodDemandForecaster:
    """
    Predicts blood demand based on:
    - Historical disaster patterns
    - Disaster predictions (from disaster_predictor)
    - Regional population data
    - Seasonal patterns
    
    Objectives Met:
    - Predict blood shortages before they happen
    - Match supply with demand regionally
    - Eliminate waste through smart redistribution
    """
    
    def __init__(self):
        self.demand_model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        )
        self.disaster_encoder = LabelEncoder()
        self.region_encoder = LabelEncoder()
        self.trained = False
        
    def create_synthetic_training_data(self):
        """
        Create synthetic training data based on real-world disaster → blood usage patterns.
        In production, replace with actual historical data.
        
        Based on research:
        - Earthquake: 50-200 units per 1000 affected
        - Flood: 20-80 units per 1000 affected
        - Storm: 30-100 units per 1000 affected
        - Epidemic: 10-40 units per 1000 affected
        - Drought: 5-20 units per 1000 affected (indirect)
        """
        print("📊 Generating synthetic training data...")
        
        disaster_blood_usage = {
            'Earthquake': {'min': 50, 'max': 200, 'avg': 125},
            'Flood': {'min': 20, 'max': 80, 'avg': 50},
            'Storm': {'min': 30, 'max': 100, 'avg': 65},
            'Epidemic': {'min': 10, 'max': 40, 'avg': 25},
            'Drought': {'min': 5, 'max': 20, 'avg': 12},
            'Landslide': {'min': 40, 'max': 150, 'avg': 95},
            'Wildfire': {'min': 25, 'max': 90, 'avg': 57},
        }
        
        regions = [
            'Southeast Asia', 'East Asia', 'South Asia', 
            'Central Asia', 'Western Asia'
        ]
        
        data = []
        np.random.seed(42)
        
        # Generate 5000 synthetic historical records
        for _ in range(5000):
            disaster = np.random.choice(list(disaster_blood_usage.keys()))
            region = np.random.choice(regions)
            
            # Population affected (in thousands)
            pop_affected = np.random.uniform(1, 100)  # 1k to 100k people
            
            # Severity (1-5 scale)
            severity = np.random.randint(1, 6)
            
            # Season (affects logistics and availability)
            season = np.random.choice(['Spring', 'Summer', 'Fall', 'Winter'])
            season_encoded = {'Spring': 0, 'Summer': 1, 'Fall': 2, 'Winter': 3}[season]
            
            # Calculate blood units needed based on disaster type and severity
            base_rate = disaster_blood_usage[disaster]['avg']
            severity_multiplier = severity / 3.0  # Scale severity impact
            
            blood_units = int(
                (pop_affected * base_rate / 1000) * severity_multiplier * 
                np.random.uniform(0.8, 1.2)  # Add realistic variance
            )
            
            # Ensure minimum of 5 units
            blood_units = max(5, blood_units)
            
            data.append({
                'disaster_type': disaster,
                'region': region,
                'population_affected_thousands': pop_affected,
                'severity': severity,
                'season': season_encoded,
                'blood_units_used': blood_units
            })
        
        df = pd.DataFrame(data)
        print(f"✅ Generated {len(df)} synthetic training records")
        return df
    
    def train(self, historical_data=None):
        """
        Train the blood demand forecasting model
        
        Args:
            historical_data: DataFrame with columns:
                - disaster_type
                - region
                - population_affected_thousands
                - severity
                - season (0-3)
                - blood_units_used (target)
        """
        print("\n🎯 Training Blood Demand Forecasting Model...")
        
        # Use synthetic data if no real data provided
        if historical_data is None:
            historical_data = self.create_synthetic_training_data()
        
        # Encode categorical variables
        historical_data['disaster_encoded'] = self.disaster_encoder.fit_transform(
            historical_data['disaster_type']
        )
        historical_data['region_encoded'] = self.region_encoder.fit_transform(
            historical_data['region']
        )
        
        # Prepare features
        X = historical_data[[
            'disaster_encoded', 
            'region_encoded',
            'population_affected_thousands',
            'severity',
            'season'
        ]]
        
        y = historical_data['blood_units_used']
        
        # Train model
        self.demand_model.fit(X, y)
        self.trained = True
        
        # Calculate training score
        train_score = self.demand_model.score(X, y)
        print(f"✅ Model trained successfully!")
        print(f"   Training R² Score: {train_score:.3f}")
        
        # Feature importance
        feature_names = [
            'Disaster Type', 'Region', 'Population Affected', 
            'Severity', 'Season'
        ]
        importances = self.demand_model.feature_importances_
        
        print(f"\n🔍 Feature Importance:")
        for name, importance in sorted(
            zip(feature_names, importances), 
            key=lambda x: x[1], 
            reverse=True
        ):
            print(f"   {name}: {importance:.3f}")
    
    def predict_demand(self, disaster_predictions, region_populations=None):
        """
        Predict blood demand based on disaster predictions
        
        Args:
            disaster_predictions: List of dicts with:
                - region
                - predicted_disaster
                - confidence
                - year (optional)
            
            region_populations: Dict of {region: population_in_thousands}
        
        Returns:
            DataFrame with predicted blood demand
        """
        if not self.trained:
            print("⚠️ Model not trained. Training with synthetic data...")
            self.train()
        
        # Default population data (can be replaced with real data)
        if region_populations is None:
            region_populations = {
                'Southeast Asia': 50,  # 50k affected on average
                'East Asia': 45,
                'South Asia': 60,
                'Central Asia': 30,
                'Western Asia': 35,
                'Unknown': 40
            }
        
        results = []
        current_season = (datetime.now().month % 12) // 3  # 0-3 for seasons
        
        for pred in disaster_predictions:
            region = pred.get('region', 'Unknown')
            disaster = pred.get('predicted_disaster', 'Unknown')
            confidence = pred.get('confidence', 50) / 100
            year = pred.get('year', datetime.now().year)
            
            # Skip if disaster type not in training data
            if disaster not in self.disaster_encoder.classes_:
                continue
            
            # Encode inputs
            disaster_encoded = self.disaster_encoder.transform([disaster])[0]
            
            # Handle unknown regions
            if region in self.region_encoder.classes_:
                region_encoded = self.region_encoder.transform([region])[0]
            else:
                # Use most common region encoding as fallback
                region_encoded = 0
            
            population = region_populations.get(region, 40)
            
            # Estimate severity based on confidence
            # High confidence = likely severe disaster
            severity = int(np.clip(1 + (confidence * 4), 1, 5))
            
            # Prepare features
            features = np.array([[
                disaster_encoded,
                region_encoded,
                population,
                severity,
                current_season
            ]])
            
            # Predict blood units needed
            predicted_units = int(self.demand_model.predict(features)[0])
            
            # Adjust by confidence (lower confidence = wider range)
            uncertainty = int(predicted_units * (1 - confidence) * 0.3)
            
            results.append({
                'region': region,
                'predicted_disaster': disaster,
                'year': year,
                'predicted_blood_units': predicted_units,
                'confidence': confidence * 100,
                'severity_estimate': severity,
                'range_min': max(5, predicted_units - uncertainty),
                'range_max': predicted_units + uncertainty,
                'alert_level': self._get_alert_level(predicted_units)
            })
        
        return pd.DataFrame(results)
    
    def _get_alert_level(self, units):
        """Categorize demand into alert levels"""
        if units >= 100:
            return 'HIGH'
        elif units >= 50:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def match_supply_demand(self, current_inventory, demand_predictions):
        """
        Match regional blood supply with predicted demand
        Returns recommendations for redistribution
        
        Args:
            current_inventory: DataFrame from read_blood_df()
            demand_predictions: DataFrame from predict_demand()
        
        Returns:
            List of redistribution recommendations
        """
        print("\n🔄 Matching Supply with Predicted Demand...")
        
        recommendations = []
        
        # Group current inventory by region
        supply_by_region = current_inventory.groupby('Region')['Units'].sum().to_dict()
        
        for _, pred in demand_predictions.iterrows():
            region = pred['region']
            needed = pred['predicted_blood_units']
            disaster = pred['predicted_disaster']
            
            # Get current supply in region
            current_supply = supply_by_region.get(region, 0)
            
            # Calculate shortage/surplus
            balance = current_supply - needed
            coverage_percent = (current_supply / needed * 100) if needed > 0 else 100
            
            recommendation = {
                'region': region,
                'predicted_disaster': disaster,
                'current_supply': current_supply,
                'predicted_demand': needed,
                'balance': balance,
                'coverage_percent': round(coverage_percent, 1)
            }
            
            if balance < 0:
                # SHORTAGE
                shortage = abs(balance)
                recommendation['status'] = '🔴 SHORTAGE'
                recommendation['action'] = f'REQUEST {shortage} units from surplus regions'
                recommendation['priority'] = 'HIGH' if shortage > 50 else 'MEDIUM'
                
            elif balance > needed * 0.5:
                # SURPLUS (more than 150% of need)
                surplus = int(balance - (needed * 0.2))  # Keep 20% buffer
                if surplus > 0:
                    recommendation['status'] = '🟢 SURPLUS'
                    recommendation['action'] = f'OFFER {surplus} units to shortage regions'
                    recommendation['priority'] = 'LOW'
                else:
                    recommendation['status'] = '🟡 ADEQUATE'
                    recommendation['action'] = 'No action needed'
                    recommendation['priority'] = 'NONE'
                    
            else:
                # ADEQUATE
                recommendation['status'] = '🟡 ADEQUATE'
                recommendation['action'] = 'Monitor closely'
                recommendation['priority'] = 'NONE'
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def check_expiry_waste(self, current_inventory, days_threshold=7):
        """
        Identify blood about to expire that could be redistributed
        
        Args:
            current_inventory: DataFrame from read_blood_df()
            days_threshold: Days before expiry to flag (default 7)
        
        Returns:
            DataFrame of at-risk blood units
        """
        at_risk = []
        today = datetime.now().date()
        
        for _, row in current_inventory.iterrows():
            expires_str = row.get('ExpiresOn', '')
            if not expires_str:
                continue
            
            try:
                expires_date = datetime.strptime(expires_str, '%Y-%m-%d').date()
                days_left = (expires_date - today).days
                
                if 0 <= days_left <= days_threshold:
                    at_risk.append({
                        'id': row['id'],
                        'Region': row['Region'],
                        'Country': row['Country'],
                        'BloodType': row['BloodType'],
                        'Units': row['Units'],
                        'ExpiresOn': expires_str,
                        'DaysLeft': days_left,
                        'Status': 'URGENT' if days_left <= 3 else 'WARNING'
                    })
            except Exception:
                continue
        
        return pd.DataFrame(at_risk) if at_risk else pd.DataFrame()
    
    def save_model(self):
        """Save trained model to disk"""
        if not self.trained:
            print("⚠️ Cannot save untrained model")
            return
        
        model_path = os.path.join(MODELS_DIR, 'blood_demand_forecaster.joblib')
        encoder_path = os.path.join(MODELS_DIR, 'blood_encoders.joblib')
        
        joblib.dump(self.demand_model, model_path)
        joblib.dump({
            'disaster': self.disaster_encoder,
            'region': self.region_encoder
        }, encoder_path)
        
        metadata = {
            'created_at': datetime.now().isoformat(),
            'model_type': 'RandomForestRegressor',
            'disaster_types': list(self.disaster_encoder.classes_),
            'regions': list(self.region_encoder.classes_)
        }
        
        with open(os.path.join(MODELS_DIR, 'blood_model_metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Model saved to {MODELS_DIR}/")
    
    def load_model(self):
        """Load trained model from disk"""
        model_path = os.path.join(MODELS_DIR, 'blood_demand_forecaster.joblib')
        encoder_path = os.path.join(MODELS_DIR, 'blood_encoders.joblib')
        
        if not os.path.exists(model_path):
            print("⚠️ No saved model found. Please train first.")
            return False
        
        self.demand_model = joblib.load(model_path)
        encoders = joblib.load(encoder_path)
        self.disaster_encoder = encoders['disaster']
        self.region_encoder = encoders['region']
        self.trained = True
        
        print("✅ Model loaded successfully")
        return True


def main():
    """Standalone training script"""
    print("="*60)
    print("🩸 Blood Demand Forecasting Model Training")
    print("="*60)
    
    forecaster = BloodDemandForecaster()
    forecaster.train()
    forecaster.save_model()
    
    print("\n" + "="*60)
    print("🎉 TRAINING COMPLETE!")
    print("="*60)
    print(f"\n📂 Model saved to: {MODELS_DIR}/")
    print("\n✅ Next: Integrate into Streamlit app (see blood_tab_enhanced)")


if __name__ == "__main__":
    main()