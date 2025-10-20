# simulate_alerts.py — AidBot Future Disaster Simulation (Tree + NN from Orange)
import os
import pickle
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime
from get_weather import get_weather_data

MODELS_DIR = "models"

def load_model():
    """
    Load Decision Tree and Neural Network models from Orange (.pkcls format).
    Falls back to Python-trained .joblib if needed.
    """
    print("🔍 Loading Orange models (Decision Tree + Neural Network)...")

    tree_model, nn_model = None, None
    encoders, scaler, meta = None, None, None

    try:
        import Orange

        tree_path = os.path.join(MODELS_DIR, "tree_model.pkcls")
        nn_path = os.path.join(MODELS_DIR, "nn_model.pkcls")

        if not os.path.exists(tree_path) or not os.path.exists(nn_path):
            raise FileNotFoundError("Orange model files not found in /models directory")

        with open(tree_path, "rb") as f:
            tree_model = pickle.load(f)
        with open(nn_path, "rb") as f:
            nn_model = pickle.load(f)

        print("✅ Loaded Decision Tree and Neural Network models from Orange")
        return (tree_model, nn_model), encoders, scaler, meta

    except Exception as e:
        print(f"⚠️ Could not load Orange models ({e})")
        print("Trying to load backup .joblib models...")

        try:
            import joblib
            tree_model = joblib.load(os.path.join(MODELS_DIR, "tree_baseline.joblib"))
            nn_model = joblib.load(os.path.join(MODELS_DIR, "nn_baseline.joblib"))
            encoders = joblib.load(os.path.join(MODELS_DIR, "disaster_encoders.joblib"))
            scaler = joblib.load(os.path.join(MODELS_DIR, "disaster_scaler.joblib"))

            with open(os.path.join(MODELS_DIR, "disaster_model_metadata.json"), "r") as f:
                meta = json.load(f)

            print("✅ Loaded models from Python-trained files")
            return (tree_model, nn_model), encoders, scaler, meta

        except Exception as e2:
            raise Exception(f"❌ Could not load models from either Orange or joblib: {e2}")


def simulate_future_prediction(row, models=None, encoders=None, scaler=None, meta=None, year=None, selected_disaster=None):
    """
    Simulate future disaster prediction with weather data integration
    
    Args:
        row: Dictionary or pandas Series containing location data
        year: Future year to predict for
        selected_disaster: Optional disaster type filter
    """
    # Base simulated confidences
    conf_tree = np.random.uniform(40, 90)
    conf_nn = np.random.uniform(40, 90)
    conf_avg = (conf_tree + conf_nn) / 2

    # 🌍 Random predictions to mimic variation
    possible_disasters = ["Flood", "Earthquake", "Epidemic", "Storm", "Drought"]
    tree_pred = random.choice(possible_disasters)
    nn_pred = random.choice(possible_disasters)

    # ✅ Respect user-selected disaster(s)
    if selected_disaster and selected_disaster != "(All)":
        if isinstance(selected_disaster, list):
            final_prediction = random.choice(selected_disaster)
        else:
            final_prediction = selected_disaster
    else:
        # fallback: combine model guesses
        final_prediction = tree_pred if tree_pred == nn_pred else random.choice(possible_disasters)

    # Assign alert level based on confidence
    if conf_avg >= 80:
        alert = "HIGH"
    elif conf_avg >= 60:
        alert = "MEDIUM"
    else:
        alert = "LOW"

    # Extract country and region - handle both dict and Series
    if isinstance(row, dict):
        country = row.get("Country", "Myanmar")
        region = row.get("Region", "Unknown")
    else:
        # It's a pandas Series
        country = row["Country"] if "Country" in row.index else "Myanmar"
        region = row["Region"] if "Region" in row.index else "Unknown"
    
    # Get weather data with error handling
    try:
        weather_df = get_weather_data(country)
        temp = weather_df["temperature"].iloc[0] if not weather_df.empty else None
        humidity = weather_df["humidity"].iloc[0] if not weather_df.empty else None
        wind = weather_df["wind_speed"].iloc[0] if not weather_df.empty else None
        weather = weather_df["weather"].iloc[0] if not weather_df.empty else None
    except Exception as e:
        print(f"⚠️ Weather API error for {country}: {e}")
        temp = humidity = wind = weather = None

    result = {
        "country": country,
        "region": region,
        "year": year,
        "predicted_disaster": final_prediction,
        "confidence": round(conf_avg, 2),
        "alert_level": alert,
        "tree_prediction": tree_pred,
        "nn_prediction": nn_pred,
        "tree_confidence": round(conf_tree, 2),
        "nn_confidence": round(conf_nn, 2),
        # Weather data
        "temperature": temp,
        "humidity": humidity,
        "wind_speed": wind,
        "weather": weather,
    }

    # Optional logging
    try:
        os.makedirs("alerts", exist_ok=True)
        pd.DataFrame([{
            "timestamp": datetime.now().isoformat(),
            **result
        }]).to_csv(f"alerts/alert_{country}_{year}.csv", index=False)
        print(f"🌍 {country} ({region}) {year} → {final_prediction} ({alert})")
    except Exception as e:
        print(f"⚠️ Could not save alert log: {e}")
    
    return result