# Reflection: Failures and Fixes

This document covers the real issues encountered while building the Research Graph pipeline, why each one happened, and how it was resolved. All of these occurred during actual development and testing, not simulated for this report.

## Design choice: single agent vs multi-agent

A single-agent architecture (LangGraph) was chosen over a multi-agent crew structure. The task does not involve distinct collaborating roles (researcher, writer, reviewer); it is one continuous pipeline with conditional retry and correction logic, which LangGraph's explicit state and conditional edges handle more directly than a role-based multi-agent setup would.

## Failure 1: Model ignoring the requested JSON structure

Early versions of the generation prompt described the expected JSON structure in plain text, including example values. The model frequently ignored the described structure and returned a different shape entirely (different field names, no nested location objects, English content where Arabic was requested).

Fix: switched from a text-described schema to Groq's `response_format` with an explicit `json_schema`, generated to match the Pydantic model. This made the schema a hard constraint enforced by the API rather than a suggestion embedded in the prompt. After this change, every generation returned the exact expected structure.

## Failure 2: Model refusing the request outright

A request asking the model to list "every country" an event is visible from was rejected by the API with a `json_validate_failed` error, the model's own explanation being that it could not provide an exhaustive list of every country for each event.

Fix: the prompt was changed from demanding an exhaustive list of individual countries to requesting general geographic regions (for example, "the Middle East" or "the Northern Hemisphere"). This was both easier for the model to commit to honestly and more astronomically accurate, since visibility is a function of latitude bands, not political borders.

## Failure 3: Structurally valid but factually incorrect data

Rule-based validation (checking that required fields exist and that dates fall within the target year) passed data that was structurally complete but contained real errors: implausible event dates, meteor showers assigned viewing directions inconsistent with their known radiant, and in one case a fabricated planetary conjunction that is not a real astronomical event.

Fix: added a second validation layer, an LLM-based reviewer (`llmValidate`), that checks the generated events for real-world plausibility rather than just structural correctness. This reflects a deliberate choice to combine rule-based and LLM-based validation rather than relying on either alone: rule-based checks are fast and catch obvious structural problems, while the LLM-based check catches content-level errors that no fixed rule could anticipate.

## Failure 4: Retry discarding correct information

The initial retry design regenerated the entire event list from scratch on every failed validation, with no memory of what specifically was wrong. This meant a mostly-correct result with one flawed event was thrown away entirely, and a new attempt could introduce different errors instead of correcting the original one.

Fix: two related changes. First, the validation error message is now fed back into the next generation attempt as explicit correction guidance, rather than repeating the exact same prompt. Second, after the standard retry budget (3 attempts) is exhausted, a dedicated fixer node takes the last generated data plus the specific reported issue and attempts a targeted correction instead of full regeneration. The fix is then re-validated before being accepted; if it still fails after its own limited retry budget, the data and the failure reason are saved separately rather than silently overwriting the last known-good file.

## Guardrails summary

- Maximum 3 full regeneration attempts before escalating to the fixer node.
- Maximum 2 fixer attempts before giving up and saving the failure state separately.
- A failed run never overwrites the last successful `yearlyEvents.json`.
- All model calls use a fixed, pinned model (`openai/gpt-oss-120b`) rather than relying on default routing.

## Observability

LangSmith tracing is enabled for all graph runs under the project `sky-agenda-week8`, including every retry and fixer invocation, with no additional instrumentation code required beyond setting the project's environment variables. This made it possible to inspect the exact sequence of node executions for both the failed and the eventually successful runs described above.
