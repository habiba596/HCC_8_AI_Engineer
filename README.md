# Sky Agenda

Sky Agenda is a bilingual astronomy assistant that tells users what astronomical events are visible from their location during a time period they choose. The response is generated in a friendly, conversational Egyptian Arabic tone.

This is a Week 8 (Agentic AI) submission for the Helwan Career Center 12-week AI industry roadmap. The project is built around two separate LangGraph pipelines backed by the Groq API (model: `openai/gpt-oss-120b`), plus a Streamlit interface.

## How it works

The system is split into two independent graphs, each responsible for a different part of the workflow.

### 1. Research Graph (`research_graph.py`)

Run once a year, not part of the live user flow. It generates a full year's worth of astronomical events and validates them before saving.

Flow:

```
START -> searchNode -> validateDate -> llmValidate -> formatAndSave -> END
```

With two safety layers built in:

- If rule-based or LLM-based validation fails, the graph retries generation up to 3 times.
- If validation still fails after 3 attempts, a dedicated fixer node takes the last generated data plus the specific validation error and attempts a targeted correction, rather than discarding everything and starting over. This fix is re-validated before being accepted.
- If the fixer also fails after its allowed attempts, the last version and the error reason are saved separately instead of overwriting the last known-good data file.

Output: `yearlyEvents.json`

### 2. Query Graph (`query_graph.py`)

Runs every time a user submits a question through the UI.

Flow:

```
START -> loadEvents -> filterNode -> END
```

`loadEvents` reads `yearlyEvents.json`. `filterNode` sends the full event list along with the user's location, time period, and viewing direction to the model, which:

- Infers the user's general region from their stated location (no hardcoded country-to-region mapping)
- Compares each event's date against the requested time period
- States clearly if no data exists for a requested year, rather than inventing events
- Mentions naked-eye visibility naturally within the response text
- Responds in a warm, conversational Arabic tone

### 3. UI (`app.py`)

A Streamlit interface with four inputs: location, time period, viewing direction, and an optional extra question. Submitting calls the Query Graph directly and displays the returned text.

## Setup

```
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
Groq_key=your_groq_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
```

## Usage

Generate or refresh the yearly event data (run this first, and only once per year):

```
python research_graph.py
```

Launch the application:

```
streamlit run app.py
```

## Tracing

LangSmith tracing is enabled for both graphs under the project name `sky-agenda-week8`. Every run, including retries and fixer invocations, is logged and viewable at smith.langchain.com.

## Project structure

```
research_graph.py    Yearly data generation and validation pipeline
query_graph.py        Live query pipeline used by the UI
app.py                 Streamlit interface
yearlyEvents.json       Generated event data (produced by research_graph.py)
REPORT.md               Reflection on failures encountered and fixes applied
```

## Notes

- Only the Groq API is used throughout; no other model provider is required.
- The old Gradio-based prototype and the local Ollama-based offline model have been fully removed and replaced by this architecture, in part because the local model produced inconsistent and sometimes factually wrong visibility claims.
