"""Local web interface for the AI cooking simulator."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List
import os
import secrets

from flask import Flask, jsonify, render_template, request

import main as cooking


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
translator = cooking.GoogleCloudTranslationClient()


@lru_cache(maxsize=1)
def recipe_catalog() -> List[cooking.Recipe]:
    return cooking.load_recipes(cooking.DEFAULT_API_KEY, limit=30)


def serialize_recipe(recipe: cooking.Recipe) -> Dict[str, Any]:
    return {
        "name": recipe.name,
        "cuisine": recipe.cuisine,
        "ingredients": recipe.ingredients,
        "tools": recipe.tools,
        "steps": recipe.steps,
        "taste_profile": recipe.taste_profile,
        "difficulty": recipe.difficulty,
        "description": recipe.description,
        "source": recipe.source,
    }


def read_inventory(payload: Any) -> Dict[str, int]:
    if not isinstance(payload, dict):
        raise ValueError("재료 목록 형식이 올바르지 않습니다.")
    inventory: Dict[str, int] = {}
    for name, quantity in payload.items():
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > 80
            or isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 1
            or quantity > 9999
        ):
            raise ValueError("재료 이름 또는 수량이 올바르지 않습니다.")
        inventory[name.strip()] = quantity
    return inventory


def json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/bootstrap")
def bootstrap():
    recipes = recipe_catalog()
    return jsonify({
        "recipes": [serialize_recipe(recipe) for recipe in recipes],
        "inventory": cooking.Fridge().inventory,
        "api_available": any(recipe.source == "spoonacular" for recipe in recipes),
    })


@app.get("/api/recipes")
def search_recipes():
    query = request.args.get("q", "").strip()
    if len(query) > 120:
        return json_error("검색어는 120자 이내로 입력해 주세요.")
    recipes = cooking.load_recipes(cooking.DEFAULT_API_KEY, limit=30, query=query)
    return jsonify({
        "recipes": [serialize_recipe(recipe) for recipe in recipes],
        "api_available": any(recipe.source == "spoonacular" for recipe in recipes),
    })


@app.post("/api/recommend")
def recommend_recipes():
    payload = request.get_json(silent=True) or {}
    try:
        inventory = read_inventory(payload.get("inventory", {}))
    except ValueError as error:
        return json_error(str(error))

    fridge = cooking.Fridge()
    fridge.inventory = inventory
    assistant = cooking.AIKitchenAssistant()
    recipes = assistant.recommend(
        fridge,
        recipe_catalog(),
        api_key=cooking.DEFAULT_API_KEY,
        limit=cooking.RECOMMENDATION_LIMIT,
    )
    return jsonify({
        "recipes": [serialize_recipe(recipe) for recipe in recipes],
        "mode": "popular" if assistant.used_popular_fallback else "ingredients",
    })


@app.post("/api/fridge/add")
def add_ingredient():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    quantity = payload.get("quantity")
    try:
        inventory = read_inventory(payload.get("inventory", {}))
    except ValueError as error:
        return json_error(str(error))
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        return json_error("재료 이름을 1~80자로 입력해 주세요.")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 9999:
        return json_error("수량은 1~9999 사이의 정수로 입력해 주세요.")
    name = name.strip()
    if inventory.get(name, 0) + quantity > 9999:
        return json_error("재료별 보관 수량은 9999개까지입니다.")
    inventory[name] = inventory.get(name, 0) + quantity
    return jsonify({
        "inventory": inventory,
        "message": f"{name} {quantity}개를 냉장고에 저장했습니다.",
    })


@app.post("/api/fridge/remove")
def remove_ingredient():
    payload = request.get_json(silent=True) or {}
    try:
        inventory = read_inventory(payload.get("inventory", {}))
    except ValueError as error:
        return json_error(str(error))
    name = payload.get("name")
    quantity = payload.get("quantity", 1)
    if not isinstance(name, str) or not name.strip():
        return json_error("꺼낼 재료를 선택해 주세요.")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return json_error("수량은 1 이상의 정수로 입력해 주세요.")
    if inventory.get(name, 0) < quantity:
        return json_error("냉장고에 해당 수량의 재료가 없습니다.")
    inventory[name] -= quantity
    if inventory[name] == 0:
        del inventory[name]
    return jsonify({
        "inventory": inventory,
        "message": f"{name} {quantity}개를 냉장고에서 꺼냈습니다.",
    })


@app.post("/api/translate")
def translate_text():
    payload = request.get_json(silent=True) or {}
    target = payload.get("target")
    texts = payload.get("texts")
    if target not in {"ko", "en", "ja", "zh"}:
        return json_error("지원하지 않는 언어입니다.")
    if (
        not isinstance(texts, list)
        or len(texts) > 100
        or any(not isinstance(text, str) or len(text) > 2000 for text in texts)
    ):
        return json_error("번역할 문장 목록이 올바르지 않습니다.")
    try:
        translations = translator.translate_many(texts, target)
    except cooking.TranslationError as error:
        return json_error(str(error), 503)
    return jsonify({"translations": translations})


@app.post("/api/evaluate")
def evaluate_recipe():
    payload = request.get_json(silent=True) or {}
    recipe_data = payload.get("recipe")
    if not isinstance(recipe_data, dict):
        return json_error("평가할 레시피가 없습니다.")
    string_fields = ("name", "cuisine", "taste_profile", "description", "source")
    if any(not isinstance(recipe_data.get(field, ""), str) for field in string_fields):
        return json_error("레시피 정보가 올바르지 않습니다.")
    ingredients = recipe_data.get("ingredients")
    steps = recipe_data.get("steps")
    selected = payload.get("selected_ingredients")
    completed = payload.get("completed_steps")
    if (
        not isinstance(ingredients, list)
        or not ingredients
        or len(ingredients) > 100
        or any(not isinstance(item, str) for item in ingredients)
        or not isinstance(steps, list)
        or not steps
        or len(steps) > 100
        or any(not isinstance(item, str) for item in steps)
        or not isinstance(selected, list)
        or any(item not in ingredients for item in selected)
        or not isinstance(completed, list)
        or any(item not in steps for item in completed)
    ):
        return json_error("평가 정보의 형식이 올바르지 않습니다.")

    recipe = cooking.Recipe(
        name=recipe_data["name"][:200],
        cuisine=recipe_data["cuisine"][:100],
        ingredients=ingredients,
        tools=[],
        steps=steps,
        taste_profile=recipe_data["taste_profile"][:80],
        description=recipe_data["description"][:2000],
        source=recipe_data["source"][:40],
    )
    result = cooking.RecipeEvaluator().evaluate(recipe, selected, completed)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
