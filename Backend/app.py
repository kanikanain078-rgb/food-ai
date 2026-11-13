
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import re
import joblib
import math

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. LOAD DATASET AND MODEL
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "packaged_foods_india_clean.csv")
MODEL_FILE = os.path.join(BASE_DIR, "foodsage_model.joblib")

products = pd.read_csv(DATA_FILE, encoding="utf-8-sig")

if "Data_Quality_Status" in products.columns:
    products = products[
        products["Data_Quality_Status"].astype(str).str.strip().str.lower()
        == "valid"
    ].copy()

products.reset_index(drop=True, inplace=True)

ml_model = joblib.load(MODEL_FILE)

print("ML model loaded successfully!")
print("Products loaded:", len(products))


# ==========================================
# 2. COLUMN CONFIGURATION
# ==========================================

NUTRIENTS = {
    "added_sugar": "Sugar_g",
    "fiber": "Dietary_Fiber_g",
    "protein": "Proteins_g",
    "sodium": "Sodium_mg",
    "saturated_fat": "Saturated_Fat_g"
}

for column in NUTRIENTS.values():
    if column not in products.columns:
        raise ValueError(f"Missing required dataset column: {column}")

products["Serving_Size_g"] = pd.to_numeric(
    products["Serving_Size_g"], errors="coerce"
)

for column in NUTRIENTS.values():
    products[column] = pd.to_numeric(
        products[column], errors="coerce"
    )

# Convert prices into numbers.
# Missing prices remain NaN and are not filled with guessed values.

if "Price_INR" not in products.columns:
    raise ValueError("Missing required dataset column: Price_INR")

products["Price_INR"] = pd.to_numeric(
    products["Price_INR"], errors="coerce"
)


# ==========================================
# 3. HELPER FUNCTIONS
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


def get_preferences(data):

    diet = str(data.get("diet", "any")).strip().lower()

    if diet in ["", "none", "any"]:
        diet = "any"

    if diet == "veg":
        diet = "vegetarian"

    allergies = data.get("allergies", [])

    if isinstance(allergies, str):
        allergies = allergies.split(",")

    if not isinstance(allergies, list):
        return None, None

    allergies = [
        str(item).strip().lower()
        for item in allergies
        if str(item).strip()
    ]

    if diet not in ["any", "vegetarian", "vegan"]:
        return None, None

    return diet, allergies


# BUDGET HELPER FUNCTION

def get_budget(data):

    value = data.get("max_price")

    # Empty budget means no price restriction.
    if value is None or str(value).strip() == "":
        return None

    try:
        budget = float(value)

        if not math.isfinite(budget) or budget < 0:
            return "invalid"

        return budget

    except (ValueError, TypeError):
        return "invalid"


def product_details(row, product_id):

    return {
        "product_id": str(product_id),
        "product_name": clean_text(row.get("Item name", "")),
        "brand": clean_text(row.get("Brand_Name", "")),
        "category": clean_text(row.get("Category", "")),

        # PRODUCT PRICE
        "price_inr": (
            round(float(row["Price_INR"]), 2)
            if pd.notna(row["Price_INR"]) else None
        ),

        "serving_size": (
            round(float(row["Serving_Size_g"]), 2)
            if pd.notna(row["Serving_Size_g"]) else None
        ),

        "added_sugar": (
            round(float(row["Sugar_g"]), 2)
            if pd.notna(row["Sugar_g"]) else None
        ),

        "fiber": (
            round(float(row["Dietary_Fiber_g"]), 2)
            if pd.notna(row["Dietary_Fiber_g"]) else None
        ),

        "protein": (
            round(float(row["Proteins_g"]), 2)
            if pd.notna(row["Proteins_g"]) else None
        ),

        "sodium": (
            round(float(row["Sodium_mg"]), 2)
            if pd.notna(row["Sodium_mg"]) else None
        ),

        "saturated_fat": (
            round(float(row["Saturated_Fat_g"]), 2)
            if pd.notna(row["Saturated_Fat_g"]) else None
        )
    }


# ==========================================
# 4. INGREDIENT AND ALLERGEN TEXT
# ==========================================

INGREDIENT_COLUMNS = [
    "Ingredients",
    "Allergens",
    "Allergen_Information",
    "Allergen_Statement",
    "May_Contain",
    "May_Contain_Statement",
    "Precautionary_Statement",
    "Allergen_Declaration"
]


