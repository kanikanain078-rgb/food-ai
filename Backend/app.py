
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import re

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. LOAD REAL DATASET
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(
    BASE_DIR,
    "packaged_foods_india_clean.csv"
)

products = pd.read_csv(
    DATA_FILE,
    encoding="utf-8-sig"
)

# Keep only verified records
if "Data_Quality_Status" in products.columns:
    products = products[
        products["Data_Quality_Status"] == "Valid"
    ].copy()

# Reset index so product IDs remain consistent
products = products.reset_index(drop=True)

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

print("FoodSage dataset loaded:", len(products), "products")


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
    ).strip()

    # Support older frontend option values too
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


def calculate_score(row, priority):
    """
    Project-defined Priority Match Score.
    This is not an official health rating.
    """

    column = NUTRIENTS[priority]
    value = row[column]

    if pd.isna(value):
        return None

    value = float(value)

    if priority == "added_sugar":
        score = max(0, 100 - value * 2)

    elif priority == "sodium":
        score = max(0, 100 - value / 10)

    elif priority == "saturated_fat":
        score = max(0, 100 - value * 5)

    elif priority == "protein":
        score = min(100, value * 5)

    elif priority == "fiber":
        score = min(100, value * 10)

    return round(score, 1)


def allergy_conflict(row, allergies):
    """
    Conservative keyword check.
    Missing ingredient information is treated as unknown.
    """

    if not allergies:
        return False

    ingredients = clean_text(row.get("Ingredients", ""))

    if not ingredients:
        return True

    for allergy in allergies:
        if not allergy:
            continue

        pattern = r"\b" + re.escape(allergy) + r"\b"

        if re.search(pattern, ingredients, re.IGNORECASE):
            return True

    return False


def diet_conflict(row, diet):
    """
    Basic ingredient keyword filter.
    This is not a certified vegetarian/vegan classification.
    """

    diet = str(diet).strip().lower()

    if diet in ["", "any", "none"]:
        return False

    ingredients = clean_text(row.get("Ingredients", ""))

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

        if re.search(pattern, ingredients, re.IGNORECASE):
            return True

    return False


# ==========================================
# 3. HOME ROUTE
# ==========================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "FoodSage backend is running!",
        "dataset": "packaged_foods_india_clean.csv",
        "products_loaded": len(products)
    })


# ==========================================
# 4. GET CATEGORIES
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
# 5. GET PRODUCTS FOR DROPDOWN
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
# 6. RECOMMENDATION FEATURE
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

    # Diet filter
    if str(diet).lower() not in ["any", "none", ""]:
        filtered = filtered[
            ~filtered.apply(
                lambda row: diet_conflict(row, diet),
                axis=1
            )
        ]

    # Allergy filter
    if allergies:
        filtered = filtered[
            ~filtered.apply(
                lambda row: allergy_conflict(row, allergies),
                axis=1
            )
        ]

    nutrient_column = NUTRIENTS[priority]

    # Require selected nutrient
    filtered = filtered.dropna(
        subset=[nutrient_column]
    ).copy()

    if filtered.empty:
        return jsonify({
            "recommendations": [],
            "message": "No matching products found with the available data."
        })

    filtered["score"] = filtered.apply(
        lambda row: calculate_score(row, priority),
        axis=1
    )

    filtered = filtered.sort_values(
        by="score",
        ascending=False
    ).head(5)

    recommendations = []

    for index, row in filtered.iterrows():

        item = product_details(row, index)

        item["score"] = row["score"]

        item["explanation"] = (
            "Ranked using the selected nutrient. "
            "This is a project-defined comparison score."
        )

        recommendations.append(item)

    return jsonify({
        "recommendations": recommendations,
        "message": "Recommendations generated from the real dataset."
    })


# ==========================================
# 7. HEALTHIER ALTERNATIVE FEATURE
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

    # Compare only matching recorded serving sizes.
    candidates = candidates[
        candidates["Serving_Size_g"] == selected_serving
    ].copy()

    # Lower is preferred for these nutrients
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

    # Higher is preferred for these nutrients
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
# 8. RUN SERVER
# ==========================================

if __name__ == "__main__":

    print("\n========== FOODSAGE ==========")
    print("Dataset:", DATA_FILE)
    print("Products loaded:", len(products))
    print("Categories:", products["Category"].nunique())
    print("Backend starting...\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
