# model_train.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

# Load data
df = pd.read_csv("delivery_data.csv")

# Features and target
X = df[["distance_km", "num_stops", "weather", "time_of_day", "traffic_level"]]
y = df["actual_eta_min"]

# Preprocessing
categorical_features = ["weather", "time_of_day", "traffic_level"]
preprocessor = ColumnTransformer(
    transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)],
    remainder="passthrough"
)

# Model pipeline
model = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", RandomForestRegressor(n_estimators=100, random_state=42))
])

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model.fit(X_train, y_train)

# Save model
joblib.dump(model, "eta_model.pkl")
print("✅ Model trained and saved as eta_model.pkl")