def get_ingredient_text(row):

    text_parts = []

    for column in INGREDIENT_COLUMNS:

        if column in row.index:

            value = clean_text(row[column])

            if value:
                text_parts.append(value)

    return " ".join(text_parts)


def get_allergy_text(row):

    product_name = clean_text(row.get("Item name", ""))

    ingredient_text = get_ingredient_text(row)

    return product_name + " " + ingredient_text


def contains_term(text, term):

    pattern = r"\b" + re.escape(term) + r"\b"

    return bool(
        re.search(pattern, text, re.IGNORECASE)
    )


# ==========================================
# 5. ALLERGY GROUPS
# ==========================================

ALLERGY_GROUPS = {

    "peanut": [
        "peanut", "peanuts",
        "groundnut", "groundnuts"
    ],

    "milk": [
        "milk", "milk powder", "milk solids",
        "skimmed milk", "whey", "casein",
        "lactose", "butter", "cream", "cheese"
    ],

    "soy": [
        "soy", "soya", "soybean", "soybeans"
    ],

    "gluten": [
        "gluten", "wheat", "barley", "rye"
    ],

    "wheat": [
        "wheat", "wheat flour", "wheat starch"
    ],

    "egg": [
        "egg", "eggs", "egg white",
        "egg yolk", "albumin"
    ],

    "tree nuts": [
        "almond", "almonds",
        "cashew", "cashews",
        "walnut", "walnuts",
        "pista", "pistas",
        "pistachio", "pistachios",
        "hazelnut", "hazelnuts",
        "pecan", "pecans",
        "macadamia"
    ],

    "nuts": [
        "nut", "nuts",
        "peanut", "peanuts",
        "groundnut", "groundnuts",
        "almond", "almonds",
        "cashew", "cashews",
        "walnut", "walnuts",
        "pista", "pistas",
        "pistachio", "pistachios",
        "hazelnut", "hazelnuts",
        "pecan", "pecans",
        "macadamia"
    ],

    "sesame": [
        "sesame", "sesame seeds", "til"
    ],

    "fish": [
        "fish", "anchovy", "anchovies",
        "fish oil", "fish sauce"
    ],

    "shellfish": [
        "prawn", "prawns", "shrimp",
        "crab", "lobster", "crustacean"
    ]
}


# ==========================================
# 6. ALLERGY CHECK
# ==========================================

def allergy_conflict(row, allergies):

    if not allergies:
        return False

    ingredient_text = get_ingredient_text(row)

    # Missing ingredient information:
    # conservatively exclude when an allergy is selected.
    if not ingredient_text:
        return True

    searchable_text = get_allergy_text(row)

    for allergy in allergies:

        terms = ALLERGY_GROUPS.get(
            allergy, [allergy]
        )

        for term in terms:

            if contains_term(searchable_text, term):
                return True

    return False


# ==========================================
# 7. DIET CHECK
# ==========================================

VEGETARIAN_CONFLICTS = [
    "chicken", "mutton", "fish", "meat",
    "beef", "pork", "prawn", "prawns",
    "shrimp", "crab", "lobster",
    "fish sauce", "oyster sauce",
    "anchovy", "gelatin", "gelatine",
    "lard", "tallow", "animal rennet"
]

VEGAN_CONFLICTS = VEGETARIAN_CONFLICTS + [
    "milk", "milk powder", "milk solids",
    "skimmed milk", "cheese", "butter",
    "ghee", "cream", "whey", "casein",
    "lactose", "egg", "eggs",
    "egg white", "egg yolk",
    "honey", "curd", "yogurt", "paneer"
]


def diet_conflict(row, diet):

    if diet == "any":
        return False

    ingredient_text = get_ingredient_text(row)

    if not ingredient_text:
        return True

    searchable_text = get_allergy_text(row)

    if diet == "vegetarian":
        conflicts = VEGETARIAN_CONFLICTS

    elif diet == "vegan":
        conflicts = VEGAN_CONFLICTS

    else:
        return False

    for word in conflicts:

        if contains_term(searchable_text, word):
            return True

    return False


# ==========================================
# 8. APPLY ALL RESTRICTIONS
# ==========================================

