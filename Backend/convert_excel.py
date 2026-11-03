
import pandas as pd
from pathlib import Path

# ==========================================
# 1. FILE PATHS
# ==========================================

folder = Path(__file__).resolve().parent

input_file = folder / "packaged_foods_india (1).csv"
output_file = folder / "packaged_foods_india_clean.csv"
report_file = folder / "food_quality_report.csv"

# ==========================================
# 2. LOAD DATASET
# ==========================================

if not input_file.exists():
    raise FileNotFoundError(f"Dataset not found: {input_file}")

df = pd.read_csv(input_file, encoding="utf-8-sig")

print("Dataset loaded successfully!")
print("Original shape:", df.shape)

# ==========================================
# 3. CLEAN COLUMN NAMES
# ==========================================

df.columns = df.columns.str.strip()
df.columns = df.columns.str.replace("\ufeff", "", regex=False)

# ==========================================
# 4. REMOVE EMPTY ROWS AND COLUMNS
# ==========================================

df.dropna(how="all", inplace=True)
df.dropna(axis=1, how="all", inplace=True)

# ==========================================
# 5. REMOVE EXACT DUPLICATES
# ==========================================

duplicates = df.duplicated().sum()
df.drop_duplicates(inplace=True)

print("Duplicate rows removed:", duplicates)

# ==========================================
# 6. STANDARDIZE CATEGORIES
# ==========================================

if "Category" in df.columns:
    df["Category"] = (
        df["Category"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["Category"] = df["Category"].replace({
        "ICEREAMES": "ICE CREAM"
    })

# ==========================================
# 7. CLEAN DIETARY FIBRE AND CHOLESTEROL
# ==========================================

special_columns = [
    "Dietary_Fiber_g",
    "Cholesterol_mg"
]

for col in special_columns:
    if col in df.columns:

        original_values = df[col].astype("string").str.strip()

        df[col + "_upper_bound"] = (
            original_values.str.startswith("<", na=False)
        )

        extracted = original_values.str.extract(
            r"([-+]?\d*\.?\d+)",
            expand=False
        )

        df[col] = pd.to_numeric(extracted, errors="coerce")

# ==========================================
# 8. CONVERT NUMERIC COLUMNS
# ==========================================

numeric_columns = [
    "Serving_Size_g",
    "Calories_kcal",
    "Carbohydrates_g",
    "Proteins_g",
    "Total_Fat_g",
    "Saturated_Fat_g",
    "Trans_Fat_g",
    "Sugar_g",
    "Sodium_mg",
    "Calcium_mg",
    "Iron_mg",
    "Price_INR"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# ==========================================
# 9. REMOVE UNNECESSARY COLUMNS
# ==========================================

columns_to_remove = [
    "Source_of_Data",
    "Collection_Date",
    "Collected_By",
    "Remarks"
]

df.drop(columns=columns_to_remove, errors="ignore", inplace=True)

# ==========================================
# 10. DATA QUALITY VALIDATION
# ==========================================

macro_columns = [
    "Carbohydrates_g",
    "Proteins_g",
    "Total_Fat_g"
]

df["Macro_Total_g"] = df[macro_columns].sum(
    axis=1,
    min_count=3
)

df["Data_Quality_Status"] = "Valid"

# Missing macronutrients
missing = df[macro_columns].isnull().any(axis=1)

df.loc[missing, "Data_Quality_Status"] = "Needs Verification"

# Individual macro value above 100g
invalid = (
    df[macro_columns].gt(100).any(axis=1)
    & ~missing
)

df.loc[invalid, "Data_Quality_Status"] = "Invalid"

# Total macronutrients above 100g
high_total = (
    (df["Macro_Total_g"] > 100)
    & (df["Data_Quality_Status"] == "Valid")
)

df.loc[high_total, "Data_Quality_Status"] = "Needs Verification"

# ==========================================
# 11. CREATE QUALITY REPORT
# ==========================================

report_columns = [
    "Item name",
    "Serving_Size_g",
    "Carbohydrates_g",
    "Proteins_g",
    "Total_Fat_g",
    "Macro_Total_g",
    "Data_Quality_Status"
]

report = df[
    df["Data_Quality_Status"] != "Valid"
][report_columns].copy()

report.to_csv(
    report_file,
    index=False,
    encoding="utf-8-sig"
)

# ==========================================
# 12. SAVE FINAL CLEANED DATASET
# ==========================================

df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

# ==========================================
# 13. DISPLAY RESULTS
# ==========================================

print("\n===================================")
print(" FOODSAGE DATA CLEANING COMPLETE")
print("===================================")

print("\nFinal dataset shape:", df.shape)

print("\nData quality status:")
print(df["Data_Quality_Status"].value_counts())

print("\nMissing values:")
print(df.isnull().sum())

print("\nRemaining duplicates:", df.duplicated().sum())

print("\nCleaned dataset saved at:")
print(output_file)

print("\nQuality report saved at:")
print(report_file)

print("\nALL OPERATIONS COMPLETED!")
