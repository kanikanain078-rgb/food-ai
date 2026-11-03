
import pandas as pd

# ==========================================
# FOODSAGE - FOOD RECOMMENDATION SYSTEM
# ==========================================

FILE_NAME = "packaged_foods_india_clean.csv"

df = pd.read_csv(FILE_NAME)


# ==========================================
# 1. PREPARE DATASET
# ==========================================

def prepare_data(data):

    data = data.copy()

    numeric_columns = [
        "Serving_Size_g",
        "Sugar_g",
        "Sodium_mg",
        "Saturated_Fat_g",
        "Proteins_g",
        "Dietary_Fiber_g",
        "Trans_Fat_g"
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    # Use only verified rows if quality status exists
    if "Data_Quality_Status" in data.columns:
        data = data[
            data["Data_Quality_Status"] == "Valid"
        ].copy()

    # Serving size must be positive
    data = data[
        data["Serving_Size_g"].notna()
        & (data["Serving_Size_g"] > 0)
    ].copy()

    # Convert nutrition values to per 100g only
    # This assumes source values are per stated serving.
    nutrition_columns = [
        "Sugar_g",
        "Sodium_mg",
        "Saturated_Fat_g",
        "Proteins_g",
        "Dietary_Fiber_g",
        "Trans_Fat_g"
    ]

    for column in nutrition_columns:

        data[column + "_100g"] = (
            data[column] * 100 / data["Serving_Size_g"]
        )

    return data


# ==========================================
# 2. CALCULATE PRODUCT SCORE
# ==========================================

def calculate_score(row, goal):

    score = 0
    reasons = []

    # Sugar: maximum 25
    sugar = row["Sugar_g_100g"]

    if sugar <= 5:
        score += 25
        reasons.append("Lower sugar")
    elif sugar <= 10:
        score += 18
        reasons.append("Moderate-low sugar")
    elif sugar <= 20:
        score += 10
        reasons.append("Moderate sugar")
    else:
        score += 3
        reasons.append("Higher sugar")

    # Sodium: maximum 20
    sodium = row["Sodium_mg_100g"]

    if sodium <= 120:
        score += 20
        reasons.append("Lower sodium")
    elif sodium <= 400:
        score += 14
    elif sodium <= 600:
        score += 7
    else:
        score += 2

    # Saturated fat: maximum 20
    saturated_fat = row["Saturated_Fat_g_100g"]

    if saturated_fat <= 1.5:
        score += 20
        reasons.append("Lower saturated fat")
    elif saturated_fat <= 5:
        score += 14
    elif saturated_fat <= 10:
        score += 7
    else:
        score += 2

    # Protein: maximum 15
    protein = row["Proteins_g_100g"]

    if protein >= 10:
        score += 15
        reasons.append("Higher protein")
    elif protein >= 5:
        score += 9
    else:
        score += 3

    # Fibre: maximum 10
    fibre = row["Dietary_Fiber_g_100g"]

    if fibre >= 6:
        score += 10
        reasons.append("Higher fibre")
    elif fibre >= 3:
        score += 6
    else:
        score += 2

    # Trans fat: maximum 10
    trans_fat = row["Trans_Fat_g_100g"]

    if trans_fat == 0:
        score += 10
        reasons.append("Recorded trans fat is zero")
    elif trans_fat <= 0.5:
        score += 5
    else:
        reasons.append("Trans fat recorded above zero")

    # Goal adjustment
    if goal == "lower sugar" and sugar > 15:
        score -= 5

    elif goal == "higher protein" and protein < 10:
        score -= 5

    return max(0, min(score, 100)), reasons


# ==========================================
# 3. RECOMMEND PRODUCTS
# ==========================================

def recommend_food(category, preference, goal):

    data = prepare_data(df)

    # Category filter
    if category.lower() != "all":

        data = data[
            data["Category"].str.lower()
            == category.lower()
        ]

    # Basic vegetarian keyword filter
    if preference.lower() in ["veg", "vegetarian"]:

        non_veg_words = [
            "chicken", "mutton", "fish",
            "meat", "egg", "prawn", "shrimp"
        ]

        data = data[
            ~data["Ingredients"].str.lower().str.contains(
                "|".join(non_veg_words),
                na=False
            )
        ]

    # Require all nutrition values used in scoring
    required = [
        "Sugar_g_100g",
        "Sodium_mg_100g",
        "Saturated_Fat_g_100g",
        "Proteins_g_100g",
        "Dietary_Fiber_g_100g",
        "Trans_Fat_g_100g"
    ]

    data = data.dropna(subset=required)

    results = []

    for _, row in data.iterrows():

        score, reasons = calculate_score(
            row, goal.lower()
        )

        results.append({

            "Product": row["Item name"],
            "Brand": row["Brand_Name"],
            "Category": row["Category"],
            "Serving Size (g)": row["Serving_Size_g"],
            "Sugar/100g": round(row["Sugar_g_100g"], 2),
            "Protein/100g": round(row["Proteins_g_100g"], 2),
            "Sodium/100g (mg)": round(row["Sodium_mg_100g"], 2),
            "Score": score,
            "Reason": ", ".join(reasons)

        })

    result = pd.DataFrame(results)

    if result.empty:
        return result

    result = result.sort_values(
        by="Score",
        ascending=False
    )

    return result.head(5)


# ==========================================
# 4. MAIN PROGRAM
# ==========================================

if __name__ == "__main__":

    print("\n========== FOODSAGE ==========")

    category = input(
        "Enter category (BISCUIT / CHOCOLATE / ALL): "
    ).strip()

    preference = input(
        "Enter preference (veg / any): "
    ).strip()

    goal = input(
        "Enter goal (lower sugar / higher protein / balanced): "
    ).strip().lower()

    valid_goals = [
        "lower sugar",
        "higher protein",
        "balanced"
    ]

    if goal not in valid_goals:

        print("\nInvalid goal entered.")

    else:

        result = recommend_food(
            category,
            preference,
            goal
        )

        if result.empty:

            print("\nNo matching products found.")

        else:

            print("\n===== TOP 5 FOOD COMPARISONS =====\n")

            print(
                result.to_string(index=False)
            )

            print(
                "\nScores are provisional project comparison scores."
            )

            print(
                "They are not medical or official health ratings."
            )