def apply_restrictions(data, diet, allergies):

    if diet != "any":

        data = data[
            ~data.apply(
                lambda row: diet_conflict(row, diet),
                axis=1
            )
        ]

    if allergies:

        data = data[
            ~data.apply(
                lambda row: allergy_conflict(row, allergies),
                axis=1
            )
        ]

    return data.copy()


# ==========================================
# 9. ML MODEL PREDICTION
# ==========================================

def predict_ml_score(row, priority):

    model_input = pd.DataFrame([{

        "added_sugar_g": row["Sugar_g"],
        "fiber_g": row["Dietary_Fiber_g"],
        "protein_g": row["Proteins_g"],
        "sodium_mg": row["Sodium_mg"],
        "saturated_fat_g": row["Saturated_Fat_g"],

        "category": clean_text(row["Category"]).lower(),

        # Match the values used during model training.
        "diet": "vegetarian",
        "priority": priority,
        "vegetarian": True,
        "vegan": False

    }])

    prediction = float(
        ml_model.predict(model_input)[0]
    )

    prediction = max(1.0, min(5.0, prediction))

    return round(prediction * 20, 2)


# ==========================================
# 10. HOME ROUTE
# ==========================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "FoodSage backend is running!",
        "products_loaded": len(products),
        "ml_model_loaded": ml_model is not None,
        "categories": products["Category"].nunique()
    })


# ==========================================
# 11. CATEGORIES ROUTE
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
# 12. PRODUCTS ROUTE
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

            "product_name": clean_text(
                row.get("Item name", "")
            ),

            "brand": clean_text(
                row.get("Brand_Name", "")
            ),

            "category": clean_text(
                row.get("Category", "")
            ),

            "price_inr": (
                round(float(row["Price_INR"]), 2)
                if pd.notna(row["Price_INR"]) else None
            )

        })

    return jsonify({
        "products": result
    })


# ==========================================
# 13. RECOMMENDATION ROUTE
# ==========================================

@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.get_json(silent=True) or {}

    category = str(
        data.get("category", "")
    ).strip()

    priority = get_priority(data)

    diet, allergies = get_preferences(data)

    budget = get_budget(data)

    if not category:

        return jsonify({
            "error": "Please select a category."
        }), 400

    if priority is None:

        return jsonify({
            "error": "Invalid nutrient priority."
        }), 400

    if diet is None:

        return jsonify({
            "error": "Invalid dietary preference."
        }), 400

    if allergies is None:

        return jsonify({
            "error": "Allergies must be provided as a list."
        }), 400

    if budget == "invalid":

        return jsonify({
            "error": "Please enter a valid non-negative budget."
        }), 400

    filtered = products[
        products["Category"].astype(str).str.strip().str.lower()
        == category.lower()
    ].copy()

    print("\n========== RECOMMENDATION REQUEST ==========")
    print("Diet:", diet)
    print("Allergies:", allergies)
    print("Priority:", priority)
    print("Maximum budget:", budget)
    print("Products before filters:", len(filtered))

    filtered = apply_restrictions(
        filtered, diet, allergies
    )

    print("Products after diet/allergy filters:", len(filtered))

    # APPLY BUDGET FILTER
    # Products with missing prices are excluded only
    # when the user has entered a budget.

    if budget is not None:

        filtered = filtered[
            filtered["Price_INR"].notna()
            & (filtered["Price_INR"] <= budget)
        ].copy()

        print("Products after budget filter:", len(filtered))

    nutrient_column = NUTRIENTS[priority]

    filtered = filtered.dropna(
        subset=[nutrient_column]
    ).copy()

    if filtered.empty:

        return jsonify({

            "recommendations": [],

            "message": (
                "No matching products found with the selected "
                "dietary, allergy and budget restrictions."
            ),

            "filters_applied": {
                "diet": diet,
                "allergies": allergies,
                "priority": priority,
                "max_price": budget
            }

        })

    try:

        filtered["score"] = filtered.apply(
            lambda row: predict_ml_score(row, priority),
            axis=1
        )

    except Exception as error:

        app.logger.exception(
            "ML prediction failed"
        )

        return jsonify({
            "error": "ML recommendation failed.",
            "details": str(error)
        }), 500

    filtered = filtered.sort_values(
        by="score",
        ascending=False
    ).head(5)

    recommendations = []

    for rank, (index, row) in enumerate(
        filtered.iterrows(), start=1
    ):

        item = product_details(row, index)

        item["score"] = float(row["score"])
        item["rank"] = rank

        item["explanation"] = (
            "Ranked using the trained FoodSage MLP model "
            "for the selected nutritional priority."
        )

        recommendations.append(item)

    return jsonify({

        "recommendations": recommendations,

        "message": "Recommendations generated successfully.",

        "filters_applied": {
            "diet": diet,
            "allergies": allergies,
            "priority": priority,
            "max_price": budget
        }

    })


