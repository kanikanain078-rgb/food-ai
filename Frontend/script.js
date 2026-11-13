
const API_URL = "http://127.0.0.1:5000";

const recommendBtn = document.getElementById("recommendBtn");
const results = document.getElementById("results");
const resultSummary = document.getElementById("resultSummary");

const alternativeBtn = document.getElementById("alternativeBtn");
const alternativeResults = document.getElementById("alternativeResults");
const alternativeSummary = document.getElementById("alternativeSummary");

const categorySelect = document.getElementById("category");
const baseProductSelect = document.getElementById("baseProduct");

const nutrientInfo = {
    added_sugar: { label: "Added Sugar", unit: "g" },
    fiber: { label: "Fibre", unit: "g" },
    protein: { label: "Protein", unit: "g" },
    sodium: { label: "Sodium", unit: "mg" },
    saturated_fat: { label: "Saturated Fat", unit: "g" }
};


// ==========================================
// 1. PRIORITY NORMALIZATION
// ==========================================

function normalizePriority(value) {

    const mapping = {
        added_sugar_g: "added_sugar",
        fiber_g: "fiber",
        protein_g: "protein",
        sodium_mg: "sodium",
        saturated_fat_g: "saturated_fat"
    };

    return mapping[value] || value;
}


// ==========================================
// 2. GET USER PREFERENCES
// ==========================================

function getUserPreferences() {

    const diet = document.getElementById("diet").value;

    const allergyText =
        document.getElementById("allergies").value;

    const allergies = allergyText
        .split(",")
        .map(item => item.trim().toLowerCase())
        .filter(item => item !== "");

    return {
        diet: diet,
        allergies: allergies
    };
}


// ==========================================
// 3. GET AND VALIDATE BUDGET
// ==========================================

function getBudget(inputId) {

    const value = document.getElementById(inputId).value.trim();

    // Empty budget means no price restriction.
    if (value === "") {
        return null;
    }

    const budget = Number(value);

    if (!Number.isFinite(budget) || budget < 0) {
        alert("Please enter a valid budget of ₹0 or more.");
        return undefined;
    }

    return budget;
}


// ==========================================
// 4. APPLIED FILTER SUMMARY
// ==========================================

function showAppliedFilters(preferences, priority, budget) {

    const dietLabel =
        preferences.diet || "Any diet";

    const allergyLabel =
        preferences.allergies.length > 0
            ? preferences.allergies.join(", ")
            : "None";

    const priorityLabel =
        nutrientInfo[priority]?.label || priority;

    const budgetLabel =
        budget === null ? "No limit" : `₹${budget}`;

    return `Diet: ${dietLabel} | Allergies: ${allergyLabel} | Priority: ${priorityLabel} | Budget: ${budgetLabel}`;
}


// ==========================================
// 5. FORMAT PRICE
// ==========================================

function formatPrice(product) {

    const price =
        product.price_inr ?? product.Price_INR ?? product.price;

    if (price === null || price === undefined || price === "") {
        return "Price: Not available";
    }

    const numericPrice = Number(price);

    if (!Number.isFinite(numericPrice)) {
        return "Price: Not available";
    }

    return `Price: ₹${numericPrice.toFixed(2)}`;
}


// ==========================================
// 6. LOAD CATEGORIES
// ==========================================

async function loadCategories() {

    try {

        const response = await fetch(`${API_URL}/categories`);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load categories.");
        }

        categorySelect.innerHTML =
            '<option value="">Choose a category</option>';

        data.categories.forEach(category => {

            const option = document.createElement("option");

            option.value = category;
            option.textContent = category;

            categorySelect.appendChild(option);

        });

    } catch (error) {

        console.error("Category loading error:", error);

    }
}


// ==========================================
// 7. LOAD PRODUCTS
// ==========================================

