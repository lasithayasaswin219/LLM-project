
# """Validated tools for a local, reproducible recipe agent.

# Ingredient quantities are grams, including liquids for this classroom demo.
# Nutrition is approximate reference data, not health advice.
# """
import json
from pathlib import Path
from langchain_core.tools import tool

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _read(filename):
    with (DATA / filename).open(encoding="utf-8") as f:
        return json.load(f)


def _recipe(recipe_id):
    if not isinstance(recipe_id, str) or not recipe_id.strip():
        return None
    return next(
        (r for r in _read("recipes.json") if r["id"] == recipe_id.strip()),
        None
    )


def _parse_ingredients(available):
    if not isinstance(available, str) or not available.strip():
        raise ValueError("available_ingredients must contain comma-separated ingredient names")

    values = [x.strip().lower() for x in available.split(",") if x.strip()]

    if not values or len(values) > 40:
        raise ValueError("Provide between 1 and 40 ingredients")

    aliases = {
        "eggs": "egg",
        "onions": "onion",
        "tomatoes": "tomato",
        "rice": "cooked rice",
        "oil": "cooking oil",
        "oats": "rolled oats",
        "chickpeas": "cooked chickpeas",
        "pasta": "dry pasta",
        "potatoes": "potato",
        "carrots": "carrot",
        "tuna": "canned tuna"
    }

    return set(aliases.get(x, x) for x in values)


@tool
def search_recipes(available_ingredients: str, max_results: int = 5) -> dict:
    """Search local recipes ranked by overlap with comma-separated available ingredients. Returns recipe IDs for other tools."""
    try:
        available = _parse_ingredients(available_ingredients)

        # FIX: Correct indentation and integer conversion
        try:
            max_results = int(max_results)
        except (ValueError, TypeError):
            return {"error": "max_results must be a valid integer"}

        if not 1 <= max_results <= 20:
            return {"error": "max_results must be between 1 and 20"}

        ranked = []

        for recipe in _read("recipes.json"):
            names = set(recipe["ingredients"])
            match = sorted(names & available)
            missing = sorted(names - available)

            ranked.append({
                "id": recipe["id"],
                "name": recipe["name"],
                "time_minutes": recipe["time_minutes"],
                "matched": match,
                "missing": missing,
                "match_count": len(match),
                "match_fraction": round(len(match) / len(names), 2)
            })

        ranked.sort(
            key=lambda x: (
                -x["match_count"],
                len(x["missing"]),
                x["time_minutes"]
            )
        )

        return {
            "available": sorted(available),
            "recipes": ranked[:max_results],
            "note": "Search covers the bundled local database, not every possible recipe."
        }

    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


@tool
def check_ingredients(recipe_id: str, available_ingredients: str) -> dict:
    """Compare user's comma-separated ingredients against a recipe ID, returning required gram quantities and missing items."""
    try:
        available = _parse_ingredients(available_ingredients)
        recipe = _recipe(recipe_id)

        if not recipe:
            return {"error": f"Unknown recipe_id: {recipe_id}"}

        missing = {
            k: v for k, v in recipe["ingredients"].items()
            if k not in available
        }

        have = {
            k: v for k, v in recipe["ingredients"].items()
            if k in available
        }

        return {
            "recipe_id": recipe_id,
            "have": have,
            "missing": missing,
            "all_available": not missing,
            "note": "Presence only, not quantity sufficiency. All amounts are grams."
        }

    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


@tool
def calculate_nutrition(recipe_id: str, servings: int = 1) -> dict:
    """Calculate approximate calories and protein per serving for recipe ID using gram quantities and a local per-100g table. servings is desired portions (1-12)."""
    try:
        if not isinstance(servings, int) or not 1 <= servings <= 12:
            return {"error": "servings must be between 1 and 12"}

        recipe = _recipe(recipe_id)

        if not recipe:
            return {"error": f"Unknown recipe_id: {recipe_id}"}

        nutrition = _read("nutrition.json")

        unknown = [
            k for k in recipe["ingredients"]
            if k not in nutrition
        ]

        if unknown:
            return {"error": f"Missing nutrition values for: {', '.join(unknown)}"}

        total_cal = sum(
            g * nutrition[k][0] / 100
            for k, g in recipe["ingredients"].items()
        )

        total_protein = sum(
            g * nutrition[k][1] / 100
            for k, g in recipe["ingredients"].items()
        )

        return {
            "recipe_id": recipe_id,
            "recipe_batch_servings": recipe["servings"],
            "requested_servings": servings,
            "batch_calories_kcal": round(total_cal),
            "per_serving_calories_kcal": round(total_cal / servings),
            "per_serving_protein_g": round(total_protein / servings, 1),
            "note": "Estimates for whole recipe divided into requested servings; ingredients are NOT scaled. Values are approximate."
        }

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


@tool
def save_recipe(recipe_id: str, note: str = "") -> dict:
    """Persist a selected local recipe by ID and optional brief note to data/saved_recipes.json; do not invoke unless user requests saving."""
    try:
        recipe = _recipe(recipe_id)

        if not recipe:
            return {"error": f"Unknown recipe_id: {recipe_id}"}

        if not isinstance(note, str) or len(note) > 300:
            return {"error": "note must be text no longer than 300 characters"}

        path = DATA / "saved_recipes.json"
        saved = _read("saved_recipes.json")

        if not isinstance(saved, list):
            return {"error": "Saved recipe file has an invalid format"}

        saved.append({
            "id": recipe_id,
            "name": recipe["name"],
            "note": note,
            "ingredients": recipe["ingredients"],
            "instructions": recipe["instructions"]
        })

        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(saved, indent=2),
            encoding="utf-8"
        )
        tmp.replace(path)

        return {
            "saved": True,
            "recipe_id": recipe_id,
            "path": str(path),
            "total_saved": len(saved)
        }

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


TOOLS = [
    search_recipes,
    check_ingredients,
    calculate_nutrition,
    save_recipe
]

TOOL_MAP = {t.name: t for t in TOOLS}