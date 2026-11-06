
import pandas as pd
import joblib
import os

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

data = pd.read_csv(
    os.path.join(BASE_DIR, "training_examples.csv")
)

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

required_columns = feature_columns + ["product_id", "expert_label"]

missing = [col for col in required_columns if col not in data.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

# Remove rows without a target or product ID
data = data.dropna(subset=["expert_label", "product_id"]).copy()

# Convert numeric columns
for col in numeric_features + ["expert_label"]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data = data.dropna(subset=["expert_label", "product_id"])

if not data["expert_label"].between(1, 5).all():
    raise ValueError("Labels must be between 1 and 5.")

if data["product_id"].nunique() < 4:
    raise ValueError("At least 4 unique products are required.")

X = data[feature_columns]
y = data["expert_label"]

# Handle missing numerical and categorical values
numeric_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
    ("numbers", numeric_pipeline, numeric_features),
    ("categories", categorical_pipeline, categorical_features)
])

neural_network = MLPRegressor(
    hidden_layer_sizes=(32, 16),
    activation="relu",
    solver="adam",
    learning_rate_init=0.001,
    max_iter=1500,
    random_state=42,
    early_stopping=True
)

model = Pipeline([
    ("preprocessor", preprocessor),
    ("neural_network", neural_network)
])

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

print("Training FoodSage MLP neural network...")
print("Training examples:", len(X_train))
print("Testing examples:", len(X_test))

model.fit(X_train, y_train)

predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)

print("\nModel Evaluation")
print("----------------------")
print("Mean Absolute Error:", round(mae, 3))

model_path = os.path.join(BASE_DIR, "foodsage_model.joblib")

joblib.dump(model, model_path)

print("\nModel saved successfully!")
print("File: foodsage_model.joblib")
print("\nFoodSage training completed!")
