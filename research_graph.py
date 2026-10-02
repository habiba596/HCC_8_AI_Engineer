import json
import os
import time
from typing import TypedDict
from pathlib import Path
from groq import Groq
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

from dotenv import load_dotenv
load_dotenv()

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "sky-agenda-week8"

class ResearchState(TypedDict):
    targetYear: int
    rawEvents : list
    isValid: bool
    validationError : str
    attempts :int
    fixAttempts : int
    inFixMode: bool


class AstronomicalEvent(BaseModel):
    eventName: str
    dateTimeISO : str
    isNakedEyeVisible : bool
    viewingDirection : str
    locations : list
    description : str


def getGroqApiKey()-> str :
    apiKey = os.getenv("Groq_key")
    if not apiKey:
        raise RuntimeError("Groq_key environment variable is missing.")
    return apiKey


def extractJson(text: str)-> str :
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 :
        raise ValueError(f"No JSON found in response:\n{text[:300]}")
    return text[start:end+1]


def searchNode(state: ResearchState)-> dict:
    client = Groq(api_key= getGroqApiKey())
    targetYear = state["targetYear"]

    previousError = state.get("validationError", "")

    correctionNote = ""
    if previousError:
        correctionNote = f"""
            IMPORTANT: A previous attempt failed this check with the following issue:
            "{previousError}"
            Fix this specific issue in your new response. Double-check dates and visibility locations carefully.
        """


    prompt = f"""List all significant astronomical events for the entire year {targetYear} (meteor showers, eclipses, planetary alignments, supermoons, conjunctions, etc.).
        For each event, list the general geographic regions from which it is visible (for example: the Middle East, Western Europe, East Asia, North America, Southern Africa, etc.) — describe coverage broadly rather than naming individual countries.
        Write eventName, viewingDirection, and description content in Arabic text, but keep the JSON keys themselves in English.
        Base every field on real astronomical data for {targetYear}.
        {correctionNote}
    """

    response = client.chat.completions.create(
        model= "openai/gpt-oss-120b",
        messages=[
            {
                "role" : "system",
                "content" : "You return structured astronomical event data."
            },
            {
                "role" : "user",
                "content" : prompt
            }
        ],
        max_tokens= 8000,

        response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "yearly_events",
            "schema": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "eventName": {"type": "string"},
                                "dateTimeISO": {"type": "string"},
                                "isNakedEyeVisible": {"type": "boolean"},
                                "viewingDirection": {"type": "string"},
                                "locations": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "description": {"type": "string"}
                            },
                            "required": ["eventName", "dateTimeISO", "isNakedEyeVisible",
                                        "viewingDirection", "locations", "description"]
                        }
                    }
                },
                "required": ["year", "events"]
            }
        }
    }
    )
    rawContent = response.choices[0].message.content
    parsed = json.loads(rawContent)

    currentAttempts = state.get("attempts", 0)

    return {
        "rawEvents": parsed["events"],
        "attempts": currentAttempts + 1
    }


def validateDate(state:ResearchState)-> dict:
    events = state.get("rawEvents", [])

    if len(events)==0:
        return {
            "isValid" : False,
            "validationError" : "No events were returned"
        }

    requiredFields = [
                      "eventName", 
                      "dateTimeISO", "isNakedEyeVisible", 
                      "viewingDirection", "locations", 
                      "description"
                      ]

    for event in events:
        for field in requiredFields :
            if field not in event:
                return {"isValid": False, "validationError": f"An event is missing the field: {field}"}
        if not event ["locations"] :
            return {"isValid": False, "validationError": f"An event has no locations: {event.get('eventName', '')}"}

    targetYear = state["targetYear"]

    for event in events :
        eventYear = event["dateTimeISO"][:4]
        if eventYear != str(targetYear):
            return {"isValid": False, "validationError": f"Event has a date from a different year: {event['dateTimeISO']}"}

    return {"isValid": True, "validationError": ""}

def fixerNode(state: ResearchState) -> dict:
    client = Groq(api_key=getGroqApiKey())
    events = state["rawEvents"]
    error = state.get("validationError", "")

    fixPrompt = f"""The following list of astronomical events has a known issue:
"{error}"

Here is the current data:
{json.dumps(events, ensure_ascii=False)}

Fix ONLY the issue described above. Keep everything else unchanged.
Return the corrected full list in the same JSON structure (same fields, same keys).
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Respond with raw JSON only. Start with { and end with }."},
            {"role": "user", "content": fixPrompt}
        ],
        max_tokens=8000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "fixed_events",
                "schema": {
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "eventName": {"type": "string"},
                                    "dateTimeISO": {"type": "string"},
                                    "isNakedEyeVisible": {"type": "boolean"},
                                    "viewingDirection": {"type": "string"},
                                    "locations": {"type": "array", "items": {"type": "string"}},
                                    "description": {"type": "string"}
                                },
                                "required": ["eventName", "dateTimeISO", "isNakedEyeVisible",
                                             "viewingDirection", "locations", "description"]
                            }
                        }
                    },
                    "required": ["events"]
                }
            }
        }
    )

    rawContent = response.choices[0].message.content
    parsed = json.loads(rawContent)
    currentFixAttempts = state.get("fixAttempts", 0)

    return {
        "rawEvents": parsed["events"],
        "fixAttempts": currentFixAttempts + 1,
        "inFixMode": True
    }

def llmValidate(state: ResearchState) -> dict:
    client = Groq(api_key=getGroqApiKey())
    events = state["rawEvents"]

    checkPrompt = f"""Carefully review the following list of astronomical events:
{json.dumps(events, ensure_ascii=False)}

Check that:
- Every event is astronomically real and plausible (not fabricated)
- The description is consistent with the event name and viewing direction
- There is no strange duplication of the same event with inconsistent dates

Respond in JSON only: {{"isValid": true or false, "reason": "short reason"}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Respond with raw JSON only."},
            {"role": "user", "content": checkPrompt}
        ],
        max_tokens=2000,
    )

    rawJson = extractJson(response.choices[0].message.content)
    result = json.loads(rawJson)

    return {
        "isValid": result["isValid"],
        "validationError": result.get("reason", "")
    }

def saveWithError(state: ResearchState)-> dict :

    events = state.get("rawEvents", [])
    errorMessage = state.get("validationError", "Unkown error")

    outputData = {
        "year" : state["targetYear"],
        "events" : events ,
        "status" : "FAILED",
        "error" : errorMessage
    }

    outputFilePath = Path("yearlyEvents_FAILED.json")

    with open(outputFilePath, "w", encoding= "utf-8") as file :
        json.dump(outputData, file, ensure_ascii= False, indent = 2)


    print(f"FAILED after {state.get('attempts', 0)} attempts. Reason: {errorMessage}")
    print(f"Last version saved to {outputFilePath}")

    return  {}

def formatAndSave(state: ResearchState)-> dict :

    outputData = {
        "year" : state["targetYear"],
        "events" : state["rawEvents"]
    }

    outputFilePath = Path("yearlyEvents.json")
    with open(outputFilePath, "w", encoding= "utf-8") as file :
        json.dump(outputData, file, ensure_ascii= False, indent= 2)

    print(f"Saved successfully — {len(state["rawEvents"])} events")
    return {}


def routeAfterValidation(state: ResearchState)-> str :
    if state["isValid"] :
        return "format"

    if state.get("attempts", 0) < 3 :
        return "retry"
    else :
        return "tryFix"


def routeAfterFix(state: ResearchState)-> str :
    if state["isValid"] :
        return "format"
    if state.get("fixAttempts", 0) < 2 :
        return "retryFix"
    else:
        return "giveUp"

def routeAfterLlmValidate(state: ResearchState) -> str:
    if state["isValid"]:
        return "format"

    if state.get("inFixMode", False):
        if state.get("fixAttempts", 0) < 2:
            return "retryFix"
        else:
            return "giveUp"
    else:
        if state.get("attempts", 0) < 3:
            return "retry"
        else:
            return "tryFix"

builder = StateGraph(ResearchState)

builder.add_node("searchNode", searchNode)
builder.add_node("validateDate",validateDate)
builder.add_node("llmValidate",llmValidate)
builder.add_node("fixerNode", fixerNode)
builder.add_node("saveWithError",saveWithError)
builder.add_node("formatAndSave",formatAndSave)

builder.add_edge(START, "searchNode")
builder.add_edge("searchNode", "validateDate")

builder.add_conditional_edges(
    "validateDate",
    lambda state: "llmCheck" if state["isValid"] else routeAfterValidation(state),
    {
        "llmCheck" : "llmValidate",
        "retry" : "searchNode",
        "tryFix": "fixerNode"
    }
)

builder.add_conditional_edges(
    "llmValidate",
    routeAfterLlmValidate,
    {
        "format": "formatAndSave",
        "retry": "searchNode",
        "tryFix": "fixerNode",
        "retryFix": "fixerNode",
        "giveUp": "saveWithError"
    }
)

builder.add_edge("fixerNode", "llmValidate")

graph = builder.compile()


if __name__ == "__main__":
    initialState = {"targetYear": 2026, "attempts": 0}
    result = graph.invoke(initialState)
    print(result)