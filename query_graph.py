import json
import os
from typing import TypedDict
from pathlib import Path
from groq import Groq
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "sky-agenda-week8"

class QueryState(TypedDict):
    userLocation: str
    userPeriod: str
    userDirection: str
    userLanguage: str
    dataYear: int
    allEvents: list
    friendlyAnswer: str

def getGroqApiKey()-> str :
    apiKey = os.getenv("Groq_key")
    if not apiKey:
        raise RuntimeError("Groq_key environment variable is missing.")
    return apiKey

def loadEvents(state: QueryState) -> dict:
    eventsFilePath = Path("yearlyEvents.json")

    if not eventsFilePath.exists():
        raise RuntimeError("yearlyEvents.json not found. Run research_graph.py first.")

    with open(eventsFilePath, "r", encoding="utf-8") as file:
        data = json.load(file)

    return {"allEvents": data["events"], "dataYear": data["year"]}


def filterNode(state: QueryState) -> dict:
    client = Groq(api_key=getGroqApiKey())

    user_lang = state.get("userLanguage", "العربية")
    
    if user_lang == "English":
        language_instruction = "Respond entirely in English with a friendly, engaging tone."
    else:
        language_instruction = "ردي بأسلوب مصري بسيط وودود، من غير تنسيق رسمي أو نقط مرقمة جافة، كأنك بتحكيله الموضوع."

    systemPrompt = f"""انت صاحبي اللي عنده شغف بالفلك وعارف معلومات كتير عن السما والنجوم والكواكب.
                مهمتك إنك تدّيني معلومات عن الأحداث الفلكية بأسلوب ودود وبسيط، زي ما تكون بتحكيلي عن حاجة حلوة شفتها، مش بتقرالي من تقرير رسمي.

                هتستلم قايمة أحداث فلكية، كل حدث ليه تاريخ دقيق (يوم/شهر/سنة) ومناطق جغرافية مرئي منها.
                هتستلم كمان مكان المستخدم، والفترة الزمنية اللي مهتم بيها (ممكن تكون شهر معين، فصل، أو سنة)، واتجاه النظر لو حدده.

                شغلانتك:
                1. قارني تاريخ كل حدث بالفترة اللي طلبها المستخدم. لو طلب شهر معين، هاتي بس أحداث الشهر ده. لو طلب فصل (زي الصيف)، افهمي إيه الشهور اللي بتدخل في الفصل ده وفلتري على أساسها. لو طلب سنة مختلفة عن السنة اللي عندك بيانات عنها، قوليله بوضوح إنك معندكش بيانات عن السنة دي، ومتختلقيش له أحداث.
                2. افهمي مكان المستخدم جغرافياً، وحددي الأحداث اللي فعلاً تتشاف من مكانه بناءً على المناطق المذكورة في كل حدث.
                3. لو حدد اتجاه نظر، وضحي له هل الأحداث دي في نفس الاتجاه ولا لأ.
                4. اذكري دايماً هل الحدث ممكن يتشاف بالعين المجردة ولا محتاج تلسكوب.

                لو مفيش أحداث تناسب طلبه (سواء بسبب المكان، الفترة، أو السنة)، قوليله بلطف ومتختلقيش حاجة.
                
                {language_instruction}"""
    
    userPayload = f"""الأحداث المتاحة (بيانات سنة {state.get("dataYear")}):
            {json.dumps(state["allEvents"], ensure_ascii=False)}
            مكان المستخدم: {state.get("userLocation") or "مش محدد"}
            الفترة الزمنية اللي طلبها: {state.get("userPeriod") or "مش محددة (كل السنة)"}
            اتجاه النظر: {state.get("userDirection") or "مش محدد"}
        """

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": userPayload}
        ],
        max_tokens=2000,
    )

    answer = response.choices[0].message.content

    return {"friendlyAnswer": answer}

builder = StateGraph(QueryState)

builder.add_node("loadEvents", loadEvents)
builder.add_node("filterNode", filterNode)

builder.add_edge(START, "loadEvents")
builder.add_edge("loadEvents", "filterNode")
builder.add_edge("filterNode", END)

graph = builder.compile()


if __name__ == "__main__":
    initialState = {
        "userLocation": "مصر",
        "userPeriod": "أغسطس",
        "userDirection": ""
    }
    result = graph.invoke(initialState)
    print(result["friendlyAnswer"])