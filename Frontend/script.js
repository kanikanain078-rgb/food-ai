
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

// Support both new and old HTML option values.
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


// LOAD REAL CATEGORIES AND PRODUCTS

async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error("Could not load categories.");
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
            throw new Error("Could not load products.");
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


// RECOMMENDATION FEATURE

recommendBtn.addEventListener("click", getRecommendations);

async function getRecommendations() {
    const category = categorySelect.value;
    const diet = document.getElementById("diet").value;
    const priority = normalizePriority(
        document.getElementById("priority").value
    );

    const allergyText = document.getElementById("allergies").value;

    const allergies = allergyText
        .split(",")
        .map(item => item.trim().toLowerCase())
        .filter(item => item !== "");

    if (!category) {
        alert("Please select a food category.");
        return;
    }

    if (!nutrientInfo[priority]) {
        alert("Please select a valid nutrient priority.");
        return;
    }

    results.innerHTML = "";
    resultSummary.textContent = "Finding recommendations...";
    recommendBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/recommend`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                category,
                diet,
                priority,
                allergies
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to get recommendations.");
        }

        const recommendations = data.recommendations || [];

        if (recommendations.length === 0) {
            resultSummary.textContent =
                data.message || "No matching products found.";
            return;
        }

        resultSummary.textContent =
            `${recommendations.length} products found in the real dataset.`;

        recommendations.forEach(product => {
            results.appendChild(createProductCard(product, priority));
        });

    } catch (error) {
        resultSummary.textContent = error.message;
    } finally {
        recommendBtn.disabled = false;
    }
}


// RECOMMENDATION CARD

function createProductCard(product, priority) {
    const card = document.createElement("div");
    card.className = "product-card";

    const title = document.createElement("h3");
    title.textContent = product.product_name || "Food Product";

    const brand = document.createElement("p");
    brand.textContent = `Brand: ${product.brand || "Not available"}`;

    const category = document.createElement("p");
    category.textContent = `Category: ${product.category || "N/A"}`;

    const score = document.createElement("p");
    score.textContent = `Priority Match Score: ${product.score ?? "N/A"} / 100`;

    const serving = document.createElement("p");
    serving.textContent =
        `Recorded serving size: ${product.serving_size ?? "N/A"} g`;

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
    explanation.textContent = product.explanation || "";

    card.append(title, brand, category, score, serving, nutrition, explanation);

    return card;
}


// ALTERNATIVE FEATURE

alternativeBtn.addEventListener("click", findAlternatives);

async function findAlternatives() {
    const productId = baseProductSelect.value;

    const priority = normalizePriority(
        document.getElementById("alternativePriority").value
    );

    if (!productId) {
        alert("Please select a product first.");
        return;
    }

    if (!nutrientInfo[priority]) {
        alert("Please select a valid nutrient.");
        return;
    }

    alternativeResults.innerHTML = "";
    alternativeSummary.textContent = "Searching for alternatives...";
    alternativeBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/alternatives`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                product_id: productId,
                priority
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to find alternatives.");
        }

        const alternatives = data.alternatives || [];

        if (alternatives.length === 0) {
            alternativeSummary.textContent =
                data.message || "No better alternatives found.";
            return;
        }

        alternativeSummary.textContent =
            `Alternatives to ${data.selected_product || "your selected product"}:`;

        alternatives.forEach(product => {
            alternativeResults.appendChild(
                createAlternativeCard(product)
            );
        });

    } catch (error) {
        alternativeSummary.textContent =
            error.message + " Please check that the backend is running.";
    } finally {
        alternativeBtn.disabled = false;
    }
}


// ALTERNATIVE COMPARISON CARD

function createAlternativeCard(product) {
    const card = document.createElement("div");
    card.className = "product-card alternative-card";

    const title = document.createElement("h3");
    title.textContent = product.product_name;

    const brand = document.createElement("p");
    brand.textContent = `Brand: ${product.brand}`;

    const priority = nutrientInfo[product.nutrient];

    const comparison = document.createElement("div");
    comparison.className = "comparison";

    const selected = document.createElement("p");
    selected.textContent =
        `Selected product: ${product.selected_value} ${priority.unit}`;

    const alternative = document.createElement("p");
    alternative.textContent =
        `Alternative product: ${product[product.nutrient]} ${priority.unit}`;

    const difference = document.createElement("p");
    difference.className = "difference";

    difference.textContent =
        `${priority.label}: ${product.difference} ${priority.unit} ${product.difference_label}`;

    const serving = document.createElement("p");
    serving.textContent =
        `Both products have the same recorded serving size: ${product.serving_size ?? "N/A"} g`;

    const note = document.createElement("p");
    note.textContent =
        `This alternative has a better recorded ${priority.label.toLowerCase()} value.`;

    comparison.append(selected, alternative, difference);
    card.append(title, brand, serving, comparison, note);

    return card;
}


// INITIAL PAGE LOAD

loadCategories().then(() => {
    loadProducts();
});
