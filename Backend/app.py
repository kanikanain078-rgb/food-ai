from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import os
import re

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load product dataset
products = pd.read_csv(
    os.path.join(BASE_DIR, "food_products.csv")
)

# Load trained MLP model
model = joblib.load(
    os.path.join(BASE_DIR, "foodsage_model.joblib")
)

NUMERIC_FEATURES = [
    "added_sugar_g",
    "fiber_g",
    "protein_g",
    "sodium_mg",
    "saturated_fat_g"
]


def to_bool(value):
    return str(value).strip().lower() == "true"


def allergy_conflict(product, allergies):

    if not allergies:
        return False

    # Unknown allergen information is excluded when
    # the user has entered an allergy.
    if not to_bool(product["allergen_info_known"]):
        return True

    product_text = (
        str(product["ingredients"]) + " " +
        str(product["allergens"])
    ).lower()

    for allergy in allergies:
        pattern = r"\b" + re.escape(allergy.lower()) + r"\b"

        if re.search(pattern, product_text):
            return True

    return False


@app.route("/")
def home():
    return jsonify({
        "message": "FoodSage AI backend is running!"
    })


@app.route("/recommend", methods=["POST"])
def recommend():

    try:
        user = request.get_json()

        if not user:
            return jsonify({
                "error": "Missing user preferences."
            }), 400

        category = str(
            user.get("category", "")
        ).strip().lower()

        diet = str(
            user.get("diet", "none")
        ).strip().lower()

        priority = str(
            user.get("priority", "")
        ).strip().lower()

        allergies = user.get("allergies", [])

        if not category:
            return jsonify({
                "error": "Please select a category."
            }), 400

        if diet not in ["none", "vegetarian", "vegan"]:
            return jsonify({
                "error": "Invalid dietary preference."
            }), 400

        if priority not in [
            "added_sugar",
            "fiber",
            "protein",
            "sodium",
            "saturated_fat"
        ]:
            return jsonify({
                "error": "Invalid nutrition priority."
            }), 400

        if not isinstance(allergies, list):
            return jsonify({
                "error": "Allergies must be a list."
            }), 400

        # Step 1: Filter category
        candidates = products[
            products["category"].str.lower() == category
        ].copy()

        # Step 2: Apply dietary filter
        if diet == "vegetarian":
            candidates = candidates[
                candidates["vegetarian"].apply(to_bool)
            ]

        elif diet == "vegan":
            candidates = candidates[
                candidates["vegan"].apply(to_bool)
            ]

        # Step 3: Apply declared allergen information filter
        candidates = candidates[
            ~candidates.apply(
                lambda p: allergy_conflict(p, allergies),
                axis=1
            )
        ].copy()

        if candidates.empty:
            return jsonify({
                "message": "No matching products found.",
                "recommendations": []
            })

        # Step 4: Check nutrition values
        for column in NUMERIC_FEATURES:
            candidates[column] = pd.to_numeric(
                candidates[column],
                errors="coerce"
            )

        # Exclude products with incomplete nutrition data
        candidates = candidates.dropna(
            subset=NUMERIC_FEATURES
        ).copy()

        if candidates.empty:
            return jsonify({
                "message": "No products have complete nutrition data.",
                "recommendations": []
            })

        # Step 5: Prepare model inputs
        candidates["vegetarian"] = (
            candidates["vegetarian"].apply(to_bool)
        )

        candidates["vegan"] = (
            candidates["vegan"].apply(to_bool)
        )

        candidates["category"] = category
        candidates["diet"] = diet
        candidates["priority"] = priority

        feature_columns = [
            "added_sugar_g",
            "fiber_g",
            "protein_g",
            "sodium_mg",
            "saturated_fat_g",
            "category",
            "diet",
            "priority",
            "vegetarian",
            "vegan"
        ]

        X = candidates[feature_columns]

        # Step 6: Predict ratings using MLP
        predictions = model.predict(X)

        candidates["predicted_score"] = predictions.clip(1, 5)

        # Step 7: Rank products
        candidates = candidates.sort_values(
            by="predicted_score",
            ascending=False
        )

        # Step 8: Prepare results
        results = []

        for _, p in candidates.iterrows():

            priority_values = {
                "added_sugar": f'{p["added_sugar_g"]} g added sugar per 100g',
                "fiber": f'{p["fiber_g"]} g fibre per 100g',
                "protein": f'{p["protein_g"]} g protein per 100g',
                "sodium": f'{p["sodium_mg"]} mg sodium per 100g',
                "saturated_fat": f'{p["saturated_fat_g"]} g saturated fat per 100g'
            }

            explanation = (
                f'The MLP predicted a preference rating of '
                f'{p["predicted_score"]:.2f} out of 5. '
                f'The product passed the selected dietary filter. '
                f'Its declared ingredient information contains no '
                f'matching entered allergy term. '
                f'It contains {priority_values[priority]}. '
                f'Please verify the actual package label.'
            )

            results.append({
                "name": str(p["product_name"]),
                "brand": str(p["brand"]),
                "addedSugar": float(p["added_sugar_g"]),
                "fiber": float(p["fiber_g"]),
                "protein": float(p["protein_g"]),
                "sodium": float(p["sodium_mg"]),
                "saturatedFat": float(p["saturated_fat_g"]),
                "ingredients": str(p["ingredients"]),
                "allergens": str(p["allergens"]),
                "score": round(
                    float(p["predicted_score"]), 2
                ),
                "explanation": explanation
            })

        return jsonify({
            "message": "Recommendations generated successfully.",
            "recommendations": results
        })

    except Exception:
        app.logger.exception("Recommendation error")

        return jsonify({
            "error": "Unable to generate recommendations."
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )