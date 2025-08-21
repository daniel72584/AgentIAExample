import json
from typing import Optional, Mapping

from completions import generate_response
from tool_data import Prompt


def agent_qa_function(
        readme_content: Optional[str] = None,
        readme_path: Optional[str] = None,
        *,
        min_score: int = 80
) -> str:
    """
    LLM-based QA for a README.

    Provide either `readme_content` or `readme_path`. The tool returns a JSON string:
    {
      "score": int (0-100),
      "passes": bool,
      "issues": [str],
      "suggested_changes": str,
      "summary": str
    }
    """
    if not readme_content and not readme_path:
        raise ValueError("Provide either readme_content or readme_path")

    if readme_path and not readme_content:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()

    system = (
        "You are a meticulous technical editor for software READMEs. "
        "Evaluate clarity, completeness, setup accuracy, usage examples, "
        "project structure, licensing, contribution guidelines, and consistency. "
        "Be strict but practical."
    )

    user = f"""
README to review (Markdown):

<<<README_START
{readme_content}
README_END>>>

Return ONLY valid minified JSON in this exact schema:
{{
  "score": 0,                // integer 0..100
  "passes": false,           // true if good enough for release
  "issues": ["..."],         // list of concrete problems; keep each short
  "suggested_changes": "...",// concise, actionable rewrite suggestions
  "summary": "..."           // 1-2 sentences max
}}
Scoring rubric:
- 90-100: Excellent; shippable with minor polish
- 80-89: Good; ready if suggestions are applied
- 70-79: Needs work; important gaps
- <70: Insufficient

When uncertain, be conservative. If instructions are missing, mark them as issues.
Consider common sections: Overview, Quickstart, Requirements, Installation, Usage,
Configuration, Examples, Architecture/Design, Testing, Roadmap, License, Contributing.
"""

    resp = generate_response(Prompt(messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]))

    # Normalize typical SDK outputs into text
    if isinstance(resp, Mapping):
        if "content" in resp and isinstance(resp["content"], str):
            text = resp["content"]
        elif isinstance(resp.get("choices"), list) and resp["choices"]:
            text = resp["choices"][0]["message"]["content"]
        else:
            text = json.dumps(resp)
    else:
        text = str(resp)

    # Ensure valid JSON (agent might include code fences)
    text = text.strip().strip("`")
    text = text.replace("\n", " ")
    # Try to extract JSON object if surrounded by extra tokens
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        # Fallback: return a failure payload to keep the agent flow alive
        payload = {
            "score": 0,
            "passes": False,
            "issues": [f"Invalid JSON from LLM: {e}"],
            "suggested_changes": "Re-run QA; ensure the README is passed correctly.",
            "summary": "QA failed to parse."
        }

    # Apply threshold if the model forgot to set passes
    if "passes" not in payload or not isinstance(payload["passes"], bool):
        payload["passes"] = int(payload.get("score", 0)) >= min_score

    # Return a string; your agent prints/stores it in memory
    return json.dumps(payload, ensure_ascii=False)