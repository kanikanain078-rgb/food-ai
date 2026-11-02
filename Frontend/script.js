
const API_URL = "http://127.0.0.1:5000/recommend";

// Get HTML elements
const categoryInput = document.getElementById("category");
const dietInput = document.getElementById("diet");
const priorityInput = document.getElementById("priority");
const allergiesInput = document.getElementById("allergies");
const recommendBtn = document.getElementById("recommendBtn");
const resultsContainer = document.getElementById("results");
const resultSummary = document.getElementById("resultSummary");

// Show a message in the results area
function showMessage(message) {
    resultsContainer.replaceChildren();

    const paragraph = document.createElement("p");
    paragraph.textContent = message;

    resultsContainer.appendChild(paragraph);
}

// Create a product recommendation card
function createProductCard(product, index) {
    const card = document.createElement("div");
    card.className = "product-card";

    const heading = document.createElement("h3");
    heading.textContent = `${index + 1}. ${product.product_name || product.name || "Unnamed product"}`;

    const brand = document.createElement("p");
    brand.textContent = `Brand: ${product.brand || "Not available"}`;

    const score = document.createElement("p");
    score.textContent = `Predicted preference score: ${
        Number(product.predicted_score ?? product.score ?? 0).toFixed(2)
    } / 5`;

    const nutritionHeading = document.createElement("h4");
    nutritionHeading.textContent = "Nutrition information";

    const nutrition = document.createElement("ul");

    const nutritionValues = [
        ["Added sugar", product.added_sugar_g, "g"],
        ["Fibre", product.fiber_g, "g"],
        ["Protein", product.protein_g, "g"],
        ["Sodium", product.sodium_mg, "mg"],
        ["Saturated fat", product.saturated_fat_g, "g"]
    ];

    nutritionValues.forEach(([label, value, unit]) => {
        const item = document.createElement("li");
        item.textContent =
            `${label}: ${value ?? "Not available"} ${value != null ? unit : ""}`;
        nutrition.appendChild(item);
    });

    const ingredients = document.createElement("p");
    ingredients.textContent =
        `Ingredients: ${product.ingredients || "Not available"}`;

    const allergens = document.createElement("p");
    allergens.textContent =
        `Declared allergens: ${product.allergens || "Not available"}`;

    const explanation = document.createElement("p");
    explanation.textContent =
        product.explanation || "No explanation available.";

    card.append(
        heading,
        brand,
        score,
        nutritionHeading,
        nutrition,
        ingredients,
        allergens,
        explanation
    );

    return card;
}

// Get recommendations from Flask
async function getRecommendations() {
    recommendBtn.disabled = true;
    recommendBtn.textContent = "Finding recommendations...";

    resultSummary.textContent = "Please wait while we compare products.";
    showMessage("Loading recommendations...");

    const allergies = allergiesInput.value
        .split(",")
        .map(item => item.trim())
        .filter(item => item.length > 0);

    const requestData = {
        category: categoryInput.value,
        diet: dietInput.value,
        priority: priorityInput.value,
        allergies: allergies
    };

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }

        const recommendations = Array.isArray(data)
            ? data
            : data.recommendations || [];

        resultsContainer.replaceChildren();

        if (recommendations.length === 0) {
            resultSummary.textContent = "No matching products found.";
            showMessage(
                "No products match these preferences. Try another category or change your filters."
            );
            return;
        }

        resultSummary.textContent =
            `Found ${recommendations.length} matching product(s).`;

        recommendations.forEach((product, index) => {
            const card = createProductCard(product, index);
            resultsContainer.appendChild(card);
        });

    } catch (error) {
        console.error("FoodSage error:", error);

        resultSummary.textContent = "Unable to get recommendations.";

        showMessage(
            "Could not connect to the FoodSage backend. Check that Flask is running at http://127.0.0.1:5000 and try again."
        );

    } finally {
        recommendBtn.disabled = false;
        recommendBtn.textContent = "Find my best food options";
    }
}

// Button click event
recommendBtn.addEventListener("click", getRecommendations);