# ==========================================
# 14. ALTERNATIVES ROUTE
# ==========================================

@app.route("/alternatives", methods=["POST"])
def alternatives():

    data = request.get_json(silent=True) or {}

    product_id = str(
        data.get("product_id", "")
    ).strip()

    priority = get_priority(data)

    diet, allergies = get_preferences(data)

    budget = get_budget(data)

    if priority is None:

        return jsonify({
            "error": "Invalid nutrient priority."
        }), 400

    if diet is None:

        return jsonify({
            "error": "Invalid dietary preference."
        }), 400

    if allergies is None:

        return jsonify({
            "error": "Allergies must be provided as a list."
        }), 400

    if budget == "invalid":

        return jsonify({
            "error": "Please enter a valid non-negative budget."
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

    print("\n========== ALTERNATIVES REQUEST ==========")
    print("Selected product:", clean_text(selected.get("Item name", "")))
    print("Diet:", diet)
    print("Allergies:", allergies)
    print("Priority:", priority)
    print("Maximum alternative budget:", budget)

    # CHECK THE SELECTED PRODUCT FIRST.

    if diet_conflict(selected, diet):

        return jsonify({

            "alternatives": [],

            "message": (
                "The selected product does not match your dietary "
                "preference. Please select another product."
            ),

            "filters_applied": {
                "diet": diet,
                "allergies": allergies,
                "priority": priority,
                "max_price": budget
            }

        })

    if allergy_conflict(selected, allergies):

        return jsonify({

            "alternatives": [],

            "message": (
                "The selected product may contain an allergen "
                "you entered. Please select another product."
            ),

            "filters_applied": {
                "diet": diet,
                "allergies": allergies,
                "priority": priority,
                "max_price": budget
            }

        })

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

    # FIND PRODUCTS IN THE SAME CATEGORY.

    candidates = products[

        (
            products["Category"].astype(str).str.strip().str.lower()
            == selected_category.lower()
        )

        & products[nutrient_column].notna()

        & products["Serving_Size_g"].notna()

        & (products.index != selected_index)

    ].copy()

    # SAME SERVING SIZE.

    candidates = candidates[
        (candidates["Serving_Size_g"] - selected_serving).abs() < 0.01
    ].copy()

    print("Candidates before restrictions:", len(candidates))

    # APPLY THE SAME DIET AND ALLERGY FILTERS.

    candidates = apply_restrictions(
        candidates, diet, allergies
    )

    print("Candidates after restrictions:", len(candidates))

    # APPLY ALTERNATIVE BUDGET FILTER.
    # The budget applies to replacement products,
    # not to the originally selected product.

    if budget is not None:

        candidates = candidates[
            candidates["Price_INR"].notna()
            & (candidates["Price_INR"] <= budget)
        ].copy()

        print("Candidates after budget filter:", len(candidates))

    # FIND BETTER NUTRIENT VALUES.

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

        "selected_product": clean_text(
            selected.get("Item name", "")
        ),

        "alternatives": results,

        "message": (
            "Alternatives generated with your dietary, allergy "
            "and budget preferences applied."
            if results else
            "No better alternatives matching your selected restrictions, "
            "budget and serving size were found."
        ),

        "filters_applied": {
            "diet": diet,
            "allergies": allergies,
            "priority": priority,
            "max_price": budget
        }

    })


# ==========================================
# 15. RUN FLASK SERVER
# ==========================================

if __name__ == "__main__":

    print("\n========== FOODSAGE AI ==========")
    print("Products:", len(products))
    print("Categories:", products["Category"].nunique())
    print("Products with recorded prices:", products["Price_INR"].notna().sum())
    print("Products with missing prices:", products["Price_INR"].isna().sum())
    print("ML model loaded successfully!")
    print("Starting backend...\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
