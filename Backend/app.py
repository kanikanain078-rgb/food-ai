
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import re
import joblib

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. LOAD DATASET AND TRAINED ML MODEL
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(
    BASE_DIR,
    "packaged_foods_india_clean.csv"
)

MODEL_FILE = os.path.join(
    BASE_DIR,
    "foodsage_model.joblib"
)

products = pd.read_csv(
    DATA_FILE,
    encoding="utf-8-sig"
)

if "Data_Quality_Status" in products.columns:
    products = products[
        products["Data_Quality_Status"] == "Valid"
    ].copy()

products = products.reset_index(drop=True)

# Load trained MLP pipeline
ml_model = joblib.load(MODEL_FILE)

print("FoodSage ML model loaded successfully!")

NUTRIENTS = {
    "added_sugar": "Sugar_g",
    "fiber": "Dietary_Fiber_g",
    "protein": "Proteins_g",
    "sodium": "Sodium_mg",
    "saturated_fat": "Saturated_Fat_g"
}

for column in NUTRIENTS.values():
    products[column] = pd.to_numeric(
        products[column],
        errors="coerce"
    )

products["Serving_Size_g"] = pd.to_numeric(
    products["Serving_Size_g"],
    errors="coerce"
)

print("Dataset loaded:", len(products), "products")


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def get_priority(data):

    priority = str(
        data.get("priority", "added_sugar")
    ).strip().lower()

    aliases = {
        "added_sugar_g": "added_sugar",
        "fiber_g": "fiber",
        "protein_g": "protein",
        "sodium_mg": "sodium",
        "saturated_fat_g": "saturated_fat"
    }

    priority = aliases.get(priority, priority)

    if priority not in NUTRIENTS:
        return None

    return priority


def product_details(row, product_id):

    return {
        "product_id": str(product_id),
        "product_name": clean_text(row["Item name"]),
        "brand": clean_text(row["Brand_Name"]),
        "category": clean_text(row["Category"]),

        "serving_size": (
            round(float(row["Serving_Size_g"]), 2)
            if pd.notna(row["Serving_Size_g"])
            else None
        ),

        "added_sugar": (
            round(float(row["Sugar_g"]), 2)
            if pd.notna(row["Sugar_g"])
            else None
        ),

        "fiber": (
            round(float(row["Dietary_Fiber_g"]), 2)
            if pd.notna(row["Dietary_Fiber_g"])
            else None
        ),

        "protein": (
            round(float(row["Proteins_g"]), 2)
            if pd.notna(row["Proteins_g"])
            else None
        ),

        "sodium": (
            round(float(row["Sodium_mg"]), 2)
            if pd.notna(row["Sodium_mg"])
            else None
        ),

        "saturated_fat": (
            round(float(row["Saturated_Fat_g"]), 2)
            if pd.notna(row["Saturated_Fat_g"])
            else None
        )
    }


# ==========================================
# 3. ML PREDICTION
# ==========================================

def predict_ml_score(row, priority):

    # These names and categorical values must match
    # the features used in train_model.py.

    model_input = pd.DataFrame([{
        "added_sugar_g": row["Sugar_g"],
        "fiber_g": row["Dietary_Fiber_g"],
        "protein_g": row["Proteins_g"],
        "sodium_mg": row["Sodium_mg"],
        "saturated_fat_g": row["Saturated_Fat_g"],

        "category": clean_text(
            row["Category"]
        ).lower(),

        # Training examples used these fixed values.
        "diet": "vegetarian",
        "priority": priority,
        "vegetarian": True,
        "vegan": False
    }])

    prediction = float(
        ml_model.predict(model_input)[0]
    )

    # Model labels were generated on a 1–5 scale.
    prediction = max(1.0, min(5.0, prediction))

    # Convert the predicted 1–5 score into 0–100.
    return round(prediction * 20, 2)


# ==========================================
# 4. ALLERGY FILTER
# ==========================================