async function loadProducts() {

    try {

        const category = categorySelect.value;

        baseProductSelect.innerHTML =
            '<option value="">Loading products...</option>';

        const url = category
            ? `${API_URL}/products?category=${encodeURIComponent(category)}`
            : `${API_URL}/products`;

        const response = await fetch(url);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load products.");
        }

        baseProductSelect.innerHTML =
            '<option value="">Choose a product</option>';

        data.products.forEach(product => {

            const option = document.createElement("option");

            option.value = product.product_id;

            option.textContent =
                `${product.product_name} (${product.brand})`;

            baseProductSelect.appendChild(option);

        });

    } catch (error) {

        baseProductSelect.innerHTML =
            '<option value="">Unable to load products</option>';

        console.error("Product loading error:", error);

    }
}

categorySelect.addEventListener("change", loadProducts);


// ==========================================
// 8. RECOMMENDATIONS
// ==========================================

recommendBtn.addEventListener("click", getRecommendations);


async function getRecommendations() {

    const category = categorySelect.value;

    const priority = normalizePriority(
        document.getElementById("priority").value
    );

    const preferences = getUserPreferences();

    const budget = getBudget("maxBudget");

    if (budget === undefined) {
        return;
    }

    if (!category) {
        alert("Please select a category.");
        return;
    }

    if (!nutrientInfo[priority]) {
        alert("Please select a valid nutrient priority.");
        return;
    }

    results.innerHTML = "";

    resultSummary.textContent =
        "Finding recommendations...";

    recommendBtn.disabled = true;

    try {

        const requestBody = {

            category: category,
            priority: priority,
            diet: preferences.diet,
            allergies: preferences.allergies,
            max_price: budget

        };

        console.log("Recommendation request:", requestBody);

        const response = await fetch(
            `${API_URL}/recommend`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(requestBody)
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Unable to get recommendations."
            );
        }

        const recommendations =
            data.recommendations || [];

        if (recommendations.length === 0) {

            resultSummary.textContent =
                data.message || "No matching products found.";

            return;
        }

        resultSummary.textContent =
            `${recommendations.length} products found. ` +
            showAppliedFilters(preferences, priority, budget);

        recommendations.forEach((product, index) => {

            results.appendChild(
                createProductCard(product, index + 1)
            );

        });

    } catch (error) {

        resultSummary.textContent =
            error.message +
            " Please check whether the backend is running.";

    } finally {

        recommendBtn.disabled = false;

    }
}


// ==========================================
// 9. RECOMMENDATION PRODUCT CARD
// ==========================================

function createProductCard(product, rank) {

    const card = document.createElement("div");

    card.className = "product-card";

    const title = document.createElement("h3");

    title.textContent =
        product.product_name || "Food Product";

    const brand = document.createElement("p");

    brand.textContent =
        `Brand: ${product.brand || "Not available"}`;

    const category = document.createElement("p");

    category.textContent =
        `Category: ${product.category || "N/A"}`;

    const price = document.createElement("p");

    price.className = "product-price";
    price.textContent = formatPrice(product);

    const score = document.createElement("p");

    score.textContent =
        `Rank: #${rank} | Recommendation Score: ${product.score ?? "N/A"} / 100`;

    const serving = document.createElement("p");

    serving.textContent =
        `Serving Size: ${product.serving_size ?? "N/A"} g`;

    const nutrition = document.createElement("div");

    nutrition.className = "nutrition-info";

    const items = [
        ["Added Sugar", product.added_sugar, "g"],
        ["Fibre", product.fiber, "g"],
        ["Protein", product.protein, "g"],
        ["Sodium", product.sodium, "mg"],
        ["Saturated Fat", product.saturated_fat, "g"]
    ];

    items.forEach(([label, value, unit]) => {

        const item = document.createElement("p");

        item.textContent =
            `${label}: ${value ?? "Not available"}${value != null ? " " + unit : ""}`;

        nutrition.appendChild(item);

    });

    const explanation = document.createElement("p");

    explanation.textContent =
        product.explanation || "";

    card.append(
        title,
        brand,
        category,
        price,
        score,
        serving,
        nutrition,
        explanation
    );

    return card;
}


