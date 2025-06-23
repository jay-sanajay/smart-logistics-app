# train_eta_model.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

# Load data from delivery_logs.csv or your DB
df = pd.read_csv("delivery_data.csv")

# Select features and label
features = ["distance_km", "num_stops", "weather", "time_of_day", "traffic_level"]
X = pd.get_dummies(df[features])
y = df["actual_eta_min"]

# Train model
model = RandomForestRegressor()
model.fit(X, y)

# Save model
joblib.dump(model, "eta_model.pkl")
print("✅ Model saved as eta_model.pkl")
