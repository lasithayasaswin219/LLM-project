import unittest
from tools.recipe_tools import search_recipes, check_ingredients, calculate_nutrition, save_recipe


class ToolTests(unittest.TestCase):
    def test_search_returns_ranked_ids(self):
        value=search_recipes.invoke({"available_ingredients":"eggs, rice, onions, oil"})
        self.assertTrue(value["recipes"])
        self.assertIn("id",value["recipes"][0])

    def test_missing(self):
        value=check_ingredients.invoke({"recipe_id":"egg_fried_rice","available_ingredients":"eggs, rice"})
        self.assertEqual(set(value["missing"]),{"onion","cooking oil"})

    def test_nutrition(self):
        value=calculate_nutrition.invoke({"recipe_id":"egg_fried_rice","servings":2})
        self.assertGreater(value["per_serving_calories_kcal"],0)
        self.assertEqual(value["batch_calories_kcal"],round(value["per_serving_calories_kcal"]*2,0))

    def test_bad_input(self):
        self.assertIn("error",search_recipes.invoke({"available_ingredients":""}))
        self.assertIn("error",calculate_nutrition.invoke({"recipe_id":"unknown","servings":1}))

    def test_save_to_json(self):
        from tools import recipe_tools as mod
        from tempfile import TemporaryDirectory
        import json
        from pathlib import Path
        with TemporaryDirectory() as tmp:
            old=mod.DATA
            try:
                mod.DATA=Path(tmp)
                (mod.DATA/"recipes.json").write_text((old/"recipes.json").read_text())
                (mod.DATA/"saved_recipes.json").write_text("[]")
                result=save_recipe.invoke({"recipe_id":"egg_fried_rice","note":"demo"})
                self.assertTrue(result["saved"])
                self.assertEqual(len(json.loads((mod.DATA/"saved_recipes.json").read_text())),1)
            finally:
                mod.DATA=old


if __name__=="__main__":
    unittest.main()