// ==========================================
// 10. FIND ALTERNATIVES
// ==========================================

alternativeBtn.addEventListener("click", findAlternatives);


async function findAlternatives() {

    const productId = baseProductSelect.value;

    const priority = normalizePriority(
        document.getElementById("alternativePriority").value
    );

    const preferences = getUserPreferences();

    const budget = getBudget("alternativeMaxBudget");

    if (budget === undefined) {
        return;
    }

    if (!productId) {
        alert("Please select a product first.");
        return;
    }

    if (!nutrientInfo[priority]) {
        alert("Please select a valid nutrient.");
        return;
    }

    alternativeResults.innerHTML = "";

    alternativeSummary.textContent =
        "Searching for alternatives...";

    alternativeBtn.disabled = true;

    try {

        const requestBody = {

            product_id: productId,
            priority: priority,
            diet: preferences.diet,
            allergies: preferences.allergies,
            max_price: budget

        };

        console.log("Alternative request:", requestBody);

        const response = await fetch(
            `${API_URL}/alternatives`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(requestBody)
            }
        );

        const data = await response.json();

        console.log("Alternative response:", data);

        if (!response.ok) {

            throw new Error(
                data.error || "Unable to find alternatives."
            );

        }

        const alternatives =
            data.alternatives || [];

        if (alternatives.length === 0) {

            alternativeSummary.textContent =
                (data.message || "No better alternatives found.") +
                " " +
                showAppliedFilters(preferences, priority, budget);

            return;
        }

        alternativeSummary.textContent =
            `Alternatives to ${data.selected_product || "your selected product"}. ` +
            showAppliedFilters(preferences, priority, budget);

        alternatives.forEach(product => {

            alternativeResults.appendChild(
                createAlternativeCard(product)
            );

        });

    } catch (error) {

        alternativeSummary.textContent =
            error.message +
            " Please check whether the backend is running.";

    } finally {

        alternativeBtn.disabled = false;

    }
}


// ==========================================
// 11. ALTERNATIVE PRODUCT CARD
// ==========================================

function createAlternativeCard(product) {

    const card = document.createElement("div");

    card.className =
        "product-card alternative-card";

    const title = document.createElement("h3");

    title.textContent =
        product.product_name || "Food Product";

    const brand = document.createElement("p");

    brand.textContent =
        `Brand: ${product.brand || "Not available"}`;

    const price = document.createElement("p");

    price.className = "product-price";
    price.textContent = formatPrice(product);

    const priority = nutrientInfo[product.nutrient];

    const comparison = document.createElement("div");

    comparison.className = "comparison";

    if (priority) {

        const selected = document.createElement("p");

        selected.textContent =
            `Selected Product: ${product.selected_value} ${priority.unit}`;

        const alternative = document.createElement("p");

        alternative.textContent =
            `Alternative Product: ${product[product.nutrient]} ${priority.unit}`;

        const difference = document.createElement("p");

        difference.className = "difference";

        difference.textContent =
            `${priority.label}: ${product.difference} ${priority.unit} ${product.difference_label}`;

        comparison.append(
            selected,
            alternative,
            difference
        );

    }

    const serving = document.createElement("p");

    serving.textContent =
        `Serving Size: ${product.serving_size ?? "N/A"} g`;

    const note = document.createElement("p");

    note.textContent =
        priority
            ? `This product has a better recorded ${priority.label.toLowerCase()} value.`
            : "This product is an alternative recommendation.";

    card.append(
        title,
        brand,
        price,
        serving,
        comparison,
        note
    );

    return card;
}


// ==========================================
// 12. INITIAL PAGE LOAD
// ==========================================

loadCategories().then(() => {
    loadProducts();
});
