from agent import RecipeAgent


def main():
    print("Smart Recipe AI | Ollama | Type 'e' to exit")
    print("Try: I have eggs, rice, onion and oil. Find a recipe under 500 kcal, check missing ingredients and save it.")
    agent=RecipeAgent(model_name="llama3.2",max_steps=10)
    while True:
        try:
            foods=input("\nEnter foods / request (e to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if foods.lower() in {"e","exit","quit"}:
            print("Thank you for using Smart Recipe AI!")
            break
        print("\n"+agent.ask(foods))


if __name__=="__main__":
    main()
