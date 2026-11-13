# food-ai

## Key Features

FoodSage AI provides personalized packaged food recommendations based on users' dietary preferences, ingredient exclusions, nutritional priorities, and budget.

### 1. Allergy-Based Ingredient Filtering
- Detects user-selected allergens and ingredients to avoid.
- Supports filtering for ingredients such as nuts, pistachios (pista), milk, soy, and other specified allergens.
- Excludes products when matching ingredient terms are detected.

### 2. Dietary Restrictions
- Supports vegetarian and vegan dietary preferences.
- Filters products based on declared ingredient information.
- Applies dietary filtering to both recommendations and product alternatives.

### 3. Budget-Based Recommendations
- Allows users to specify an optional maximum budget.
- Filters recommended products according to the selected budget.
- Displays product prices in recommendation results.

### 4. Budget-Based Alternatives
- Provides alternative product suggestions within the user's specified budget.
- Combines budget filtering with nutritional comparisons.

### 5. Missing Price Handling
- Does not generate or assign fabricated product prices.
- Excludes products with unavailable prices when a budget filter is applied.
- Preserves accurate price information where available.

### 6. Product Price Display
- Retrieves product prices from the available dataset.
- Includes product price information in backend responses for frontend display.

### 7. AI-Based Food Recommendations
- Uses a trained Multi-Layer Perceptron (MLP) neural network.
- Predicts preference scores for eligible products.
- Ranks products based on predicted scores and selected nutritional priorities.

### 8. Nutritional Comparison
- Supports comparisons based on added sugar, dietary fibre, protein, sodium, and saturated fat.
- Suggests alternative products based on the selected nutritional priority.
