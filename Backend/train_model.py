import pandas as pd
import joblib
import os

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error

# Find the folder containing this Python file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load training dataset
data = pd.read_csv(os.path.join(BASE_DIR, "training_examples.csv"))

# Columns used by the model
numeric_features = [
    "added_sugar_g",
    "fiber_g",
    "protein_g",
    "sodium_mg",
    "saturated_fat_g"
]

categorical_features = [
    "category",
    "diet",
    "priority",
    "vegetarian",
    "vegan"
]

feature_columns = numeric_features + categorical_features

# Check required columns
required_columns = feature_columns + ["product_id", "expert_label"]

missing = [col for col in required_columns if col not in data.columns]

if missing:
    raise ValueError(f"Missing columns in CSV: {missing}")

if data[required_columns].isnull().any().any():
    raise ValueError("Some required training values are missing.")

if not data["expert_label"].between(1, 5).all():
    raise ValueError("expert_label values must be between 1 and 5.")

if data["product_id"].nunique() < 4:
    raise ValueError("Please provide at least 4 distinct product IDs.")

# Separate input features and target ratings
X = data[feature_columns]
y = data["expert_label"]

# Prepare numeric and categorical data
preprocessor = ColumnTransformer(
    transformers=[
        ("numbers", StandardScaler(), numeric_features),
        (
            "categories",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        )
    ]
)

# Create MLP neural network
neural_network = MLPRegressor(
    hidden_layer_sizes=(32, 16),
    activation="relu",
    solver="adam",
    learning_rate_init=0.001,
    max_iter=1500,
    random_state=42
)

# Combine preprocessing and neural network
model = Pipeline([
    ("preprocessor", preprocessor),
    ("neural_network", neural_network)
])

# Split data by product ID to reduce data leakage
splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.25,
    random_state=42
)

train_indices, test_indices = next(
    splitter.split(X, y, groups=data["product_id"])
)

X_train = X.iloc[train_indices]
X_test = X.iloc[test_indices]

y_train = y.iloc[train_indices]
y_test = y.iloc[test_indices]

# Train the model
print("Training FoodSage MLP neural network...")

model.fit(X_train, y_train)

# Evaluate the model
predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)

print("\nModel Evaluation")
print("----------------------")
print("Mean Absolute Error:", round(mae, 3))

# Save trained model
model_path = os.path.join(BASE_DIR, "foodsage_model.joblib")

joblib.dump(model, model_path)

print("\nModel saved successfully!")
print("File: foodsage_model.joblib")
print("\nFoodSage training completed!")