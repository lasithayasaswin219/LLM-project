# """Local LangChain/Ollama agent with bounded, inspectable tool calls."""
import json
from datetime import datetime, timezone
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from tools.recipe_tools import TOOLS, TOOL_MAP

LOG=Path(__file__).resolve().parent/"logs"/"agent_log.jsonl"
LOG.parent.mkdir(exist_ok=True)
SYSTEM_PROMPT="""You are Smart Recipe AI, a cautious local recipe assistant.
You have a small recipe database and four actual tools. Select tools based on the user's request.
For recipe recommendations use search_recipes; to establish missing ingredients use check_ingredients;
for a calorie/protein constraint use calculate_nutrition; only use save_recipe if asked to save.
When more information is needed, call tools in sensible order, using recipe IDs returned by search.
Never claim a tool ran when it did not. Never fabricate nutrition, pantry quantities or database contents.
Do not state a recipe meets a calorie limit without calculating it. If none matches, say so.
Use existing conversation context for follow-up questions.
Recipes are examples; include realistic prep/cook time, quantities in grams, numbered steps,
missing ingredients and relevant food safety (egg fully cooked, leftovers refrigerated promptly).
A tool reports ingredient presence, not sufficient quantities. Clarify that when relevant.
Keep responses concise, readable, and explicit about estimates.
"""


def _log(event):
    with LOG.open("a",encoding="utf-8") as f:
        f.write(json.dumps({"at":datetime.now(timezone.utc).isoformat(),**event},default=str)+"\n")


class RecipeAgent:
    def __init__(self, model_name="llama3.2", max_steps=10):
        self.max_steps=max_steps
        self.llm=ChatOllama(model=model_name,temperature=0).bind_tools(TOOLS)
        self.messages=[SystemMessage(content=SYSTEM_PROMPT)]

    def ask(self, user_text):
        if not user_text.strip():
            return "Please enter ingredients or a recipe question."
        self.messages.append(HumanMessage(content=user_text))
        for step in range(1,self.max_steps+1):
            try:
                response=self.llm.invoke(self.messages)
            except Exception as exc:
                _log({"event":"model_error","error":str(exc)})
                return f"Ollama error: {exc}. Is Ollama running and the model downloaded?"
            self.messages.append(response)
            calls=response.tool_calls or []
            if not calls:
                content=response.content
                if isinstance(content,str):
                    return content
                return str(content)
            for call in calls:
                name=call.get("name","")
                args=call.get("args",{})
                tool=TOOL_MAP.get(name)
                if tool is None:
                    result={"error":f"Unknown tool: {name}"}
                else:
                    try:
                        result=tool.invoke(args)
                    except Exception as exc:
                        result={"error":f"Tool arguments or execution invalid: {str(exc)}"}
                event={"event":"tool_call","step":step,"tool":name,"arguments":args,"result":result}
                _log(event)
                print(f"\n[STEP {step}] TOOL: {name}")
                # print("  arguments:",json.dumps(args,ensure_ascii=False))
                # print("  result:",json.dumps(result,ensure_ascii=False))
                self.messages.append(ToolMessage(content=json.dumps(result,ensure_ascii=False,default=str),tool_call_id=call["id"]))
        _log({"event":"step_limit","max_steps":self.max_steps})
        return "I reached the 10-step safety limit. Please narrow your request and try again."