def allergy_conflict(row, allergies):

    if not allergies:
        return False

    ingredients = clean_text(
        row.get("Ingredients", "")
    )

    # Unknown ingredients are conservatively excluded.
    if not ingredients:
        return True

    for allergy in allergies:

        if not allergy:
            continue

        pattern = r"\b" + re.escape(str(allergy)) + r"\b"

        if re.search(
            pattern,
            ingredients,
            re.IGNORECASE
        ):
            return True

    return False


# ==========================================
# 5. DIET FILTER
# ==========================================

def diet_conflict(row, diet):

    diet = str(diet).strip().lower()

    if diet in ["", "any", "none"]:
        return False

    ingredients = clean_text(
        row.get("Ingredients", "")
    )

    if not ingredients:
        return True

    non_veg_words = [
        "chicken", "mutton", "fish",
        "meat", "prawn", "shrimp"
    ]

    non_vegan_words = non_veg_words + [
        "milk", "cheese", "butter",
        "cream", "whey", "casein",
        "egg", "honey"
    ]

    if diet in ["veg", "vegetarian"]:
        words = non_veg_words

    elif diet == "vegan":
        words = non_vegan_words

    else:
        return False

    for word in words:

        pattern = r"\b" + re.escape(word) + r"\b"

        if re.search(
            pattern,
            ingredients,
            re.IGNORECASE
        ):
            return True

    return False


# ==========================================
# 6. HOME ROUTE
# ==========================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "FoodSage backend is running!",
        "dataset": "packaged_foods_india_clean.csv",
        "products_loaded": len(products),
        "ml_model_loaded": ml_model is not None
    })


# ==========================================
# 7. GET CATEGORIES
# ==========================================

@app.route("/categories", methods=["GET"])
def get_categories():

    categories = sorted(
        products["Category"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return jsonify({
        "categories": categories
    })


# ==========================================
# 8. GET PRODUCTS
# ==========================================

@app.route("/products", methods=["GET"])
def get_products():

    category = request.args.get(
        "category", ""
    ).strip()

    data = products.copy()

    if category:

        data = data[
            data["Category"].astype(str).str.strip().str.lower()
            == category.lower()
        ]

    result = []

    for index, row in data.iterrows():

        result.append({
            "product_id": str(index),
            "product_name": clean_text(row["Item name"]),
            "brand": clean_text(row["Brand_Name"]),
            "category": clean_text(row["Category"])
        })

    return jsonify({
        "products": result
    })


# ==========================================
# 9. ML-BASED RECOMMENDATIONS
# ==========================================

@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.get_json(silent=True) or {}

    category = str(
        data.get("category", "")
    ).strip()

    diet = data.get("diet", "any")

    priority = get_priority(data)

    allergies = data.get("allergies", [])

    if not category:

        return jsonify({
            "error": "Please select a category."
        }), 400

    if priority is None:

        return jsonify({
            "error": "Invalid nutrient priority."
        }), 400

    if not isinstance(allergies, list):

        return jsonify({
            "error": "Allergies must be provided as a list."
        }), 400

    filtered = products[
        products["Category"].astype(str).str.strip().str.lower()
        == category.lower()
    ].copy()

    # Dietary filtering
    if str(diet).lower() not in ["any", "none", ""]:

        filtered = filtered[
            ~filtered.apply(
                lambda row: diet_conflict(row, diet),
                axis=1
            )
        ]

    # Allergy filtering
    if allergies:

        filtered = filtered[
            ~filtered.apply(
                lambda row: allergy_conflict(row, allergies),
                axis=1
            )
        ]

    nutrient_column = NUTRIENTS[priority]

    # Require the selected nutrient.
    filtered = filtered.dropna(
        subset=[nutrient_column]
    ).copy()

    if filtered.empty:

        return jsonify({
            "recommendations": [],
            "message": "No matching products found with the available data."
        })

    # Generate predictions using the trained neural network.
    try:

        filtered["score"] = filtered.apply(
            lambda row: predict_ml_score(row, priority),
            axis=1
        )

    except Exception as error:

        app.logger.exception("ML prediction failed")

        return jsonify({
            "error": "ML recommendation failed. Check the model features.",
            "details": str(error)
        }), 500

    # Highest predicted score first.
    filtered = filtered.sort_values(
        by="score",
        ascending=False
    ).head(5)

    recommendations = []

    for index, row in filtered.iterrows():

        item = product_details(row, index)

        item["score"] = float(row["score"])

        item["explanation"] = (
            "Ranked using the trained FoodSage MLP model "
            "for the selected nutritional priority."
        )

        recommendations.append(item)

    return jsonify({
        "recommendations": recommendations,
        "message": "ML-based recommendations generated successfully."
    })


# ==========================================
# 10. HEALTHIER ALTERNATIVES
# ==========================================

@app.route("/alternatives", methods=["POST"])
def alternatives():

    data = request.get_json(silent=True) or {}

    product_id = str(
        data.get("product_id", "")
    ).strip()

    priority = get_priority(data)

    if priority is None:

        return jsonify({
            "error": "Invalid nutrient priority."
        }), 400

    try:

        selected_index = int(product_id)

        if selected_index < 0 or selected_index >= len(products):
            raise ValueError

        selected = products.iloc[selected_index]

    except (ValueError, IndexError):

        return jsonify({
            "error": "Selected product was not found."
        }), 404

    nutrient_column = NUTRIENTS[priority]

    if pd.isna(selected[nutrient_column]):

        return jsonify({
            "alternatives": [],
            "message": "Selected product has no recorded value for this nutrient."
        })

    if pd.isna(selected["Serving_Size_g"]):

        return jsonify({
            "alternatives": [],
            "message": "Selected product has no recorded serving size."
        })

    selected_category = clean_text(
        selected["Category"]
    )

    selected_value = float(
        selected[nutrient_column]
    )

    selected_serving = float(
        selected["Serving_Size_g"]
    )

    candidates = products[
        (
            products["Category"].astype(str).str.strip().str.lower()
            == selected_category.lower()
        )
        & products[nutrient_column].notna()
        & products["Serving_Size_g"].notna()
        & (products.index != selected_index)
    ].copy()

    candidates = candidates[
        candidates["Serving_Size_g"] == selected_serving
    ].copy()

    if priority in [
        "added_sugar",
        "sodium",
        "saturated_fat"
    ]:

        candidates = candidates[
            candidates[nutrient_column] < selected_value
        ].sort_values(
            by=nutrient_column,
            ascending=True
        )

        difference_label = "less"

    else:

        candidates = candidates[
            candidates[nutrient_column] > selected_value
        ].sort_values(
            by=nutrient_column,
            ascending=False
        )

        difference_label = "more"

    results = []

    for index, row in candidates.head(5).iterrows():

        item = product_details(row, index)

        alternative_value = float(
            row[nutrient_column]
        )

        item["selected_value"] = round(
            selected_value, 2
        )

        item["difference"] = round(
            abs(selected_value - alternative_value), 2
        )

        item["difference_label"] = difference_label

        item["nutrient"] = priority

        results.append(item)

    return jsonify({
        "selected_product": clean_text(selected["Item name"]),
        "alternatives": results,
        "message": (
            "Alternatives compared using matching recorded serving sizes."
            if results else
            "No better alternative with a matching serving size was found."
        )
    })


# ==========================================
# 11. RUN SERVER
# ==========================================

if __name__ == "__main__":

    print("\n========== FOODSAGE AI ==========")
    print("Dataset:", DATA_FILE)
    print("Products loaded:", len(products))
    print("ML model:", MODEL_FILE)
    print("Categories:", products["Category"].nunique())
    print("Backend starting...\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
